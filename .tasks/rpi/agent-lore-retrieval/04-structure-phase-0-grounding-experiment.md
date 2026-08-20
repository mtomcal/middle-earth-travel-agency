1. [ ] Phase 1 — Publish and query a compatible lore index
2. [ ] Phase 2 — Produce one bounded evidence-aware model attempt
3. [ ] Phase 3 — Retain one complete matched comparison batch
4. [ ] Phase 4 — Deliver the operator command and paired review reports
5. [ ] Phase 5 — Run the live qualification and record the human gate

## Phase 1 — Publish and query a compatible lore index

### Observable outcome

Dependency: none. An operator can run `meta corpus build-index --manifest MANIFEST --config CONFIG --output INDEX` against a validated immutable release, receive a newly and atomically published SQLite index, and open that index read-only for deterministic lore-only search and immediate context. The command reports the release ID, 182 indexed passages for `corpus-v1-rc1`, output path, and configuration identity; it never reads or changes activation state.

### Expected files

- `config/lore-grounding-experiment.yaml` — versioned copyable baseline containing the approved complete Phase 0 YAML schema and defaults.
- `src/middle_earth_travel_agency/experiment_config.py` — duplicate-safe YAML loading, schema/bounds validation, immutable normalized configuration values, canonical non-secret serialization, and configuration identity hashing.
- `src/middle_earth_travel_agency/retrieval_index.py` — index/result dataclasses, release projection, four-table SQLite schema, staged validation/publication, compatibility checks, safe query translation, BM25 search, and coordinate-safe context lookup.
- `src/middle_earth_travel_agency/cli.py` — the `corpus build-index` parser and composition-root handler, resolving `articles/` and `curation.jsonl` beside the supplied manifest before calling the existing release validator.
- `pyproject.toml` and `uv.lock` — add and lock PyYAML.
- `tests/test_experiment_config.py`, `tests/test_retrieval_index.py`, and `tests/test_cli.py` — focused configuration, projection/retrieval, publication, and command coverage.

### Automated checks

