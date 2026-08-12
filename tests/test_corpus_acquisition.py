import bz2
import io
import json
from datetime import UTC, datetime

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
