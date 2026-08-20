import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest

from middle_earth_travel_agency.corpus_curation import CurationState, load_corpus
from middle_earth_travel_agency.corpus_release import create_release
from middle_earth_travel_agency.curation_snapshot import export_snapshot
from middle_earth_travel_agency.retrieval_index import build_index, open_index


@dataclass(frozen=True)
class IndexSettings:
    tokenizer: str = "unicode61"
    remove_diacritics: int = 2


@dataclass(frozen=True)
class RetrievalSettings:
    query_mode: str = "all-terms"
    result_limit: int = 5
    title_weight: float = 5.0
    heading_weight: float = 2.0
    body_weight: float = 1.0
    tie_breaker: str = "passage-id"


@dataclass(frozen=True)
class Config:
    config_identity: str = "test-config"
    index_identity: str = "test-index"
    index: IndexSettings = IndexSettings()
    retrieval: RetrievalSettings = RetrievalSettings()


def _article(article_id, title, passages):
    return {
        "article_artifact_id": article_id,
        "canonical_title": title,
        "extracted_passages": passages,
        "page_id": 1,
        "revision_id": 2,
        "revision_timestamp": "2026-08-01T00:00:00Z",
        "source_snapshot": {
            "dump_run": "test",
            "extraction_profile": "test",
            "filename": "test.xml",
            "retrieval_timestamp": "2026-08-01T00:00:00Z",
            "source_url": "https://example.test/test.xml",
            "wiki_database": "enwiki",
        },
    }


def _passage(article_id, passage_id, ordinal, text, heading=("History",)):
    return {
        "article_artifact_id": article_id,
        "passage_id": passage_id,
        "heading_path": list(heading),
        "paragraph_ordinal": ordinal,
        "normalized_text": text,
    }


def _release(tmp_path):
    articles = tmp_path / "source"
    articles.mkdir()
    (articles / "gondor.json").write_text(
        json.dumps(
            _article(
                "gondor",
                "Góndor",
                [
                    _passage("gondor", "lore-first", 1, "Minas Tirith has seven circles."),
                    _passage("gondor", "excluded", 2, "Editorial note omitted."),
                    _passage("gondor", "lore-third", 3, "The White Tree stood in the court."),
                    _passage("gondor", "lore-fourth", 4, "The court held a fountain."),
                    _passage("gondor", "other-section", 1, "Stewards ruled Gondor.", ("Rule",)),
                    _passage("gondor", "gap-first", 1, "A gap begins here.", ("Gap",)),
                    _passage("gondor", "gap-third", 3, "A gap ends here.", ("Gap",)),
                ],
            )
        )
    )
    corpus = load_corpus(articles)
    state_path = tmp_path / "curation.sqlite"
    state = CurationState(state_path, corpus)
    for passage in corpus.passages:
        state.record(
            passage.passage_id,
            "l" if passage.passage_id != "excluded" else "r",
            "q",
            passage.text,
        )
    state.close()
    snapshot = tmp_path / "curation.jsonl"
    export_snapshot(state_path, snapshot)
    manifest = tmp_path / "release" / "manifest.json"
    create_release(
        release_id="corpus-test", articles_dir=articles, curation_snapshot=snapshot, output=manifest
    )
    return manifest


