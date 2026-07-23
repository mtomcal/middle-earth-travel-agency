"""Tests for the deterministic corpus backup capability.

Each test exercises one operator-visible behavior at a public seam:
``halls_of_knowledge.corpus_backup.create_backup``,
``halls_of_knowledge.corpus_backup.verify_backup``, and the two
``hok corpus`` subcommands. The tests construct a canonical corpus fixture
on disk, then assert the contract advertised in the spec.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from halls_of_knowledge import corpus_backup
from halls_of_knowledge.cli import main
from halls_of_knowledge.corpus_backup import (
    ARCHIVE_BASENAME_PREFIX,
    ARCHIVE_SUFFIX,
    BackupError,
    BackupResult,
    create_backup,
    verify_backup,
)


def _archive_path(directory: Path, label: str) -> Path:
    return directory / f"{ARCHIVE_BASENAME_PREFIX}-{label}{ARCHIVE_SUFFIX}"


def _sidecar_path(directory: Path, label: str) -> Path:
    return directory / f"{ARCHIVE_BASENAME_PREFIX}-{label}{ARCHIVE_SUFFIX}.sha256"


# --------------------------------------------------------------------------- #
# Canonical fixture                                                           #
# --------------------------------------------------------------------------- #


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        text = str(payload)
    path.write_text(text)


def _source_snapshot() -> dict[str, str]:
    return {
        "wiki_database": "enwiki",
        "dump_run": "20260701",
        "filename": "enwiki-20260701-pages-articles.xml.bz2",
        "source_url": (
            "https://dumps.wikimedia.org/enwiki/20260701/enwiki-20260701-pages-articles.xml.bz2"
        ),
        "retrieval_timestamp": "2026-07-20T12:30:00+00:00",
        "extraction_profile": "full non-multistream article dump",
    }


def _article(*, artifact_id: str, title: str, page_id: int, revision_id: int) -> dict[str, object]:
    src = _source_snapshot()
    return {
        "article_artifact_id": artifact_id,
        "wiki_database": src["wiki_database"],
        "dump_run": src["dump_run"],
        "source_snapshot": src,
        "page_id": page_id,
        "namespace": 0,
        "canonical_title": title,
        "redirect_chain": [],
        "revision_id": revision_id,
        "parent_revision_id": revision_id - 1,
        "revision_timestamp": "2026-06-30T10:00:00Z",
        "permanent_revision_url": f"https://en.wikipedia.org/w/index.php?oldid={revision_id}",
        "history_url": f"https://en.wikipedia.org/w/index.php?title={title}&action=history",
        "raw_wikitext": f"'''{title}''' was in Middle-earth.",
        "extractor_identity": "mwparserfromhell 0.7.4",
        "extractor_configuration": {"supported_structure": "prose paragraphs"},
        "extracted_passages": [
            {
                "passage_id": f"passage_{artifact_id}_1",
                "article_artifact_id": artifact_id,
                "heading_path": ["Lead"],
                "paragraph_ordinal": 1,
                "normalized_text": f"{title} was in Middle-earth.",
                "structure": "prose paragraph",
            }
        ],
        "structural_exclusions": [],
    }


def _seed_canonical(repo: Path) -> None:
    """Write the minimal canonical corpus tree at <repo>/data/."""
    data = repo / "data"
    src = _source_snapshot()
    _write(
        data / "discovery" / "initial.json",
        {
            "schema_version": 1,
            "records": [
                {
                    "discovery_route": "category or API",
                    "discovery_reference": "https://en.wikipedia.org/wiki/Category:Middle-earth",
                    "observed_page_title": "Gandalf",
                    "observed_page_id": 1,
                    "discovery_timestamp": "2026-07-20T12:00:00+00:00",
                },
            ],
        },
    )
    _write(data / "corpus" / "source" / "source-snapshot.json", src)
    _write(
        data / "corpus" / "acquisition-result.json",
        {
            "schema_version": 1,
            "source_snapshot": src,
            "scan_passes": 2,
            "successes": [
                {"candidate_title": "Gandalf", "article_artifact_id": "article_aaa"},
                {"candidate_title": "Mithrandir", "article_artifact_id": "article_bbb"},
            ],
            "failures": [],
        },
    )
    _write(
        data / "corpus" / "articles" / "article_aaa.json",
        _article(artifact_id="article_aaa", title="Gandalf", page_id=1, revision_id=100),
    )
    _write(
        data / "corpus" / "articles" / "article_bbb.json",
        _article(artifact_id="article_bbb", title="Mithrandir", page_id=2, revision_id=101),
    )


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _init_git(repo: Path) -> str:
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "config", "user.email", "t@e.test")
    _git(repo, "config", "user.name", "tester")
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "seed")
    return _git(repo, "rev-parse", "HEAD")


# --------------------------------------------------------------------------- #
# Public-seam tests                                                           #
# --------------------------------------------------------------------------- #


def test_create_backup_then_verify_succeeds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    head = _init_git(repo)
    out = tmp_path / "backups"

    result = create_backup(repo, label="release-2026-07-20", output_dir=out)

    assert isinstance(result, BackupResult)
    assert result.git_head == head
    archive = _archive_path(out, "release-2026-07-20")
    sidecar = _sidecar_path(out, "release-2026-07-20")
    assert archive.is_file() and sidecar.is_file()

    sidecar_text = sidecar.read_text().strip()
    digest, _, name = sidecar_text.partition("  ")
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert name == archive.name

    verify_backup(archive)  # does not raise on a valid archive


def test_backup_is_byte_deterministic_for_same_inputs(tmp_path: Path, monkeypatch) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _seed_canonical(a)
    _seed_canonical(b)
    _init_git(a)
    _init_git(b)
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    # Force both repos to report the same HEAD so the manifest is identical
    # (the GIT HEAD is the only material difference between two otherwise
    # identical repos).
    fixed_head = "0" * 40
    monkeypatch.setattr(
        corpus_backup,
        "_run_git",
        lambda _repo, *args: fixed_head if args == ("rev-parse", "HEAD") else "",
    )

    create_backup(a, label="same", output_dir=out_a)
    create_backup(b, label="same", output_dir=out_b)

    assert _archive_path(out_a, "same").read_bytes() == _archive_path(out_b, "same").read_bytes()
    assert _sidecar_path(out_a, "same").read_text() == _sidecar_path(out_b, "same").read_text()


def test_archive_members_are_sorted_and_normalized(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    out = tmp_path / "backups"

    create_backup(repo, label="normalized", output_dir=out)
    archive = _archive_path(out, "normalized")
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            assert member.uid == 0 and member.gid == 0
            assert member.uname == "" and member.gname == ""
            assert member.mtime == 0
            assert oct(member.mode) == oct(0o644)
    assert names == sorted(names)


def test_manifest_records_label_head_source_and_digests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    head = _init_git(repo)
    out = tmp_path / "backups"

    create_backup(repo, label="manifest", output_dir=out)
    archive = _archive_path(out, "manifest")
    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(
            tar.extractfile("backup-manifest.json").read().decode()  # type: ignore[union-attr]
        )

    assert manifest["schema_version"] == 1
    assert manifest["label"] == "manifest"
    assert manifest["git_head"] == head
    assert manifest["source_snapshot"]["wiki_database"] == "enwiki"
    assert manifest["source_snapshot"]["dump_run"] == "20260701"

    members = {entry["path"]: entry for entry in manifest["members"]}
    expected = {
        "data/discovery/initial.json",
        "data/corpus/source/source-snapshot.json",
        "data/corpus/acquisition-result.json",
        "data/corpus/articles/article_aaa.json",
        "data/corpus/articles/article_bbb.json",
    }
    assert set(members) == expected
    for path, entry in members.items():
        on_disk = (repo / path).read_bytes()
        assert entry["size_bytes"] == len(on_disk)
        assert entry["sha256"] == hashlib.sha256(on_disk).hexdigest()
    # Backup must not introduce its own wall-clock fields.
    assert "created_at" not in manifest
    assert "generated_at" not in manifest


def test_backup_excludes_secrets_dump_logs_temp_sqlite_and_invalid_runs(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    (repo / ".env").write_text("HOK_WIKIMEDIA_CONTACT=secret@example.test\n")
    (repo / "data" / "corpus" / "source" / "enwiki-20260701-pages-articles.xml.bz2").write_bytes(
        b"huge dump"
    )
    (
        repo / "data" / "corpus" / "source" / "enwiki-20260701-pages-articles.xml.bz2.tmp"
    ).write_bytes(b"part")
    (repo / "hok-redirects-abc").mkdir()
    (repo / "hok-redirects-abc" / "redirects.sqlite3").write_bytes(b"x")
    (repo / "throttle.ctrl").write_text("busy")
    (repo / "logs").mkdir()
    (repo / "logs" / "hok.log").write_text("log")
    (repo / "hok.pid").write_text("42")
    (repo / "data" / "corpus" / "stray.json").write_text('{"unrelated": true}\n')
    _write(
        repo / "data" / "corpus" / "acquisition-result-20260720T120000000Z.json",
        {
            "schema_version": 1,
            "source_snapshot": _source_snapshot(),
            "scan_passes": 2,
            "successes": [],
            "failures": [
                {
                    "candidate_identity": "Bogus",
                    "stage": "source scan",
                    "reason": "absent",
                    "recoverable": True,
                }
            ],
        },
    )

    create_backup(repo, label="exclusions", output_dir=tmp_path / "backups", allow_dirty=True)
    archive = _archive_path(tmp_path / "backups", "exclusions")
    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
    forbidden = {
        ".env",
        "data/corpus/source/enwiki-20260701-pages-articles.xml.bz2",
        "data/corpus/source/enwiki-20260701-pages-articles.xml.bz2.tmp",
        "hok-redirects-abc/redirects.sqlite3",
        "throttle.ctrl",
        "logs/hok.log",
        "hok.pid",
        "data/corpus/stray.json",
        "data/corpus/acquisition-result-20260720T120000000Z.json",
    }
    assert not (forbidden & names), f"forbidden paths in archive: {forbidden & names}"
    assert {
        "data/discovery/initial.json",
        "data/corpus/source/source-snapshot.json",
        "data/corpus/acquisition-result.json",
        "data/corpus/articles/article_aaa.json",
        "data/corpus/articles/article_bbb.json",
        "backup-manifest.json",
    } <= names


def test_backup_accepts_category_seed_discovery_metadata(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    _write(
        repo / "data" / "discovery" / "direct-subcategories.json",
        {
            "schema_version": 1,
            "records": [
                {
                    "source_category": "Category:Middle-earth",
                    "category_title": "Category:Middle-earth characters",
                    "page_id": 42,
                    "timestamp": "2026-07-20T12:00:00+00:00",
                }
            ],
        },
    )
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "seed category metadata")

    create_backup(repo, label="category-seed", output_dir=tmp_path / "backups")

    archive = _archive_path(tmp_path / "backups", "category-seed")
    with tarfile.open(archive, "r:gz") as tar:
        assert "data/discovery/direct-subcategories.json" in tar.getnames()


def test_backup_refuses_dirty_tree_without_allow_dirty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    (repo / "data" / "discovery" / "initial.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": [
                    {
                        "discovery_route": "human nomination",
                        "discovery_reference": "operator",
                        "observed_page_title": "Changed",
                        "observed_page_id": 99,
                        "discovery_timestamp": "2026-07-20T12:00:00+00:00",
                    }
                ],
            }
        )
        + "\n"
    )

    with pytest.raises(BackupError, match="dirty"):
        create_backup(repo, label="dirty", output_dir=tmp_path / "backups")
    assert not (tmp_path / "backups" / "dirty.tar.gz").exists()


def test_backup_records_head_and_proceeds_with_allow_dirty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    head = _init_git(repo)
    (repo / "data" / "discovery" / "initial.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": [
                    {
                        "discovery_route": "human nomination",
                        "discovery_reference": "operator",
                        "observed_page_title": "Changed",
                        "observed_page_id": 99,
                        "discovery_timestamp": "2026-07-20T12:00:00+00:00",
                    }
                ],
            }
        )
        + "\n"
    )

    result = create_backup(repo, label="ok", output_dir=tmp_path / "backups", allow_dirty=True)
    assert result.git_head == head


def test_backup_accepts_a_git_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    worktree = tmp_path / "worktree"
    _git(repo, "worktree", "add", "--detach", str(worktree), "HEAD")
    assert (worktree / ".git").is_file()

    result = create_backup(worktree, label="worktree", output_dir=tmp_path / "backups")

    assert result.archive_path.is_file()


def test_backup_reports_git_executable_unavailable_as_backup_error(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    def _missing_git(*_args, **_kwargs):
        raise FileNotFoundError("git missing")

    monkeypatch.setattr(corpus_backup.subprocess, "run", _missing_git)
    with pytest.raises(BackupError, match="git is unavailable"):
        create_backup(repo, label="nogit", output_dir=tmp_path / "backups")


def test_backup_refuses_to_overwrite_archive_or_sidecar(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    out = tmp_path / "backups"

    create_backup(repo, label="once", output_dir=out)
    archive = _archive_path(out, "once")
    sidecar = _sidecar_path(out, "once")
    original_archive = archive.read_bytes()
    original_sidecar = sidecar.read_text()

    with pytest.raises(BackupError, match="overwrite"):
        create_backup(repo, label="once", output_dir=out)
    assert archive.read_bytes() == original_archive
    assert sidecar.read_text() == original_sidecar
    assert not (out / f"{ARCHIVE_BASENAME_PREFIX}-once{ARCHIVE_SUFFIX}.part").exists()


def test_backup_rejects_unsafe_label(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    for bad in ("../etc/passwd", "with/slash", "with space", "name.tar.gz", ".."):
        with pytest.raises(BackupError):
            create_backup(repo, label=bad, output_dir=tmp_path / "backups")
    assert list((tmp_path / "backups").glob("*.tar.gz")) == []


def test_verify_detects_tampered_archive_bytes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="tamper", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "tamper")
    archive.write_bytes(archive.read_bytes() + b"!")
    with pytest.raises(BackupError, match="sha256"):
        verify_backup(archive)


def test_verify_detects_tampered_sidecar(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="bad-sidecar", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "bad-sidecar")
    sidecar = _sidecar_path(tmp_path / "backups", "bad-sidecar")
    sidecar.write_text("0" * 64 + "  " + archive.name + "\n")
    with pytest.raises(BackupError, match="sha256"):
        verify_backup(archive)


def test_verify_detects_missing_or_extra_members(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="members", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "members")

    rebuilt = tmp_path / "backups" / "members-rebuilt.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(rebuilt, "w:gz") as dst:
        for member in src.getmembers():
            data = src.extractfile(member).read() if member.isfile() else None  # type: ignore[union-attr]
            if member.name == "backup-manifest.json":
                manifest = json.loads(data.decode())
                manifest["members"].append(
                    {
                        "path": "data/corpus/articles/article_ghost.json",
                        "size_bytes": 1,
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                    }
                )
                data = (
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                ).encode()
            new_member = tarfile.TarInfo(name=member.name)
            new_member.size = len(data)
            new_member.mode = 0o644
            new_member.uid = new_member.gid = 0
            new_member.mtime = 0
            dst.addfile(new_member, __import__("io").BytesIO(data))
    rebuilt.replace(archive)
    _sidecar_path(tmp_path / "backups", "members").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError, match="membership"):
        verify_backup(archive)


def test_verify_detects_malformed_or_unsafe_archive(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.tar.gz"
    bogus.write_bytes(b"not a tarball")
    (tmp_path / "bogus.tar.gz.sha256").write_text(
        hashlib.sha256(bogus.read_bytes()).hexdigest() + "  " + bogus.name + "\n"
    )
    with pytest.raises(BackupError):
        verify_backup(bogus)

    unsafe = tmp_path / "unsafe.tar.gz"
    with tarfile.open(unsafe, "w:gz") as tar:
        member = tarfile.TarInfo(name="../escaped.txt")
        member.size = 2
        member.mode = 0o644
        member.uid = member.gid = 0
        member.mtime = 0
        tar.addfile(member, __import__("io").BytesIO(b"hi"))
    (tmp_path / "unsafe.tar.gz.sha256").write_text(
        hashlib.sha256(unsafe.read_bytes()).hexdigest() + "  " + unsafe.name + "\n"
    )
    with pytest.raises(BackupError, match="path-traversal"):
        verify_backup(unsafe)


def test_verify_detects_member_hash_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="mismatch", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "mismatch")

    rebuilt = tmp_path / "backups" / "mismatch-rebuilt.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(rebuilt, "w:gz") as dst:
        import io

        for member in src.getmembers():
            data = src.extractfile(member).read() if member.isfile() else None  # type: ignore[union-attr]
            if member.name == "data/corpus/articles/article_aaa.json":
                payload = json.loads(data.decode())
                # Replace the leading text with a same-length but different
                # string so the byte size and the manifest size stay aligned
                # while the sha256 no longer matches.
                old = payload["raw_wikitext"]
                payload["raw_wikitext"] = "X" * len(old)
                data = (
                    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                ).encode()
            new_member = tarfile.TarInfo(name=member.name)
            new_member.size = len(data)
            new_member.mode = 0o644
            new_member.uid = new_member.gid = 0
            new_member.mtime = 0
            dst.addfile(new_member, io.BytesIO(data))
    rebuilt.replace(archive)
    _sidecar_path(tmp_path / "backups", "mismatch").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError, match="sha256"):
        verify_backup(archive)


def test_backup_rejects_acquisition_result_mismatched_with_artifacts(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    _write(
        repo / "data" / "corpus" / "acquisition-result.json",
        {
            "schema_version": 1,
            "source_snapshot": _source_snapshot(),
            "scan_passes": 2,
            "successes": [
                {"candidate_title": "Gandalf", "article_artifact_id": "article_aaa"},
                {"candidate_title": "Mithrandir", "article_artifact_id": "article_bbb"},
                {"candidate_title": "Sauron", "article_artifact_id": "article_missing"},
            ],
            "failures": [],
        },
    )
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "mismatched")
    with pytest.raises(BackupError, match="not on disk"):
        create_backup(repo, label="mismatch", output_dir=tmp_path / "backups")


def test_backup_rejects_acquisition_with_failures(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    _write(
        repo / "data" / "corpus" / "acquisition-result.json",
        {
            "schema_version": 1,
            "source_snapshot": _source_snapshot(),
            "scan_passes": 2,
            "successes": [{"candidate_title": "Gandalf", "article_artifact_id": "article_aaa"}],
            "failures": [
                {
                    "candidate_identity": "X",
                    "stage": "source scan",
                    "reason": "absent",
                    "recoverable": True,
                }
            ],
        },
    )
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "failures")
    with pytest.raises(BackupError, match="failures"):
        create_backup(repo, label="fails", output_dir=tmp_path / "backups")


def test_backup_rejects_wrong_pinned_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    bad = _source_snapshot()
    bad["dump_run"] = "20990101"
    bad["filename"] = "enwiki-20990101-pages-articles.xml.bz2"
    bad["source_url"] = (
        "https://dumps.wikimedia.org/enwiki/20990101/enwiki-20990101-pages-articles.xml.bz2"
    )
    _write(repo / "data" / "corpus" / "source" / "source-snapshot.json", bad)
    payload = _article(artifact_id="article_aaa", title="Gandalf", page_id=1, revision_id=100)
    payload["source_snapshot"] = bad
    payload["dump_run"] = bad["dump_run"]
    _write(repo / "data" / "corpus" / "articles" / "article_aaa.json", payload)
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "wrong source")
    with pytest.raises(BackupError, match="pinned"):
        create_backup(repo, label="wrong", output_dir=tmp_path / "backups")


def test_backup_rejects_article_with_invalid_passage_structure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    article = _article(artifact_id="article_aaa", title="Gandalf", page_id=1, revision_id=100)
    article["extracted_passages"] = [{"passage_id": "incomplete"}]
    _write(repo / "data" / "corpus" / "articles" / "article_aaa.json", article)
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "bad passage")

    with pytest.raises(BackupError, match="extracted_passages\\[0\\] missing"):
        create_backup(repo, label="bad-passage", output_dir=tmp_path / "backups")


def test_backup_rejects_wrong_namespace(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    payload = _article(artifact_id="article_aaa", title="Gandalf", page_id=1, revision_id=100)
    payload["namespace"] = 14
    _write(repo / "data" / "corpus" / "articles" / "article_aaa.json", payload)
    _git(repo, "add", "-A", "data")
    _git(repo, "commit", "-q", "-m", "wrong namespace")
    with pytest.raises(BackupError, match="namespace"):
        create_backup(repo, label="ns", output_dir=tmp_path / "backups")


# --------------------------------------------------------------------------- #
# Operator entry point                                                        #
# --------------------------------------------------------------------------- #


def test_package_cli_creates_and_verifies_a_backup(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    out = tmp_path / "backups"
    monkeypatch.chdir(repo)

    assert main(["corpus", "backup", "--label", "cli", "--output-dir", str(out)]) == 0
    assert main(["corpus", "verify-backup", str(_archive_path(out, "cli"))]) == 0


def test_create_backup_uses_agreed_archive_basename(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    out = tmp_path / "backups"
    create_backup(repo, label="acquisition-v1", output_dir=out)
    assert (out / "hok-enwiki-20260701-acquisition-v1.tar.gz").is_file()
    assert (out / "hok-enwiki-20260701-acquisition-v1.tar.gz.sha256").is_file()


def test_verify_rejects_evil_member_even_if_manifest_lists_it(
    tmp_path: Path,
) -> None:
    """A manifest entry cannot smuggle a non-allowlisted path into the archive."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="allowlist", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "allowlist")

    rebuilt = tmp_path / "backups" / "allowlist-rebuilt.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(rebuilt, "w:gz") as dst:
        for member in src.getmembers():
            data = src.extractfile(member).read() if member.isfile() else None  # type: ignore[union-attr]
            if member.name == "backup-manifest.json":
                manifest = json.loads(data.decode())
                manifest["members"].append(
                    {
                        "path": "data/evil.txt",
                        "size_bytes": 1,
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                    }
                )
                data = (
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                ).encode()
            new_member = tarfile.TarInfo(name=member.name)
            new_member.size = len(data)
            new_member.mode = 0o644
            new_member.uid = new_member.gid = 0
            new_member.mtime = 0
            dst.addfile(new_member, __import__("io").BytesIO(data))
        # Sneak an extra evil.txt member into the tar so the membership check
        # passes; the allowlist check must still reject it.
        evil = tarfile.TarInfo(name="data/evil.txt")
        evil.size = 1
        evil.mode = 0o644
        evil.uid = evil.gid = 0
        evil.mtime = 0
        dst.addfile(evil, __import__("io").BytesIO(b"x"))
    rebuilt.replace(archive)
    _sidecar_path(tmp_path / "backups", "allowlist").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError, match="allowlist"):
        verify_backup(archive)