- [ ] Configuration tests reject unsafe tags, duplicate or unknown keys, missing fields, wrong scalar types, unsupported schema versions, and every out-of-range value; accepted defaults and overrides normalize and hash deterministically.
- [ ] Projection tests prove that every and only manifest-admitted lore passage enters `passages` and `passages_fts`; lore, non-lore, and structural-exclusion coordinates are represented without copying unavailable text, while an absent coordinate remains detectable as an ordinal gap.
- [ ] Schema validation rejects missing/duplicate metadata, passage/FTS count mismatches, dangling content or lore coordinates, coordinate disagreement, unavailable coordinates with passage IDs, and lore passages without exactly one matching coordinate.
- [ ] Search tests cover title, full-heading display, and body matches; `unicode61 remove_diacritics 2`; safely quoted `all-terms` and `any-terms` translation; `5/2/1` BM25 weights; result bounds; ascending rank; and both approved deterministic tie breakers.
- [ ] Context tests return the target plus at most one consecutive neighbor per side and stop with `section-edge`, `non-lore-or-excluded`, or `ordinal-gap` without crossing article/heading boundaries or skipping unavailable coordinates.
- [ ] Compatibility tests reject the wrong release, manifest digest, schema/config identity, tokenizer/indexed-column contract, count, absent or malformed index, and tampering before retrieval is exposed through a read-only connection.
- [ ] Publication tests prove release validation precedes projection, staged validation precedes atomic publication, an existing destination is never overwritten, concurrent builders publish at most one complete index, and failures leave no partial sibling or activation change.
- [ ] CLI tests lock the approved argument shape, `Path` conversion, exact delegation, stable success summary, and existing `error: ...`/status-1 operator-failure behavior.
- [ ] `uv run pytest tests/test_experiment_config.py tests/test_retrieval_index.py tests/test_cli.py`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` pass.

### Manual validation

- [ ] Build a fresh scratch index from `data/releases/corpus-v1-rc1/manifest.json` with the baseline YAML and confirm the summary identifies `corpus-v1-rc1`, 182 passages, the destination, and the configuration identity.
- [ ] Open the published index through `RetrievalIndex`, search representative accented and title/body terms, and inspect context near a section edge and a non-lore boundary; only admitted normalized prose and stable evidence identity are visible.
- [ ] Repeat the build against the same destination and confirm it fails safely without changing the previously readable index.

## Phase 2 — Produce one bounded evidence-aware model attempt

### Observable outcome

Dependency: Phase 1. Given one question, one pinned `RetrievalIndex`, one retrieval condition, and a model adapter, `answer_case(...)` produces one sanitized terminal `AttemptRecord`: a grounded answer, an explicitly ungrounded submitted answer, an insufficient-evidence result, or a classified cell failure. A deterministic fake adapter exercises the entire message/tool loop without network access, while the production adapter maps the same boundary to OpenRouter through the minimal LangChain integration.

### Expected files

- `src/middle_earth_travel_agency/lore_agent.py` — the OpenRouter adapter, application-owned `search_lore`, `get_lore_context`, and `submit_answer` schemas, ordered tool loop, retrieval budget, final-only transition, typed submission validation, provider retry/timeout handling, sanitization, trace records, and `answer_case(...)` entry point.
- `src/middle_earth_travel_agency/experiment_config.py` — provider, agent, retrieval, timeout, retry, decoding, and output-limit values used immutably by an attempt.
- `pyproject.toml` and `uv.lock` — add and lock `langchain-openai` plus directly imported compatible `langchain-core` interfaces, without the top-level LangChain agent runtime, LangGraph, memory, or tracing packages.
- `tests/test_lore_agent.py` — deterministic adapter, enabled/disabled retrieval services, fake provider responses/errors, and complete attempt-contract coverage.

### Automated checks

- [ ] Adapter tests verify the exact OpenRouter model ID, `https://openrouter.ai/api/v1`, direct secret injection without global environment mutation, frozen decoding/timeouts/retries, streaming disabled, and no server tools, web search, fallback models, or router-specific required fields.
- [ ] Tool-schema tests prove prompts can supply only plain query text or a previously returned passage ID and cannot access SQL, paths, manifests, index lifecycle, release selection, ranking controls, result limits, files, or alternate evidence sources.
- [ ] Loop tests require the first retrieval call to be search, execute calls sequentially in declared order, emit one correlated `ToolMessage` per call, count each valid or invalid retrieval request, restrict context to evidence already returned in the attempt, and record the ordered safe trace.
- [ ] Budget tests enforce the default four-call limit, all valid configured limits, and a derived model-turn ceiling; reject mixed retrieval/final or multiple final calls; send excess calls bounded errors; provide one correction opportunity while budget remains; and make exactly one final-only invocation after exhaustion.
- [ ] Submission tests accept only one non-empty typed `submit_answer`, preserve ordered duplicate-free in-scope evidence IDs, classify answered-with-valid-evidence as grounded, keep unsupported answer text visibly `ungrounded_answer`, and never treat plain assistant text as completion.
- [ ] Disabled-condition and insufficiency tests prove the model receives the same prompt without being told its condition, search/context return no evidence, no fallback exists, answered model-memory prose stays ungrounded, and an honest insufficient-evidence submission remains distinct from a model/retrieval failure.
- [ ] Retry/timeout tests cover only transport failures, request timeouts, HTTP 429, and HTTP 5xx; identical retry inputs; `Retry-After` and bounded jitter; overall-deadline cancellation; no budget/turn consumption; and no retries for authentication, other 4xx, tool, or submission errors.
- [ ] Sanitization tests prove records never contain API keys, headers, raw exception representations, provider bodies, stack traces, hidden reasoning, or unapproved prompt content while retaining safe failure code/stage/message, request/retry counts, timing, usage, and returned model identity.
- [ ] `uv run pytest tests/test_lore_agent.py`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` pass.

### Manual validation

- [ ] Drive one easy enabled case through the deterministic adapter and inspect the resulting answer, evidence IDs, ordered tool trace, budget transitions, and resolved display passages.
- [ ] Drive the same case with retrieval disabled and confirm that no passage content appears and any factual submitted answer is labeled ungrounded rather than promoted.
- [ ] Simulate a malformed call, a transient retry, and a timeout and confirm each retained diagnostic is useful but contains no credential or provider payload.

## Phase 3 — Retain one complete matched comparison batch

### Observable outcome

Dependency: Phase 2. A direct `ExperimentRunner` invocation freezes one validated non-secret configuration and produces a new, inspectable batch containing an immutable `run.json`, 100 independently terminal append-only `attempts.jsonl` records, and an incomplete human-fillable `review.json`; it schedules the approved ten cases as disabled-then-enabled five-model waves and computes no score, rank, winner, or model recommendation.

### Expected files

- `src/middle_earth_travel_agency/lore_experiment.py` — the exact approved case catalog, case/run/attempt coordinates and identities, preflight validation, 20-wave `asyncio.TaskGroup` scheduling, concurrency semaphore, failure escalation, durable artifact writing/loading, and review-template/gate validation.
- `src/middle_earth_travel_agency/lore_agent.py` — any narrow additions needed to expose stable attempt records and distinguish global authentication/authorization failures from cell-local failures.
- `tests/test_lore_experiment.py` — catalog, scheduling, durability, failure-isolation, artifact-integrity, and review-gate tests using deterministic models.

### Automated checks

- [ ] Catalog tests lock the exact five easy and five hard IDs/questions, require unique IDs/questions, validate every human-only expected passage against the pinned index, and prove review focus/evidence expectations never enter messages, searches, or tool results.
- [ ] Preflight tests reject missing/duplicate/malformed five-model lists, incompatible manifest/index/config identities, bad output destinations, and invalid resolved configuration before a provider call or run directory is created.
- [ ] Envelope tests prove `run.json` is written before calls and retains schema/run identity, creation time, source revision, release/index/config identities, ordered models/cases/conditions, expected count, prompt identity, and every non-secret resolved value without credentials.
- [ ] Scheduling tests execute 20 stable case waves, disabled before enabled, five fresh stateless model attempts per wave, identical frozen prompt/decoding/orchestration settings across paired conditions, a configurable maximum concurrency no greater than five, a barrier between waves, and stable report coordinates despite out-of-order completion.
- [ ] Durability tests flush each terminal attempt as one canonical JSONL line before checkpointing, accept completion-order lines, reject duplicate/missing coordinates or a changed envelope, preserve partial diagnostics after interruption, and never resume or mutate an existing run.
- [ ] Failure tests stop scheduling and suppress qualification on authentication/authorization, durable-write, or run-integrity batch failures while allowing request timeout, exhausted transient retry, model rejection, invalid tool behavior, malformed submission, and isolated retrieval errors to remain cell-local.
- [ ] Completeness tests produce 50 enabled plus 50 disabled records even when selected cells fail, retain timing/outcome/evidence/error/model/config metadata independently, and do not reuse messages, tool budgets, responses, or state across cells.
- [ ] Review validation accepts only a matching run ID plus either `selected` with one configured exact model and non-empty rationale or `none` with non-empty rationale; the generated incomplete template never satisfies the gate.
- [ ] `uv run pytest tests/test_lore_experiment.py tests/test_lore_agent.py`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` pass.

