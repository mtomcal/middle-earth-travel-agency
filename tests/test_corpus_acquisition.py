import bz2
import io
import json
import sqlite3
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError

import pytest
from email.message import Message

from middle_earth_travel_agency.corpus_acquisition import (
    CandidatePage,
    DiscoveryRecord,
    DiscoveryRequest,
    PywikibotCatalog,
    SourceSnapshot,
    discover_candidates,
    download_initial_dump,
    extract_article_artifacts,
    _blocks,
    _classify_block,
    _contact_user_agent,
    _iter_dump_pages,
    _normalize_prose,
    _resolve_redirect,
    _write_immutable_json,
)


class StubCatalog:
    def articles(self, category: str, limit: int):
        assert category == "Category:Middle-earth characters"
        assert limit == 3
        return [
            CandidatePage(page_id=10, title="Gandalf"),
            CandidatePage(page_id=11, title="Frodo Baggins"),
        ]


def test_discovery_preserves_routes_and_deduplicates_by_page_id():
    observed_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)

    result = discover_candidates(
        DiscoveryRequest(
            categories=("Middle-earth characters",),
            nominations=("Gandalf",),
            max_candidates=3,
        ),
        catalog=StubCatalog(),
        observed_at=observed_at,
    )

    assert [record.observed_page_id for record in result.records] == [10, 11]
    assert result.records[0].discovery_route == "category or API"
    assert result.records[0].discovery_reference == (
        "https://en.wikipedia.org/wiki/Category:Middle-earth_characters"
    )
    assert result.records[0].discovery_timestamp == "2026-07-20T12:00:00+00:00"


def test_extraction_resolves_an_earlier_redirect_target_in_two_sequential_passes(tmp_path):
    xml = """<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
      <siteinfo><sitename>Wikipedia</sitename><dbname>enwiki</dbname></siteinfo>
      <page><title>Gandalf</title><ns>0</ns><id>1</id>
        <revision><id>101</id><parentid>100</parentid><timestamp>2026-06-30T10:00:00Z</timestamp>
          <text xml:space="preserve">'''Gandalf''' was a [[Wizard (Middle-earth)|wizard]] in Middle-earth.

== History ==
He bore the name [[Mithrandir]].

* Navigation-like list

{{Unresolved|meaning}} shaped this paragraph.</text>
        </revision>
      </page>
      <page><title>Mithrandir</title><ns>0</ns><id>2</id><redirect title="Gandalf" />
        <revision><id>102</id><timestamp>2026-06-30T11:00:00Z</timestamp>
          <text xml:space="preserve">#REDIRECT [[Gandalf]]</text>
        </revision>
      </page>
    </mediawiki>"""
    dump_path = tmp_path / "enwiki-20260701-pages-articles.xml.bz2"
    dump_path.write_bytes(bz2.compress(xml.encode()))
    output_dir = tmp_path / "artifacts"
    discovery = DiscoveryRecord(
        discovery_route="human nomination",
        discovery_reference="operator nomination",
        observed_page_title="Mithrandir",
        observed_page_id=None,
        discovery_timestamp="2026-07-20T12:00:00+00:00",
    )

    result = extract_article_artifacts(
        dump_path,
        discoveries=(discovery,),
        output_dir=output_dir,
        source=SourceSnapshot.initial(retrieved_at="2026-07-20T12:30:00+00:00"),
    )

    assert result.scan_passes == 2
    assert len(result.successes) == 1
    artifact_path = output_dir / f"{result.successes[0].article_artifact_id}.json"
    first_serialization = artifact_path.read_bytes()
    repeat = extract_article_artifacts(
        dump_path,
        discoveries=(discovery,),
        output_dir=output_dir,
        source=SourceSnapshot.initial(retrieved_at="2026-07-20T12:30:00+00:00"),
    )
    assert repeat == result
    assert artifact_path.read_bytes() == first_serialization
    artifact = json.loads(first_serialization)
    assert artifact["canonical_title"] == "Gandalf"
    assert artifact["revision_id"] == 101
    assert artifact["parent_revision_id"] == 100
    assert artifact["raw_wikitext"].startswith("'''Gandalf'''")
    assert artifact["redirect_chain"] == [{"source_title": "Mithrandir", "target_title": "Gandalf"}]
    assert [passage["normalized_text"] for passage in artifact["extracted_passages"]] == [
        "Gandalf was a wizard in Middle-earth.",
        "He bore the name Mithrandir.",
    ]
    assert artifact["extracted_passages"][1]["heading_path"] == ["History"]
    assert {item["structure_type"] for item in artifact["structural_exclusions"]} == {
        "list",
        "unresolved template",
    }


