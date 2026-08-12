"""Offline candidate discovery and Wikimedia dump acquisition."""

from __future__ import annotations

import bz2
import hashlib
import json
import re
import sqlite3
import tempfile
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Callable, Iterable, Iterator, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import mwparserfromhell


@dataclass(frozen=True)
class CandidatePage:
    page_id: int
    title: str


@dataclass(frozen=True)
class DiscoveryRequest:
    categories: tuple[str, ...] = ()
    nominations: tuple[str, ...] = ()
    max_candidates: int = 100


@dataclass(frozen=True)
class DiscoveryRecord:
    discovery_route: str
    discovery_reference: str
    observed_page_title: str
    observed_page_id: int | None
    discovery_timestamp: str


@dataclass(frozen=True)
class DiscoveryResult:
    records: tuple[DiscoveryRecord, ...]


class CandidateCatalog(Protocol):
    def articles(self, category: str, limit: int) -> Iterable[CandidatePage]: ...


class PywikibotCatalog:
    """Bounded, identified, serial Wikimedia category discovery."""

    def __init__(self, *, contact: str, minimum_request_interval: float = 1.0) -> None:
        if minimum_request_interval < 1.0:
            raise ValueError("minimum request interval must be at least one second")
        _contact_user_agent(contact)
        import pywikibot
        from pywikibot import config

        config.user_agent_description = f"contact: {contact.strip()}"
        config.user_agent_format = (
            "HallsOfKnowledge/0.1 ({script_comments}) {pwb} ({revision}) {python}"
        )
        config.minthrottle = minimum_request_interval
        config.maxthrottle = max(config.maxthrottle, 60)
        config.max_retries = 5
        config.retry_wait = max(config.retry_wait, 5)
        config.maxlag = 5
        self._pywikibot = pywikibot
        self._site = pywikibot.Site("en", "wikipedia")
        self._site.throttle.set_delays(delay=minimum_request_interval, absolute=True)

    def articles(self, category: str, limit: int) -> Iterable[CandidatePage]:
        if limit <= 0:
            return
        category_page = self._pywikibot.Category(self._site, category)
        for page in category_page.articles(recurse=False, total=limit, namespaces=0):
            yield CandidatePage(page_id=page.pageid, title=page.title())


@dataclass(frozen=True)
class SourceSnapshot:
    wiki_database: str
    dump_run: str
    filename: str
    source_url: str
    retrieval_timestamp: str
    extraction_profile: str = "full non-multistream article dump"

    @classmethod
    def initial(cls, *, retrieved_at: str) -> "SourceSnapshot":
        filename = "enwiki-20260701-pages-articles.xml.bz2"
        return cls(
            wiki_database="enwiki",
            dump_run="20260701",
            filename=filename,
            source_url=f"https://dumps.wikimedia.org/enwiki/20260701/{filename}",
            retrieval_timestamp=retrieved_at,
        )


@dataclass(frozen=True)
class AcquisitionSuccess:
    candidate_title: str
    article_artifact_id: str


@dataclass(frozen=True)
class AcquisitionFailure:
    candidate_identity: str
    stage: str
    reason: str
    recoverable: bool


@dataclass(frozen=True)
class ExtractionResult:
    successes: tuple[AcquisitionSuccess, ...]
    failures: tuple[AcquisitionFailure, ...]
    scan_passes: int


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    bytes_downloaded: int
    resumed: bool
    source_url: str


@dataclass(frozen=True)
class _PageRecord:
    title: str
    namespace: int
    page_id: int
    redirect_target: str | None
    revision_id: int
    parent_revision_id: int | None
    revision_timestamp: str
    raw_wikitext: str


def _category_title(value: str) -> str:
    return value if value.startswith("Category:") else f"Category:{value}"


def _category_url(value: str) -> str:
    title = _category_title(value).replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{quote(title, safe=':_()')}"