### Manual validation

- [ ] Run a deterministic five-model batch into a new scratch directory and inspect that `run.json` precedes 100 complete uniquely coordinated JSONL lines and that the disabled/enabled ordering is visible in attempt metadata.
- [ ] Force one fake model to fail and confirm its cell remains diagnostic while all 99 siblings complete; then force an authentication failure and confirm the batch stops without pretending to qualify.
- [ ] Fill copies of `review.json` with selected, none, mismatched-model, wrong-run, and blank-rationale decisions and confirm only the two approved human-authored shapes pass gate validation.

## Phase 4 — Deliver the operator command and paired review reports

### Observable outcome

Dependency: Phase 3. An operator can run `meta experiment run --manifest MANIFEST --index INDEX --config CONFIG --output-dir OUTPUT_DIR`; after preflight it executes one live-capable matched batch and leaves the complete five-file output layout with separate self-contained retrieval-enabled and retrieval-disabled HTML reports derived only from retained structured data. Existing corpus commands and release bytes remain unchanged.

### Expected files

- `src/middle_earth_travel_agency/experiment_report.py` — complete-batch validation, pure escaped HTML projection, excerpt bounding, approved matrix/status/evidence presentation, and atomic paired-report publication.
- `src/middle_earth_travel_agency/cli.py` — the top-level `experiment run` parser/handler, `.env` loading, explicit manifest/index/config/output composition, preflight sequencing, runner invocation, paired rendering, stable success summary, and safe error presentation.
- `src/middle_earth_travel_agency/experiment_config.py` — exact parsing of `META_OPENROUTER_API_KEY` and ordered `META_EXPERIMENT_MODELS` without serializing the secret or introducing CLI/YAML overrides.
- `.env.example` — blank `META_OPENROUTER_API_KEY`, documented five-model `META_EXPERIMENT_MODELS` placeholder, and blank `META_LORE_MODEL` pending Phase 5 qualification; never a real credential.
- `tests/test_experiment_report.py`, `tests/test_cli.py`, and updates to `tests/test_experiment_config.py` and `tests/test_lore_experiment.py` — pure rendering, public composition, environment, complete-layout, and failure-path coverage.
- `.tasks/rpi/agent-lore-retrieval/prototypes/retrieval-enabled-report-prototype.html` — unchanged visual/information-architecture reference for implementation comparison.

### Automated checks