def test_projects_only_admitted_lore_and_searches_titles_headings_and_bodies(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index?#.sqlite"
    build = build_index(manifest=manifest, output=output, config=Config())

    assert build.metadata.release_id == "corpus-test"
    assert build.metadata.passage_count == 6
    assert output.is_file()
    with open_index(manifest=manifest, index=output, config=Config()) as index:
        title_results = index.search("gondor")
        assert len(title_results) == 5
        assert all(result.passage.title == "Góndor" for result in title_results)
        assert "excluded" not in {result.passage_id for result in title_results}
        assert {result.passage_id for result in index.search("History")} == {
            "lore-first",
            "lore-third",
            "lore-fourth",
        }
        assert [result.passage_id for result in index.search("White Tree")] == ["lore-third"]
        assert index.search("editorial") == []
        assert index.search("History")[0].passage.heading_path == ("History",)


def test_context_does_not_expose_unavailable_text_or_cross_section_boundaries(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index.sqlite"
    build_index(manifest=manifest, output=output, config=Config())

    with open_index(manifest=manifest, index=output, config=Config()) as index:
        first = index.context("lore-first")
        assert first.before is None
        assert first.before_boundary == "section-edge"
        assert first.after is None
        assert first.after_boundary == "non-lore-or-excluded"
        third = index.context("lore-third")
        assert third.before is None
        assert third.before_boundary == "non-lore-or-excluded"
        assert third.after is not None
        assert third.after.passage_id == "lore-fourth"
        assert third.after_boundary is None
        fourth = index.context("lore-fourth")
        assert fourth.before is not None
        assert fourth.before.passage_id == "lore-third"
        assert fourth.after is None
        assert fourth.after_boundary == "section-edge"
        gap = index.context("gap-first")
        assert gap.after is None
        assert gap.after_boundary == "ordinal-gap"
        with pytest.raises(ValueError, match="unknown lore"):
            index.context("excluded")


def test_safe_all_terms_and_any_terms_queries_and_readonly_compatibility(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index.sqlite"
    build_index(manifest=manifest, output=output, config=Config())
    any_terms = Config(
        config_identity="any-test-config",
        index_identity="any-test-index",
        retrieval=RetrievalSettings(query_mode="any-terms"),
    )

    with open_index(manifest=manifest, index=output, config=Config()) as index:
        assert index.search('Minas "Tree"') == []
    any_output = tmp_path / "any-index.sqlite"
    build_index(manifest=manifest, output=any_output, config=any_terms)
    with open_index(manifest=manifest, index=any_output, config=any_terms) as index:
        assert {result.passage_id for result in index.search("Minas Tree")} == {
            "lore-first",
            "lore-third",
        }
        with pytest.raises(sqlite3.OperationalError):
            index._connection.execute("INSERT INTO passages(passage_id) VALUES ('nope')")


def test_refuses_existing_destinations_and_tampered_or_incompatible_indexes(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index.sqlite"
    build_index(manifest=manifest, output=output, config=Config())

    with pytest.raises(FileExistsError, match="overwrite"):
        build_index(manifest=manifest, output=output, config=Config())
    with pytest.raises(ValueError, match="configuration"):
        open_index(manifest=manifest, index=output, config=Config(index_identity="different"))
    connection = sqlite3.connect(output)
    connection.execute("DELETE FROM context_coordinates WHERE passage_id = 'lore-first'")
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="matching lore coordinate"):
        open_index(manifest=manifest, index=output, config=Config())


def test_rejects_tampered_fts_entries_before_exposing_readonly_retrieval(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index.sqlite"
    build_index(manifest=manifest, output=output, config=Config())
    connection = sqlite3.connect(output)
    row = connection.execute(
        "SELECT id, title, heading, body FROM passages WHERE passage_id = 'lore-first'"
    ).fetchone()
    assert row is not None
    connection.execute(
        """INSERT INTO passages_fts(passages_fts, rowid, title, heading, body)
           VALUES ('delete', ?, ?, ?, ?)""",
        row,
    )
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="FTS integrity"):
        open_index(manifest=manifest, index=output, config=Config())


def test_concurrent_builders_publish_at_most_one_complete_index(tmp_path):
    manifest = _release(tmp_path)
    output = tmp_path / "index.sqlite"

    def build():
        try:
            return build_index(manifest=manifest, output=output, config=Config())
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        builds = list(executor.map(lambda _: build(), range(2)))

    assert sum(build is not None for build in builds) == 1
    with open_index(manifest=manifest, index=output, config=Config()) as index:
        assert [result.passage_id for result in index.search("White Tree")] == ["lore-third"]
