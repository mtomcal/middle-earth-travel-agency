import json

import pytest

from middle_earth_travel_agency.corpus_curation import CurationState, load_corpus
from middle_earth_travel_agency.corpus_release import create_release, validate_release
from middle_earth_travel_agency.curation_snapshot import export_snapshot


SOURCE_SNAPSHOT = {
    "dump_run": "20260701",
    "extraction_profile": "test profile",
    "filename": "enwiki-test.xml.bz2",
    "retrieval_timestamp": "2026-08-18T00:00:00+00:00",
    "source_url": "https://example.test/enwiki-test.xml.bz2",
    "wiki_database": "enwiki",
}


def _passage(article_id, passage_id, text):
    return {
        "article_artifact_id": article_id,
        "heading_path": ["History"],
        "normalized_text": text,
        "paragraph_ordinal": 1,
        "passage_id": passage_id,
    }


def _article(article_id, title, passages, *, source=SOURCE_SNAPSHOT):
    return {
        "article_artifact_id": article_id,
        "canonical_title": title,
        "extracted_passages": passages,
        "page_id": 10 if article_id == "article-alpha" else 20,
        "revision_id": 100 if article_id == "article-alpha" else 200,
        "revision_timestamp": "2026-08-01T00:00:00Z",
        "source_snapshot": source,
    }


def _write_article(directory, filename, document):
    directory.mkdir(exist_ok=True)
    (directory / filename).write_text(json.dumps(document, sort_keys=True))


def _curation_snapshot(tmp_path, articles, decisions):
    corpus = load_corpus(articles)
    state_path = tmp_path / "curation.sqlite"
    state = CurationState(state_path, corpus)
    for passage in corpus.passages:
        key = decisions.get(passage.passage_id)
        if key is not None:
            state.record(passage.passage_id, key, "question", passage.text)
    state.close()
    snapshot = tmp_path / "curation.jsonl"
    export_snapshot(state_path, snapshot)
    return snapshot


def test_creates_repeatable_manifest_with_only_lore_bearing_articles(tmp_path):
    articles = tmp_path / "articles"
    _write_article(
        articles,
        "alpha.json",
        _article(
            "article-alpha",
            "Alpha",
            [
                _passage("article-alpha", "alpha-lore", "Lore."),
                _passage("article-alpha", "alpha-analysis", "Analysis."),
            ],
        ),
    )
    _write_article(
        articles,
        "beta.json",
        _article(
            "article-beta",
            "Beta",
            [_passage("article-beta", "beta-reference", "Reference.")],
        ),
    )
    snapshot = _curation_snapshot(
        tmp_path,
        articles,
        {"alpha-lore": "l", "alpha-analysis": "a", "beta-reference": "r"},
    )
    first = tmp_path / "first" / "manifest.json"
    second = tmp_path / "second" / "manifest.json"

    result = create_release(
        release_id="corpus-v1-rc1",
        articles_dir=articles,
        curation_snapshot=snapshot,
        output=first,
    )
    create_release(
        release_id="corpus-v1-rc1",
        articles_dir=articles,
        curation_snapshot=snapshot,
        output=second,
    )

    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / "curation.jsonl").read_bytes() == snapshot.read_bytes()
    assert result.article_count == 1
    assert result.passage_count == 1
    document = json.loads(first.read_text())
    assert document["selection_policy"] == "all lore-bearing articles"
    assert document["counts"] == {"articles": 1, "lore_passages": 1}
    assert [article["canonical_title"] for article in document["articles"]] == ["Alpha"]
    assert document["articles"][0]["lore_passage_ids"] == ["alpha-lore"]
    assert document["source_snapshot"] == SOURCE_SNAPSHOT
    assert (
        validate_release(
            manifest=first,
            articles_dir=articles,
            curation_snapshot=first.parent / "curation.jsonl",
        )
        == result
    )


@pytest.mark.parametrize(("decision", "message"), [(None, "undecided"), ("s", "deferred")])
def test_rejects_incomplete_curation(tmp_path, decision, message):
    articles = tmp_path / "articles"
    _write_article(
        articles,
        "alpha.json",
        _article(
            "article-alpha",
            "Alpha",
            [_passage("article-alpha", "alpha", "Alpha passage.")],
        ),
    )
    decisions = {} if decision is None else {"alpha": decision}
    snapshot = _curation_snapshot(tmp_path, articles, decisions)

    with pytest.raises(ValueError, match=message):
        create_release(
            release_id="corpus-v1-rc1",
            articles_dir=articles,
            curation_snapshot=snapshot,
            output=tmp_path / "release" / "manifest.json",
        )


def test_validation_rejects_tampering_and_creation_refuses_overwrite(tmp_path):
    articles = tmp_path / "articles"
    _write_article(
        articles,
        "alpha.json",
        _article(
            "article-alpha",
            "Alpha",
            [_passage("article-alpha", "alpha", "Alpha passage.")],
        ),
    )
    snapshot = _curation_snapshot(tmp_path, articles, {"alpha": "l"})
    manifest = tmp_path / "release" / "manifest.json"
    arguments = {
        "release_id": "corpus-v1-rc1",
        "articles_dir": articles,
        "curation_snapshot": snapshot,
        "output": manifest,
    }
    create_release(**arguments)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        create_release(**arguments)

    document = json.loads(manifest.read_text())
    document["counts"]["lore_passages"] = 2
    manifest.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="does not match"):
        validate_release(
            manifest=manifest,
            articles_dir=articles,
            curation_snapshot=manifest.parent / "curation.jsonl",
        )


def test_rejects_invalid_release_id_and_mixed_source_snapshots(tmp_path):
    articles = tmp_path / "articles"
    _write_article(
        articles,
        "alpha.json",
        _article(
            "article-alpha",
            "Alpha",
            [_passage("article-alpha", "alpha", "Alpha passage.")],
        ),
    )
    other_source = {**SOURCE_SNAPSHOT, "dump_run": "20260801"}
    _write_article(
        articles,
        "beta.json",
        _article(
            "article-beta",
            "Beta",
            [_passage("article-beta", "beta", "Beta passage.")],
            source=other_source,
        ),
    )
    snapshot = _curation_snapshot(tmp_path, articles, {"alpha": "l", "beta": "r"})

    with pytest.raises(ValueError, match="release id"):
        create_release(
            release_id="Corpus V1",
            articles_dir=articles,
            curation_snapshot=snapshot,
            output=tmp_path / "bad-id" / "manifest.json",
        )
    with pytest.raises(ValueError, match="one source snapshot"):
        create_release(
            release_id="corpus-v1-rc1",
            articles_dir=articles,
            curation_snapshot=snapshot,
            output=tmp_path / "mixed" / "manifest.json",
        )