def test_verify_rejects_duplicate_tar_member_names(tmp_path: Path) -> None:
    archive = tmp_path / "hok-enwiki-20260701-dupes.tar.gz"
    sidecar = tmp_path / "hok-enwiki-20260701-dupes.tar.gz.sha256"
    with tarfile.open(archive, "w:gz") as dst:
        payload = b"a"
        for _ in range(2):
            info = tarfile.TarInfo(name="data/discovery/x.json")
            info.size = len(payload)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.mtime = 0
            dst.addfile(info, __import__("io").BytesIO(payload))
    sidecar.write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError, match="duplicate"):
        verify_backup(archive)


def test_verify_rejects_unsanitized_manifest_label(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="labelcheck", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "labelcheck")
    rebuilt = tmp_path / "backups" / "labelcheck-rebuilt.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(rebuilt, "w:gz") as dst:
        for member in src.getmembers():
            data = src.extractfile(member).read()  # type: ignore[union-attr]
            if member.name == "backup-manifest.json":
                manifest = json.loads(data.decode())
                manifest["label"] = "contains a space"
                data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.mtime = 0
            dst.addfile(info, __import__("io").BytesIO(data))
    rebuilt.replace(archive)
    _sidecar_path(tmp_path / "backups", "labelcheck").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )

    with pytest.raises(BackupError, match="backup label"):
        verify_backup(archive)