def discover_candidates(
    request: DiscoveryRequest,
    *,
    catalog: CandidateCatalog,
    observed_at: datetime,
) -> DiscoveryResult:
    """Discover a bounded candidate set without admitting it to the corpus."""
    records: list[DiscoveryRecord] = []
    seen_page_ids: set[int] = set()
    seen_titles: set[str] = set()
    timestamp = observed_at.isoformat()

    for category in request.categories:
        remaining = request.max_candidates - len(records)
        if remaining <= 0:
            break
        category_title = _category_title(category)
        for page in catalog.articles(category_title, remaining):
            normalized_title = page.title.replace("_", " ").strip()
            if page.page_id in seen_page_ids or normalized_title.casefold() in seen_titles:
                continue
            records.append(
                DiscoveryRecord(
                    discovery_route="category or API",
                    discovery_reference=_category_url(category_title),
                    observed_page_title=normalized_title,
                    observed_page_id=page.page_id,
                    discovery_timestamp=timestamp,
                )
            )
            seen_page_ids.add(page.page_id)
            seen_titles.add(normalized_title.casefold())
            if len(records) == request.max_candidates:
                break

    for nomination in request.nominations:
        if len(records) == request.max_candidates:
            break
        title = nomination.replace("_", " ").strip()
        if title.casefold() in seen_titles:
            continue
        records.append(
            DiscoveryRecord(
                discovery_route="human nomination",
                discovery_reference="operator nomination",
                observed_page_title=title,
                observed_page_id=None,
                discovery_timestamp=timestamp,
            )
        )
        seen_titles.add(title.casefold())

    return DiscoveryResult(records=tuple(records))


class _IncompleteDownload(OSError):
    pass


def _contact_user_agent(contact: str) -> str:
    contact = contact.strip()
    if not contact or not ("@" in contact or contact.startswith(("https://", "http://"))):
        raise ValueError("contact must be a monitored email address or HTTP(S) URL")
    return f"HallsOfKnowledge/0.1 (offline corpus acquisition; {contact})"


def download_initial_dump(
    destination: Path,
    *,
    contact: str,
    open_request: Callable[..., object] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
    retry_delays: tuple[float, ...] = (30, 60, 120, 240, 300),
    max_bytes_per_second: int | None = 16 * 1024 * 1024,
) -> DownloadResult:
    """Download the pinned dump with one connection, bounded retries, and safe resume."""
    source = SourceSnapshot.initial(retrieved_at="")
    if destination.name != source.filename:
        raise ValueError(f"destination must end with {source.filename}")
    if "/latest/" in source.source_url:
        raise ValueError("dated Wikimedia dump URL required")
    user_agent = _contact_user_agent(contact)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.exists():
        return DownloadResult(
            path=destination,
            bytes_downloaded=destination.stat().st_size,
            resumed=False,
            source_url=source.source_url,
        )

    attempts = len(retry_delays) + 1
    initially_partial = partial.exists() and partial.stat().st_size > 0
    last_error: Exception | None = None
    for attempt in range(attempts):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = Request(source.source_url, headers=headers, method="GET")
        try:
            with open_request(request, timeout=120) as response:  # type: ignore[attr-defined]
                status = getattr(response, "status", 200)
                if offset and status != 206:
                    raise _IncompleteDownload(
                        "dump provider did not honor Range; refusing to overwrite partial download"
                    )
                content_range = response.headers.get("Content-Range")
                if offset and (
                    not content_range or not content_range.startswith(f"bytes {offset}-")
                ):
                    raise _IncompleteDownload("invalid Content-Range for resumed download")
                expected = response.headers.get("Content-Length")
                expected_bytes = int(expected) if expected is not None else None
                received = 0
                started = time.monotonic()
                with partial.open("ab") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                        received += len(chunk)
                        if max_bytes_per_second:
                            target_elapsed = received / max_bytes_per_second
                            remaining = target_elapsed - (time.monotonic() - started)
                            if remaining > 0:
                                sleep(remaining)
                    output.flush()
                if expected_bytes is not None and received != expected_bytes:
                    raise _IncompleteDownload(
                        f"connection ended after {received} of {expected_bytes} response bytes"
                    )
            partial.replace(destination)
            return DownloadResult(
                path=destination,
                bytes_downloaded=destination.stat().st_size,
                resumed=initially_partial or attempt > 0,
                source_url=source.source_url,
            )
        except HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            retry_after = error.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay = min(float(retry_after), 900)
            elif retry_after:
                delay = min(
                    max(parsedate_to_datetime(retry_after).timestamp() - time.time(), 0), 900
                )
            else:
                delay = None
        except (URLError, _IncompleteDownload, ConnectionError, TimeoutError) as error:
            last_error = error
            delay = None
        if attempt >= len(retry_delays):
            break
        sleep(delay if delay is not None else retry_delays[attempt])
    assert last_error is not None
    raise last_error