- [ ] Renderer tests require exactly one terminal record for all 100 coordinates, deterministic output from fixed structured data, identical case/model ordering between reports, condition-exclusive cells, shared batch identity, and relative companion links.
- [ ] Enabled-report tests keep full answers visible and render escaped status plus evidence grouped in tool-call order with title, complete section path, bounded excerpt, and passage ID in native collapsed details; ungrounded, insufficient, and failed cells remain honestly distinct.
- [ ] Disabled-report tests state retrieval was unavailable at page and cell level, retain answer text/status, and render no empty or misleading evidence control.
- [ ] Layout tests keep batch/release/model/config identity, all exact questions, difficulty labels, and expandable human-only case notes directly visible; preserve configured five-model column order; use sticky headers/question cells where supported; and retain readable horizontally scrollable columns on narrow screens.
- [ ] Security tests HTML-escape every model/corpus/config/error value, truncate excerpts by Unicode code points after the configured 200–4,000 bound, include inline CSS only, and emit no JavaScript, remote resource, secret, executable content, semantic scoring, ranking, or winner highlight.
- [ ] Artifact tests write `retrieval-enabled.html` and `retrieval-disabled.html` atomically only after complete structured validation, never invoke retrieval/provider code during rendering, and preserve `run.json`/`attempts.jsonl` if rendering fails.
- [ ] Environment tests require a trimmed non-empty secret and exactly five trimmed unique non-empty models, preserve declared order, expose only secret presence/absence in errors, and prove there is no CLI/YAML override or global `OPENAI_API_KEY` mutation.
- [ ] CLI tests lock the approved command shape and sequencing, require a new output directory and explicit compatible inputs, render both reports after 100 terminal cells, print deterministic paths/identity, and preserve the current status-1 operator-error contract.
- [ ] Dependency-direction checks prove `cli -> config/retrieval/experiment/report`, `experiment -> agent/config/retrieval`, `agent -> config/retrieval`, and `report -> experiment records`, with no runner-to-renderer, retrieval-to-agent, or lower-level-to-CLI import.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run pre-commit run --all-files` pass with at least 90% total coverage.

### Manual validation

- [ ] Render the same retained deterministic batch twice and compare bytes; open both reports locally and confirm condition labels, companion links, exact question inventory, sticky/scrolling matrix behavior, statuses, and collapsed evidence match the approved prototype's information architecture.
- [ ] Inspect representative grounded, ungrounded, insufficient, and failed cells plus malicious HTML-like answer/evidence text; confirm answers remain readable, content is inert, disabled cells have no evidence UI, and no score or recommendation appears.
- [ ] Run `meta experiment run` with missing environment values, an incompatible index, and an existing output directory and confirm each fails before provider work without leaking the key or altering prior artifacts.

## Phase 5 — Run the live qualification and record the human gate

### Observable outcome

Dependency: Phase 4. The operator completes one real 100-attempt OpenRouter batch against the explicit `corpus-v1-rc1` manifest/index pair, a human reviews both reports and authors a valid `review.json` selecting one exact configured model or selecting none with rationale, and gate validation records whether Phase 1 may proceed. Only a selected decision updates `.env.example` with the exact non-secret `META_LORE_MODEL`; this phase does not design or implement activation, the lore cockpit, or any other Phase 1 behavior.

### Expected files

- `.env` — ignored operator-local `META_OPENROUTER_API_KEY` and the five exact candidate `META_EXPERIMENT_MODELS`; never committed or copied into artifacts.
- `data/experiments/<run-id>/run.json`, `attempts.jsonl`, `retrieval-enabled.html`, `retrieval-disabled.html`, and `review.json` — ignored retained live batch, reports, and completed human decision.
- `.env.example` — exact qualified `META_LORE_MODEL` default after a `selected` decision, or an explicit still-unset value after `none`; candidate placeholders remain non-secret while Phase 0 support exists.

### Automated checks

- [ ] Build/open preflight validates the exact manifest, published index, release identity, index/config compatibility, and all ten expected evidence IDs before any live provider call.
- [ ] Batch validation confirms one immutable envelope and exactly 100 unique terminal attempts with paired settings, disabled isolation, no missing cells, no secret-bearing fields, and two reports derived from that same batch.
- [ ] Review-gate validation binds the completed decision to the batch and configured model list and rejects an incomplete template, altered run ID, unconfigured model, missing rationale, or any automatic/numeric verdict.
- [ ] After the model-default update, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run pre-commit run --all-files` pass.

### Manual validation

- [ ] Run the published index build and one live experiment command with the approved baseline, capturing exact model identifiers and all resolved non-secret settings in the new batch rather than editing an earlier run.
- [ ] Review every enabled/disabled model pair for pretrained recall, unsupported specificity, search/tool use, evidence fidelity, distortion, contradiction, uncertainty, and abstention; do not convert notes into a score or threshold.
- [ ] Complete `review.json` with either one qualifying exact model plus written rationale or `none` plus rationale, then run the gate validator and confirm the result.
- [ ] If a model qualifies, place that exact identifier in `.env.example` as `META_LORE_MODEL`; if none qualifies, leave Phase 1 blocked and record the retrieval/orchestration or candidate-set hypothesis that must change before a new separately identified batch.
- [ ] Confirm with the human that Phase 0 is complete and that any Phase 1 Program Design or implementation will require a later explicit task rather than continuing from this structure automatically.