def test_verify_rejects_duplicate_manifest_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    create_backup(repo, label="dupmanifest", output_dir=tmp_path / "backups")
    archive = _archive_path(tmp_path / "backups", "dupmanifest")
    rebuilt = tmp_path / "backups" / "dupmanifest-rebuilt.tar.gz"
    with tarfile.open(archive, "r:gz") as src, tarfile.open(rebuilt, "w:gz") as dst:
        for member in src.getmembers():
            data = src.extractfile(member).read() if member.isfile() else None  # type: ignore[union-attr]
            if member.name == "backup-manifest.json":
                manifest = json.loads(data.decode())
                first = manifest["members"][0]
                manifest["members"].append(first)
                data = (
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                ).encode()
            new_member = tarfile.TarInfo(name=member.name)
            new_member.size = len(data)
            new_member.mode = 0o644
            new_member.uid = new_member.gid = 0
            new_member.mtime = 0
            dst.addfile(new_member, __import__("io").BytesIO(data))
    rebuilt.replace(archive)
    _sidecar_path(tmp_path / "backups", "dupmanifest").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError, match="duplicate"):
        verify_backup(archive)


def test_verify_rejects_malformed_manifest_as_backup_error(tmp_path: Path) -> None:
    """Truncated gzip must surface as a BackupError, not a raw EOFError."""
    archive = tmp_path / "hok-enwiki-20260701-truncated.tar.gz"
    archive.write_bytes(b"\x1f\x8b\x08\x00")
    sidecar = tmp_path / "hok-enwiki-20260701-truncated.tar.gz.sha256"
    sidecar.write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    with pytest.raises(BackupError):
        verify_backup(archive)