_XML_TAG = re.compile(r"^\{[^}]+\}(.*)$")
_HEADING = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
_ADMIN_HEADINGS = {
    "bibliography",
    "external links",
    "further reading",
    "notes",
    "references",
    "sources",
}
_EXTRACTOR_CONFIGURATION = {
    "supported_structure": "prose paragraphs",
    "lead_heading": "Lead",
    "remove_inline_references": True,
    "replace_links_with_display_labels": True,
    "exclude_lists_tables_quotes_and_unresolved_templates": True,
    "whitespace_normalization": "collapse",
}


def _local_name(tag: str) -> str:
    match = _XML_TAG.match(tag)
    return match.group(1) if match else tag


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == name:
            return child.text
    return None


def _child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag) == name:
            return child
    return None


def _iter_dump_pages(dump_path: Path, *, expected_database: str) -> Iterator[_PageRecord]:
    """Stream every page and reach the XML end marker before returning."""
    with bz2.open(dump_path, "rb") as stream:
        context = ET.iterparse(stream, events=("start", "end"))
        _event, root = next(context)
        observed_database: str | None = None
        for event, element in context:
            name = _local_name(element.tag)
            if event == "end" and name == "siteinfo":
                observed_database = _child_text(element, "dbname")
                if observed_database != expected_database:
                    raise ValueError(
                        f"expected wiki database {expected_database}, got {observed_database}"
                    )
            if event != "end" or name != "page":
                continue
            if observed_database is None:
                raise ValueError("dump page appeared before required site database identity")
            revision = _child(element, "revision")
            if revision is not None:
                redirect = _child(element, "redirect")
                text_element = _child(revision, "text")
                yield _PageRecord(
                    title=_child_text(element, "title") or "",
                    namespace=int(_child_text(element, "ns") or -1),
                    page_id=int(_child_text(element, "id") or 0),
                    redirect_target=(
                        redirect.attrib.get("title") if redirect is not None else None
                    ),
                    revision_id=int(_child_text(revision, "id") or 0),
                    parent_revision_id=(
                        int(parent) if (parent := _child_text(revision, "parentid")) else None
                    ),
                    revision_timestamp=_child_text(revision, "timestamp") or "",
                    raw_wikitext=(text_element.text or "") if text_element is not None else "",
                )
            root.clear()
        if observed_database is None:
            raise ValueError("dump lacks required site database identity")


def _normalized_title(title: str) -> str:
    return title.replace("_", " ").strip()


def _title_key(title: str) -> str:
    normalized = _normalized_title(title)
    return normalized[:1].upper() + normalized[1:]


def _redirect_title(title: str) -> str:
    return _normalized_title(title.split("#", 1)[0])


def _resolve_redirect(
    connection: sqlite3.Connection, start_title: str
) -> tuple[str, list[dict[str, str]]]:
    title = _normalized_title(start_title)
    seen: set[str] = set()
    chain: list[dict[str, str]] = []
    while True:
        key = _title_key(title)
        if key in seen:
            raise ValueError(f"redirect loop at {title}")
        seen.add(key)
        row = connection.execute(
            "SELECT target_title FROM redirects WHERE source_key = ?", (key,)
        ).fetchone()
        if row is None:
            return title, chain
        target = _redirect_title(row[0])
        chain.append({"source_title": title, "target_title": target})
        title = target