def test_redirect_lookup_distinguishes_case_after_the_first_character(tmp_path):
    xml = """<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
      <siteinfo><sitename>Wikipedia</sitename><dbname>enwiki</dbname></siteinfo>
      <page><title>Middle-earth</title><ns>0</ns><id>1</id>
        <revision><id>101</id><timestamp>2026-06-30T10:00:00Z</timestamp>
          <text xml:space="preserve">Middle-earth is the principal setting.</text>
        </revision>
      </page>
      <page><title>Middle-Earth</title><ns>0</ns><id>2</id><redirect title="Middle-earth" />
        <revision><id>102</id><timestamp>2026-06-30T11:00:00Z</timestamp>
          <text xml:space="preserve">#REDIRECT [[Middle-earth]]</text>
        </revision>
      </page>
    </mediawiki>"""
    dump_path = tmp_path / "enwiki-20260701-pages-articles.xml.bz2"
    dump_path.write_bytes(bz2.compress(xml.encode()))
    discovery = DiscoveryRecord(
        discovery_route="category or API",
        discovery_reference="https://en.wikipedia.org/wiki/Category:Middle-earth",
        observed_page_title="Middle-earth",
        observed_page_id=1,
        discovery_timestamp="2026-07-20T12:00:00+00:00",
    )

    result = extract_article_artifacts(
        dump_path,
        discoveries=(discovery,),
        output_dir=tmp_path / "artifacts",
        source=SourceSnapshot.initial(retrieved_at="2026-07-20T12:30:00+00:00"),
    )

    assert len(result.successes) == 1
    assert result.failures == ()


class StubResponse(io.BytesIO):
    def __init__(self, body: bytes, *, status: int, headers: dict[str, str]):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        for name, value in headers.items():
            self.headers[name] = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_incomplete_dump_creates_no_artifacts(tmp_path):
    dump_path = tmp_path / "enwiki-20260701-pages-articles.xml.bz2"
    dump_path.write_bytes(bz2.compress(b"<mediawiki><page>"))
    output_dir = tmp_path / "artifacts"
    discovery = DiscoveryRecord(
        discovery_route="human nomination",
        discovery_reference="operator nomination",
        observed_page_title="Gandalf",
        observed_page_id=None,
        discovery_timestamp="2026-07-20T12:00:00+00:00",
    )

    with pytest.raises(Exception, match="no element found"):
        extract_article_artifacts(
            dump_path,
            discoveries=(discovery,),
            output_dir=output_dir,
            source=SourceSnapshot.initial(retrieved_at="2026-07-20T12:30:00+00:00"),
        )

    assert list(output_dir.glob("*.json")) == []


def test_pywikibot_catalog_is_identified_serial_and_non_recursive(monkeypatch):
    calls = []

    class Throttle:
        def set_delays(self, *, delay, absolute):
            calls.append(("delay", delay, absolute))

    class Site:
        throttle = Throttle()

    class Page:
        pageid = 44

        def title(self):
            return "Aragorn"

    class Category:
        def __init__(self, site, title):
            calls.append(("category", site, title))

        def articles(self, *, recurse, total, namespaces):
            calls.append(("articles", recurse, total, namespaces))
            yield Page()

    monkeypatch.setattr("pywikibot.Site", lambda *_args, **_kwargs: Site())
    monkeypatch.setattr("pywikibot.Category", Category)

    catalog = PywikibotCatalog(contact="mailto:operator@example.com", minimum_request_interval=1.0)

    assert list(catalog.articles("Category:Middle-earth characters", 5)) == [
        CandidatePage(page_id=44, title="Aragorn")
    ]
    assert ("delay", 1.0, True) in calls
    assert ("articles", False, 5, 0) in calls
    assert list(catalog.articles("Category:Middle-earth characters", 0)) == []

    with pytest.raises(ValueError, match="at least one second"):
        PywikibotCatalog(contact="mailto:operator@example.com", minimum_request_interval=0.5)


def test_dump_download_is_single_connection_resumable_and_identified(tmp_path):
    requests = []
    responses = iter(
        [
            StubResponse(b"abc", status=200, headers={"Content-Length": "6"}),
            StubResponse(
                b"def",
                status=206,
                headers={"Content-Length": "3", "Content-Range": "bytes 3-5/6"},
            ),
        ]
    )

    def open_request(request, timeout):
        requests.append((request, timeout))
        return next(responses)

    destination = tmp_path / "enwiki-20260701-pages-articles.xml.bz2"
    result = download_initial_dump(
        destination,
        contact="mailto:operator@example.com",
        open_request=open_request,
        sleep=lambda _seconds: None,
        retry_delays=(0,),
        max_bytes_per_second=None,
    )

    assert destination.read_bytes() == b"abcdef"
    assert not destination.with_suffix(destination.suffix + ".part").exists()
    assert result.bytes_downloaded == 6
    assert len(requests) == 2
    assert requests[0][0].get_header("Range") is None
    assert requests[1][0].get_header("Range") == "bytes=3-"
    assert "HallsOfKnowledge/0.1" in requests[0][0].get_header("User-agent")
    assert "operator@example.com" in requests[0][0].get_header("User-agent")