def test_backup_writes_archive_through_part_file(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    original_replace = corpus_backup.os.replace

    def _failing_replace(src, dst):
        if str(dst).endswith(".tar.gz"):
            raise OSError("simulated replace failure")
        return original_replace(src, dst)

    monkeypatch.setattr(corpus_backup.os, "replace", _failing_replace)
    with pytest.raises(BackupError, match="archive"):
        create_backup(repo, label="atomic", output_dir=tmp_path / "backups")
    out = tmp_path / "backups"
    archive = _archive_path(out, "atomic")
    sidecar = _sidecar_path(out, "atomic")
    assert not archive.exists()
    assert not sidecar.exists()
    assert not Path(f"{archive}.part").exists()
    assert not Path(f"{sidecar}.part").exists()


def test_backup_removes_archive_when_sidecar_publication_fails(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    original_replace = corpus_backup.os.replace

    def _failing_sidecar_replace(src, dst):
        if str(dst).endswith(".sha256"):
            raise OSError("simulated sidecar replace failure")
        return original_replace(src, dst)

    monkeypatch.setattr(corpus_backup.os, "replace", _failing_sidecar_replace)
    out = tmp_path / "backups"
    with pytest.raises(BackupError, match="sidecar"):
        create_backup(repo, label="paired", output_dir=out)

    archive = _archive_path(out, "paired")
    sidecar = _sidecar_path(out, "paired")
    assert not archive.exists()
    assert not sidecar.exists()
    assert not Path(f"{archive}.part").exists()
    assert not Path(f"{sidecar}.part").exists()


def test_backup_part_failure_leaves_no_published_archive(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)

    def _failing_close(*_args, **_kwargs):
        raise OSError("simulated flush failure")

    monkeypatch.setattr(corpus_backup.gzip.GzipFile, "close", _failing_close)
    with pytest.raises(BackupError):
        create_backup(repo, label="partial", output_dir=tmp_path / "backups")
    out = tmp_path / "backups"
    archive = _archive_path(out, "partial")
    assert not archive.exists()
    assert not Path(f"{archive}.part").exists()


def test_scripts_backup_corpus_delegates_to_package_cli(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_canonical(repo)
    _init_git(repo)
    out = tmp_path / "backups"
    script = Path(__file__).resolve().parents[1] / "scripts" / "backup_corpus.py"
    completed = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(script),
            "--label",
            "operator",
            "--output-dir",
            str(out),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (out / "hok-enwiki-20260701-operator.tar.gz").is_file()
    assert (out / "hok-enwiki-20260701-operator.tar.gz.sha256").is_file()