def _blocks(raw_wikitext: str) -> Iterator[tuple[list[str], int, str]]:
    hierarchy: list[str] = []
    ordinal_by_heading: dict[tuple[str, ...], int] = {}
    buffer: list[str] = []

    def flush() -> tuple[list[str], int, str] | None:
        if not buffer:
            return None
        text = "\n".join(buffer).strip()
        buffer.clear()
        path = hierarchy.copy() or ["Lead"]
        key = tuple(path)
        ordinal_by_heading[key] = ordinal_by_heading.get(key, 0) + 1
        return path, ordinal_by_heading[key], text

    for line in raw_wikitext.splitlines():
        heading = _HEADING.match(line)
        if heading:
            if block := flush():
                yield block
            level = len(heading.group(1)) - 1
            title = mwparserfromhell.parse(heading.group(2)).strip_code().strip()
            hierarchy[level - 1 :] = [title]
        elif not line.strip():
            if block := flush():
                yield block
        else:
            buffer.append(line)
    if block := flush():
        yield block


def _classify_block(heading_path: list[str], text: str) -> str | None:
    if any(heading.casefold() in _ADMIN_HEADINGS for heading in heading_path):
        return "reference or administrative material"
    lines = text.splitlines()
    if any(line.lstrip().startswith(("*", "#", ";", ":")) for line in lines):
        return "list"
    if "{|" in text or "|}" in text:
        return "table"
    lowered = text.casefold()
    if "<poem" in lowered or "<blockquote" in lowered:
        return "block quotation"
    parsed = mwparserfromhell.parse(text)
    if parsed.filter_templates(recursive=True):
        return "unresolved template"
    return None


def _normalize_prose(text: str) -> str:
    parsed = mwparserfromhell.parse(text)
    for tag in list(parsed.filter_tags(recursive=True)):
        if tag.tag.strip().casefold() == "ref":
            parsed.remove(tag)
    normalized = parsed.strip_code(normalize=True, collapse=True)
    return " ".join(normalized.split())


def _identity(prefix: str, value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()}"


def _artifact_for_page(
    page: _PageRecord,
    *,
    source: SourceSnapshot,
    redirect_chain: list[dict[str, str]],
) -> dict[str, object]:
    extractor_identity = f"mwparserfromhell {version('mwparserfromhell')}"
    artifact_id = _identity(
        "article",
        [
            source.dump_run,
            page.page_id,
            page.revision_id,
            extractor_identity,
            _EXTRACTOR_CONFIGURATION,
        ],
    )
    passages: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    for heading_path, ordinal, block in _blocks(page.raw_wikitext):
        if reason := _classify_block(heading_path, block):
            exclusions.append(
                {
                    "heading_path": heading_path,
                    "paragraph_ordinal": ordinal,
                    "structure_type": reason,
                    "reason": f"excluded by extractor policy: {reason}",
                }
            )
            continue
        normalized = _normalize_prose(block)
        if not normalized:
            continue
        passage_id = _identity("passage", [artifact_id, heading_path, ordinal])
        passages.append(
            {
                "passage_id": passage_id,
                "article_artifact_id": artifact_id,
                "heading_path": heading_path,
                "paragraph_ordinal": ordinal,
                "normalized_text": normalized,
                "structure": "prose paragraph",
            }
        )
    title_path = quote(page.title.replace(" ", "_"), safe="()_-")
    return {
        "article_artifact_id": artifact_id,
        "wiki_database": source.wiki_database,
        "dump_run": source.dump_run,
        "source_snapshot": asdict(source),
        "page_id": page.page_id,
        "namespace": page.namespace,
        "canonical_title": page.title,
        "redirect_chain": redirect_chain,
        "revision_id": page.revision_id,
        "parent_revision_id": page.parent_revision_id,
        "revision_timestamp": page.revision_timestamp,
        "permanent_revision_url": (
            f"https://en.wikipedia.org/w/index.php?oldid={page.revision_id}"
        ),
        "history_url": f"https://en.wikipedia.org/w/index.php?title={title_path}&action=history",
        "raw_wikitext": page.raw_wikitext,
        "extractor_identity": extractor_identity,
        "extractor_configuration": _EXTRACTOR_CONFIGURATION,
        "extracted_passages": passages,
        "structural_exclusions": exclusions,
    }