def test_discovery_honors_limit_and_duplicate_titles():
    class Catalog:
        def articles(self, category, limit):
            return [
                CandidatePage(page_id=1, title="Gandalf"),
                CandidatePage(page_id=2, title="gandalf"),
                CandidatePage(page_id=3, title="Aragorn"),
            ]

    result = discover_candidates(
        DiscoveryRequest(
            categories=("One", "Two"),
            nominations=("Legolas",),
            max_candidates=2,
        ),
        catalog=Catalog(),
        observed_at=datetime(2026, 8, 12, tzinfo=UTC),
    )

    assert [record.observed_page_title for record in result.records] == ["Gandalf", "Aragorn"]


def test_download_validates_inputs_and_returns_an_existing_dump(tmp_path):
    expected = SourceSnapshot.initial(retrieved_at="").filename
    with pytest.raises(ValueError, match="destination must end"):
        download_initial_dump(tmp_path / "wrong.bz2", contact="mailto:operator@example.com")
    with pytest.raises(ValueError, match="contact must be"):
        _contact_user_agent("not-a-contact")

    destination = tmp_path / expected
    destination.write_bytes(b"already downloaded")
    result = download_initial_dump(destination, contact="mailto:operator@example.com")

    assert result.path == destination
    assert result.bytes_downloaded == len(b"already downloaded")
    assert result.resumed is False


def test_download_throttles_and_retries_retryable_http_errors(tmp_path, monkeypatch):
    expected = SourceSnapshot.initial(retrieved_at="").filename
    destination = tmp_path / expected
    headers = Message()
    headers["Retry-After"] = "2"
    attempts = iter(
        [
            HTTPError("https://example.test", 429, "slow down", headers, None),
            StubResponse(b"ab", status=200, headers={"Content-Length": "2"}),
        ]
    )
    sleeps = []
    monotonic = iter((0.0, 0.0))
    monkeypatch.setattr(
        "middle_earth_travel_agency.corpus_acquisition.time.monotonic",
        lambda: next(monotonic),
    )

    def open_request(*_args, **_kwargs):
        attempt = next(attempts)
        if isinstance(attempt, Exception):
            raise attempt
        return attempt

    result = download_initial_dump(
        destination,
        contact="mailto:operator@example.com",
        open_request=open_request,
        sleep=sleeps.append,
        retry_delays=(1,),
        max_bytes_per_second=1,
    )

    assert result.resumed is True
    assert sleeps == [2.0, 2.0]


def test_download_raises_after_retry_budget_is_exhausted(tmp_path):
    destination = tmp_path / SourceSnapshot.initial(retrieved_at="").filename

    with pytest.raises(URLError, match="offline"):
        download_initial_dump(
            destination,
            contact="mailto:operator@example.com",
            open_request=lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
            sleep=lambda _seconds: None,
            retry_delays=(),
        )


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        (
            "<mediawiki><siteinfo><dbname>other</dbname></siteinfo></mediawiki>",
            "expected wiki database",
        ),
        (
            "<mediawiki><page><title>Early</title></page></mediawiki>",
            "before required site database",
        ),
        ("<mediawiki></mediawiki>", "lacks required site database"),
    ],
)
def test_dump_reader_rejects_missing_or_wrong_database_identity(tmp_path, xml, message):
    dump = tmp_path / "dump.bz2"
    dump.write_bytes(bz2.compress(xml.encode()))

    with pytest.raises(ValueError, match=message):
        list(_iter_dump_pages(dump, expected_database="enwiki"))


def test_redirect_and_extraction_helpers_cover_conservative_boundaries(tmp_path):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE redirects (source_key TEXT PRIMARY KEY, target_title TEXT)")
    connection.executemany("INSERT INTO redirects VALUES (?, ?)", (("One", "Two"), ("Two", "One")))
    with pytest.raises(ValueError, match="redirect loop"):
        _resolve_redirect(connection, "One")
    connection.close()

    blocks = list(_blocks("Lead text\n== History ==\nFirst.\n\nSecond."))
    assert blocks == [
        (["Lead"], 1, "Lead text"),
        (["History"], 1, "First."),
        (["History"], 2, "Second."),
    ]
    assert _classify_block(["References"], "Prose") == "reference or administrative material"
    assert _classify_block(["History"], "{| table |}") == "table"
    assert _classify_block(["History"], "<poem>verse</poem>") == "block quotation"
    assert _normalize_prose("Text<ref>citation</ref> remains.") == "Text remains."

    retained = tmp_path / "artifact.json"
    _write_immutable_json(retained, {"identity": 1})
    with pytest.raises(FileExistsError, match="identity collision"):
        _write_immutable_json(retained, {"identity": 2})

    wrong_dump = tmp_path / "wrong-name.bz2"
    wrong_dump.write_bytes(b"")
    with pytest.raises(ValueError, match="expected dump filename"):
        extract_article_artifacts(
            wrong_dump,
            discoveries=(),
            output_dir=tmp_path / "articles",
            source=SourceSnapshot.initial(retrieved_at="2026-08-12T00:00:00+00:00"),
        )
