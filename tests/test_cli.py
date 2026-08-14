import json
from types import SimpleNamespace

import pytest

from middle_earth_travel_agency import cli
from middle_earth_travel_agency.cli import main
from middle_earth_travel_agency.corpus_acquisition import AcquisitionSuccess, SourceSnapshot


def _write_discoveries(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": [
                    {
                        "discovery_route": "human nomination",
                        "discovery_reference": "operator nomination",
                        "observed_page_title": "Gandalf",
                        "observed_page_id": None,
                        "discovery_timestamp": "2026-08-12T12:00:00+00:00",
                    }
                ],
            }
        )
    )


def test_nomination_discovery_command_writes_repeatable_schema(tmp_path):
    output = tmp_path / "discovery.json"

    status = main(
        [
            "corpus",
            "discover",
            "--nominate",
            "Gandalf",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    document = json.loads(output.read_text())
    assert document["schema_version"] == 1
    assert document["records"][0]["observed_page_title"] == "Gandalf"
    assert document["records"][0]["discovery_route"] == "human nomination"


def test_category_discovery_loads_contact_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("META_WIKIMEDIA_CONTACT", raising=False)
    (tmp_path / ".env").write_text("META_WIKIMEDIA_CONTACT=mailto:operator@example.test\n")
    observed = {}

    class Catalog:
        def __init__(self, *, contact, minimum_request_interval):
            observed["contact"] = contact

        def articles(self, category, limit):
            return ()

    monkeypatch.setattr(cli, "PywikibotCatalog", Catalog)

    status = main(
        [
            "corpus",
            "discover",
            "--category",
            "Category:Middle-earth",
            "--output",
            str(tmp_path / "discovery.json"),
        ]
    )

    assert status == 0
    assert observed["contact"] == "mailto:operator@example.test"


def test_curation_command_requires_tty_before_opening_state(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)

    with pytest.raises(ValueError, match="interactive TTY"):
        main(
            [
                "corpus",
                "curate",
                "--articles-dir",
                str(tmp_path / "articles"),
                "--state-db",
                str(tmp_path / "state.sqlite"),
            ]
        )

    assert not (tmp_path / "state.sqlite").exists()


def test_acquire_command_records_new_and_repeat_results(tmp_path, monkeypatch, capsys):
    discoveries = tmp_path / "discoveries.json"
    _write_discoveries(discoveries)
    dump = tmp_path / SourceSnapshot.initial(retrieved_at="").filename
    dump.write_bytes(b"pinned dump fixture")
    data_dir = tmp_path / "corpus"
    observed = []

    def extract(dump_path, *, discoveries, output_dir, source, progress):
        observed.append((dump_path, tuple(discoveries), output_dir, source))
        progress(1, 0)
        progress(1, 123)
        return SimpleNamespace(
            scan_passes=1,
            successes=(AcquisitionSuccess("Gandalf", "article-gandalf"),),
            failures=(),
        )

    monkeypatch.setattr(cli, "extract_article_artifacts", extract)
    arguments = [
        "corpus",
        "acquire",
        "--discoveries",
        str(discoveries),
        "--data-dir",
        str(data_dir),
        "--dump-path",
        str(dump),
        "--retrieved-at",
        "2026-08-12T12:30:00+00:00",
    ]

    assert main(arguments) == 0
    assert main(arguments) == 0

    assert len(observed) == 2
    assert observed[0][0] == dump
    assert observed[0][2] == data_dir / "articles"
    assert (
        json.loads((data_dir / "source" / "source-snapshot.json").read_text())[
            "retrieval_timestamp"
        ]
        == "2026-08-12T12:30:00+00:00"
    )
    results = sorted(data_dir.glob("acquisition-result*.json"))
    assert len(results) == 2
    assert json.loads(results[0].read_text())["successes"][0]["candidate_title"] == "Gandalf"
    output = capsys.readouterr().out
    assert "starting extraction pass 1" in output
    assert "scanned 123 pages" in output


def test_acquire_command_downloads_missing_pinned_dump(tmp_path, monkeypatch):
    discoveries = tmp_path / "discoveries.json"
    _write_discoveries(discoveries)
    data_dir = tmp_path / "corpus"
    downloaded = {}

    def download(destination, *, contact, max_bytes_per_second):
        downloaded.update(
            destination=destination,
            contact=contact,
            max_bytes_per_second=max_bytes_per_second,
        )
        destination.write_bytes(b"downloaded fixture")

    monkeypatch.setattr(cli, "download_initial_dump", download)
    monkeypatch.setattr(
        cli,
        "extract_article_artifacts",
        lambda *args, **kwargs: SimpleNamespace(scan_passes=1, successes=(), failures=()),
    )

    assert (
        main(
            [
                "corpus",
                "acquire",
                "--discoveries",
                str(discoveries),
                "--data-dir",
                str(data_dir),
                "--contact",
                "mailto:operator@example.test",
                "--download-rate-mib",
                "8",
            ]
        )
        == 0
    )

    assert downloaded["destination"].name == SourceSnapshot.initial(retrieved_at="").filename
    assert downloaded["contact"] == "mailto:operator@example.test"
    assert downloaded["max_bytes_per_second"] == 8 * 1024 * 1024


@pytest.mark.parametrize(
    ("document", "extra", "message"),
    [
        ({"schema_version": 1, "records": []}, [], "empty candidate"),
        ({"schema_version": 2, "records": []}, [], "unsupported discovery"),
        (
            {"schema_version": 1, "records": [{}]},
            ["--download-rate-mib", "0"],
            "download rate",
        ),
    ],
)
def test_acquire_command_rejects_invalid_inputs(tmp_path, document, extra, message):
    discoveries = tmp_path / "discoveries.json"
    discoveries.write_text(json.dumps(document))

    with pytest.raises(
        (TypeError, ValueError), match=message if message != "download rate" else None
    ):
        main(
            [
                "corpus",
                "acquire",
                "--discoveries",
                str(discoveries),
                "--data-dir",
                str(tmp_path / "corpus"),
                *extra,
            ]
        )


def test_curation_command_runs_and_closes_state(tmp_path, monkeypatch):
    corpus = object()
    closed = []
    observed = {}

    class State:
        def __init__(self, path, loaded_corpus):
            observed["state"] = (path, loaded_corpus)

        def close(self):
            closed.append(True)

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(cli, "load_corpus", lambda path: corpus)
    monkeypatch.setattr(cli, "CurationState", State)
    monkeypatch.setattr(
        cli,
        "run_terminal",
        lambda state, *, review_deferred: observed.update(terminal=(state, review_deferred)),
    )

    state_path = tmp_path / "state.sqlite"
    assert (
        main(
            [
                "corpus",
                "curate",
                "--articles-dir",
                str(tmp_path / "articles"),
                "--state-db",
                str(state_path),
                "--review-deferred",
            ]
        )
        == 0
    )
    assert observed["state"] == (state_path, corpus)
    assert observed["terminal"][1] is True
    assert closed == [True]


def test_curation_snapshot_commands_delegate_and_report(tmp_path, monkeypatch, capsys):
    snapshot = tmp_path / "curation.jsonl"
    database = tmp_path / "curation.sqlite"
    observed = []
    result = SimpleNamespace(audit_events=7, metadata_records=2)
    monkeypatch.setattr(
        cli, "export_snapshot", lambda source, output: observed.append((source, output)) or result
    )
    monkeypatch.setattr(
        cli, "load_snapshot", lambda source, output: observed.append((source, output)) or result
    )

    assert (
        main(
            [
                "corpus",
                "export-curation",
                "--state-db",
                str(database),
                "--output",
                str(snapshot),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "corpus",
                "load-curation",
                "--input",
                str(snapshot),
                "--state-db",
                str(database),
            ]
        )
        == 0
    )
    assert observed == [(database, snapshot), (snapshot, database)]
    output = capsys.readouterr().out
    assert "exported 7 audit event(s)" in output
    assert "loaded 7 audit event(s)" in output


def test_console_reports_expected_operator_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "main", lambda: (_ for _ in ()).throw(ValueError("bad input")))

    with pytest.raises(SystemExit) as error:
        cli.console()

    assert error.value.code == 1
    assert "error: bad input" in capsys.readouterr().err


def test_cli_validation_rejects_unsafe_discovery_and_acquisition_inputs(tmp_path):
    assert tuple(cli._EmptyCatalog().articles("unused", 1)) == ()
    existing = tmp_path / "existing.json"
    existing.write_text("{}")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        cli._write_new_json(existing, {})

    discover = SimpleNamespace(
        category=[],
        nominate=[],
        max_candidates=100,
        contact=None,
        minimum_request_interval=1.0,
        output=tmp_path / "output.json",
    )
    with pytest.raises(ValueError, match="at least one"):
        cli._discover(discover)
    discover.nominate = ["Gandalf"]
    discover.max_candidates = 0
    with pytest.raises(ValueError, match="between 1 and 500"):
        cli._discover(discover)
    discover.max_candidates = 100
    discover.nominate = []
    discover.category = [f"Category {index}" for index in range(21)]
    with pytest.raises(ValueError, match="at most 20"):
        cli._discover(discover)
    discover.category = ["Middle-earth"]
    with pytest.raises(ValueError, match="--contact"):
        cli._discover(discover)

    discoveries = tmp_path / "discoveries.json"
    _write_discoveries(discoveries)
    acquire = SimpleNamespace(
        discoveries=discoveries,
        data_dir=tmp_path / "corpus",
        download_rate_mib=0,
        dump_path=None,
        retrieved_at=None,
        contact=None,
    )
    with pytest.raises(ValueError, match="download rate"):
        cli._acquire(acquire)
    acquire.download_rate_mib = 16
    acquire.dump_path = tmp_path / "supplied.bz2"
    with pytest.raises(ValueError, match="--retrieved-at"):
        cli._acquire(acquire)
    acquire.retrieved_at = "2026-08-12T12:00:00"
    with pytest.raises(ValueError, match="include a timezone"):
        cli._acquire(acquire)
    acquire.retrieved_at = "2026-08-12T12:00:00+00:00"
    with pytest.raises(ValueError, match="dump path must end"):
        cli._acquire(acquire)
    acquire.dump_path = None
    acquire.retrieved_at = None
    with pytest.raises(ValueError, match="--contact"):
        cli._acquire(acquire)