def _write_immutable_json(path: Path, value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text() != serialized:
            raise FileExistsError(f"immutable artifact identity collision: {path.name}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(serialized)
    temporary.replace(path)


def extract_article_artifacts(
    dump_path: Path,
    *,
    discoveries: Iterable[DiscoveryRecord],
    output_dir: Path,
    source: SourceSnapshot,
    progress: Callable[[int, int], None] | None = None,
) -> ExtractionResult:
    """Resolve candidates and build immutable artifacts using two complete sequential scans."""
    if dump_path.name != source.filename:
        raise ValueError(f"expected dump filename {source.filename}, got {dump_path.name}")
    candidates = tuple(discoveries)
    title_candidates = {_title_key(record.observed_page_title): record for record in candidates}
    page_id_candidates = {
        record.observed_page_id: record
        for record in candidates
        if record.observed_page_id is not None
    }
    matched: dict[str, tuple[DiscoveryRecord, str]] = {}
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="meta-redirects-", dir=output_dir.parent
    ) as temporary_dir:
        database = sqlite3.connect(Path(temporary_dir) / "redirects.sqlite3")
        database.execute("PRAGMA journal_mode=MEMORY")
        database.execute("PRAGMA synchronous=OFF")
        database.execute("CREATE TABLE redirects (source_key TEXT PRIMARY KEY, target_title TEXT)")
        inserts = 0
        if progress:
            progress(1, 0)
        for page_count, page in enumerate(
            _iter_dump_pages(dump_path, expected_database=source.wiki_database), start=1
        ):
            if progress and page_count % 1_000_000 == 0:
                progress(1, page_count)
            if page.redirect_target:
                database.execute(
                    "INSERT OR REPLACE INTO redirects VALUES (?, ?)",
                    (_title_key(page.title), page.redirect_target),
                )
                inserts += 1
                if inserts % 10_000 == 0:
                    database.commit()
            record = page_id_candidates.get(page.page_id) or title_candidates.get(
                _title_key(page.title)
            )
            if record is not None:
                matched[_title_key(record.observed_page_title)] = (record, page.title)
        database.commit()

        failures: list[AcquisitionFailure] = []
        resolved: dict[str, tuple[DiscoveryRecord, list[dict[str, str]]]] = {}
        for record in candidates:
            match = matched.get(_title_key(record.observed_page_title))
            if match is None:
                failures.append(
                    AcquisitionFailure(
                        candidate_identity=record.observed_page_title,
                        stage="source scan",
                        reason="candidate absent from source snapshot",
                        recoverable=True,
                    )
                )
                continue
            try:
                target_title, chain = _resolve_redirect(database, match[1])
            except ValueError as error:
                failures.append(
                    AcquisitionFailure(
                        candidate_identity=record.observed_page_title,
                        stage="redirect resolution",
                        reason=str(error),
                        recoverable=False,
                    )
                )
                continue
            resolved[_title_key(target_title)] = (record, chain)

        selected_pages: dict[str, _PageRecord] = {}
        scan_passes = 1
        if resolved:
            scan_passes = 2
            if progress:
                progress(2, 0)
            for page_count, page in enumerate(
                _iter_dump_pages(dump_path, expected_database=source.wiki_database), start=1
            ):
                if progress and page_count % 1_000_000 == 0:
                    progress(2, page_count)
                title_key = _title_key(page.title)
                if title_key in resolved:
                    selected_pages[title_key] = page

        successes: list[AcquisitionSuccess] = []
        for target_key, (record, chain) in resolved.items():
            page = selected_pages.get(target_key)
            if page is None:
                failures.append(
                    AcquisitionFailure(
                        candidate_identity=record.observed_page_title,
                        stage="redirect resolution",
                        reason="redirect target absent from source snapshot",
                        recoverable=True,
                    )
                )
                continue
            if page.namespace != 0:
                failures.append(
                    AcquisitionFailure(
                        candidate_identity=record.observed_page_title,
                        stage="redirect resolution",
                        reason=f"namespace {page.namespace} is outside namespace 0",
                        recoverable=False,
                    )
                )
                continue
            artifact = _artifact_for_page(page, source=source, redirect_chain=chain)
            artifact_id = str(artifact["article_artifact_id"])
            _write_immutable_json(output_dir / f"{artifact_id}.json", artifact)
            successes.append(
                AcquisitionSuccess(
                    candidate_title=record.observed_page_title,
                    article_artifact_id=artifact_id,
                )
            )
        database.close()

    return ExtractionResult(
        successes=tuple(successes), failures=tuple(failures), scan_passes=scan_passes
    )
