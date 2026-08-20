# Run a lore-grounding experiment

Use the Phase 0 experiment to compare exactly five OpenRouter models on the
same ten reviewed lore questions. Every batch runs each model once with lore
retrieval disabled and once with retrieval enabled, producing 100 independent
attempts and two local HTML reports.

The software records and presents the comparison. It does not score, rank, or
select a model. A human must review the paired reports and record either one
qualified model or `none`, with a written rationale.

## Understand the experiment boundary

One batch fixes all of these inputs before the first provider request:

- one immutable corpus release manifest;
- one compatible read-only SQLite retrieval index;
- one validated non-secret YAML configuration;
- five ordered, unique OpenRouter model identifiers;
- the approved five easy and five hard questions; and
- one prompt, tool contract, retrieval budget, and retry policy.

The runner schedules 20 waves in case-catalog order. For each question it runs
the five retrieval-disabled attempts first, waits for all five to finish, then
runs the five retrieval-enabled attempts. Each attempt has fresh messages,
state, tool budget, and provider calls. A failed cell remains visible and does
not invalidate its siblings. Authentication or authorization failure, loss of
artifact integrity, or inability to durably write the batch stops the run.

Retrieval-enabled answers classified as `grounded` have cited only passage IDs
returned during that attempt. This is an answer-level structural check, not a
claim-by-claim factual verdict. The human still has to compare every claim with
the displayed evidence.

## Prepare the repository

From the repository root, install the locked environment:

```bash
uv sync
```

The examples below use the retained `corpus-v1-rc1` release and the versioned
baseline configuration:

```text
data/releases/corpus-v1-rc1/manifest.json
config/lore-grounding-experiment.yaml
```

Validate the release before building an index:

```bash
uv run meta corpus validate-release \
  data/releases/corpus-v1-rc1/manifest.json \
  --articles-dir data/releases/corpus-v1-rc1/articles \
  --curation data/releases/corpus-v1-rc1/curation.jsonl
```

## Configure OpenRouter locally

Copy the variable names from `.env.example` into the repository-root `.env`:

```dotenv
META_OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
META_EXPERIMENT_MODELS=model-one,model-two,model-three,model-four,model-five
```

`META_OPENROUTER_API_KEY` must be non-empty. Keep it only in `.env`, which is
gitignored. Never put a real key in `.env.example`, a command argument, a YAML
file, an experiment artifact, or a support message.

`META_EXPERIMENT_MODELS` must contain exactly five non-empty, unique, exact
OpenRouter model IDs. Whitespace around IDs is trimmed and declared order is
preserved in scheduling and report columns. Choose models that support chat
tool calls. A model that returns prose without the required `submit_answer`
tool call will appear as `missing_submission`; do not hide that behavior by
editing the retained batch.

Review current provider pricing and limits before starting. One complete batch
contains at least 100 model requests and may contain additional turns and one
transient retry per request under the baseline configuration.

## Review or copy the YAML configuration

The versioned baseline is `config/lore-grounding-experiment.yaml`. Copy it when
testing a different hypothesis so the baseline remains easy to reproduce:

```bash
cp config/lore-grounding-experiment.yaml \
  config/lore-grounding-experiment-expanded-budget.yaml
```

The sections control:

| Section | Values owned by the operator |
|---|---|
| `index` | FTS tokenizer and diacritic folding |
| `retrieval` | query mode, result limit, BM25 weights, and deterministic tie breaker |
| `agent` | retrieval-call budget, temperature, and maximum output tokens |
| `provider` | request timeout, overall attempt timeout, and transient retry count |
| `runner` | maximum concurrent attempts, from one through five |
| `report` | displayed evidence-excerpt length |

The loader rejects missing, duplicate, unknown, wrongly typed, or out-of-range
values. The normalized configuration and its identity are retained in
`run.json`; the retained record, not the editable YAML file, is the authority
for what a completed batch used.

Changing an `index` or `retrieval` value requires a newly built compatible
index. Changing only agent, provider, runner, report, or model-list values does
not require rebuilding the index, but always requires a new experiment output
directory. Never change settings between cells in one batch.

The prompt and ten-case catalog are deliberately code-owned. They have no CLI,
environment, or YAML override. Changing either is an implementation change and
requires corresponding tests and a newly identified batch.

## Build a compatible retrieval index

Choose a new destination that identifies the release and configuration. The
builder never overwrites an existing index:

```bash
uv run meta corpus build-index \
  --manifest data/releases/corpus-v1-rc1/manifest.json \
  --config config/lore-grounding-experiment.yaml \
  --output data/indexes/corpus-v1-rc1.sqlite
```

The command validates the release, projects only admitted lore passages into a
staged SQLite index, validates the staged index, and publishes it atomically.
Its summary reports the release ID, passage count, destination, and
configuration identity. It does not read or modify release activation state.

Reusing the exact same index is appropriate when only models or non-retrieval
settings change. If the destination already exists and you intentionally need a
different index, choose a new descriptive filename. Do not delete or replace an
index that is needed to interpret a retained run.

## Run a new batch

Every output directory is immutable and must not exist before the command.
Use a descriptive, unique run name:

```bash
uv run meta experiment run \
  --manifest data/releases/corpus-v1-rc1/manifest.json \
  --index data/indexes/corpus-v1-rc1.sqlite \
  --config config/lore-grounding-experiment.yaml \
  --output-dir data/experiments/2026-08-19-baseline-01
```

Preflight validates the environment, new output destination, release, index,
configuration compatibility, candidate list, case catalog, and every expected
evidence passage before making a provider request.

The command normally prints only its final summary. In another terminal, safely
observe durable progress without reading secrets or modifying the run:

```bash
wc -l data/experiments/2026-08-19-baseline-01/attempts.jsonl
```

The count advances toward 100 in completion order. A wave may show four new
lines while waiting for one slower model. Let the configured retry and timeout
policy resolve naturally; changing it mid-run would invalidate the matched
comparison.

If the process is interrupted, keep the partial directory for diagnosis if it
is useful. It cannot be resumed, completed by hand, or used for qualification.
Start again with a new output directory.

## Inspect the retained artifacts

A successful batch contains exactly five files:

| File | Purpose |
|---|---|
| `run.json` | Immutable batch identity, source revision, release/index/config identities, ordered models/cases/conditions, prompt identity, and resolved non-secret settings |
| `attempts.jsonl` | One canonical, durably flushed terminal record for each of the 100 coordinates |
| `retrieval-enabled.html` | Self-contained enabled-condition comparison with cited evidence details |
| `retrieval-disabled.html` | Self-contained control comparison with no evidence UI |
| `review.json` | Incomplete human-decision template bound to the run ID |

The two reports are pure projections of freshly reloaded `run.json` and
`attempts.jsonl`. They contain inline CSS but no JavaScript, remote resources,
provider calls, or retrieval calls. Open both locally and confirm that their
batch IDs and ordered model columns match before comparing responses.

Attempt statuses mean:

- `grounded`: an answered enabled attempt cited one or more in-scope returned
  passages; the human must still verify that the prose faithfully uses them;
- `ungrounded answer`: the model submitted factual prose without usable cited
  evidence, commonly exposing pretrained recall in the disabled condition;
- `insufficient evidence`: the model explicitly declined to answer from the
  available evidence; and
- `failed`: the attempt retained a sanitized code and stage, such as provider
  timeout, provider rejection, invalid tool behavior, or missing submission.

Reports contain no score, pass threshold, rank, winner styling, or automatic
recommendation. A large number of completed cells, grounded labels, or
retrieval calls does not by itself qualify a model.

## Perform the human review

Review every enabled/disabled pair. Consider at least:

- what the disabled answer reveals about pretrained Tolkien recall;
- whether enabled models form useful searches and stay within the tool budget;
- whether cited passages actually support each answer claim;
- unsupported specificity, distortion, contradiction, or invented causality;
- appropriate uncertainty and abstention when evidence is incomplete; and
- operational reliability, including repeated provider or tool-call failures.

Do not convert these observations into an automatic score. Record one
qualitative decision in `review.json`.

To select one exact configured model:

```json
{
  "decision": "selected",
  "rationale": "Human-written explanation of why this model qualifies.",
  "run_id": "COPY_THE_EXACT_RUN_ID_FROM_THE_TEMPLATE",
  "schema_version": 1,
  "selected_model": "COPY_ONE_EXACT_CONFIGURED_MODEL_ID"
}
```

To record that no candidate qualifies:

```json
{
  "decision": "none",
  "rationale": "Human-written explanation of the observed failure and the next hypothesis to test.",
  "run_id": "COPY_THE_EXACT_RUN_ID_FROM_THE_TEMPLATE",
  "schema_version": 1,
  "selected_model": null
}
```

Validate the completed gate against the retained batch:

```bash
uv run python -c 'import json; from pathlib import Path; from middle_earth_travel_agency.lore_experiment import load_run_artifacts, validate_review; run = Path("data/experiments/2026-08-19-baseline-01"); retained = load_run_artifacts(run); decision = validate_review(json.loads((run / "review.json").read_text()), retained.envelope); print(f"validated {decision.decision} decision for {decision.run_id}")'
```

The validator rejects an incomplete template, wrong run ID, unconfigured
model, missing rationale, unknown fields, or a conflicting decision shape.

If a model is accepted as the Phase 1 default, copy its exact identifier to
the non-secret `META_LORE_MODEL` value in `.env.example` and run the repository
verification suite. If the decision is `none`, leave that value blank. Phase 1
remains blocked until a later, separately identified experiment tests a changed
candidate set or retrieval/orchestration hypothesis.

## Run another experiment safely

Treat every changed hypothesis as a new batch:

1. Copy and edit YAML only when changing approved non-secret settings.
2. Rebuild to a new index path when `index` or `retrieval` settings change.
3. Edit only `META_EXPERIMENT_MODELS` when changing the candidate set.
4. Choose a new output directory; never reuse or edit an earlier run.
5. Compare only reports whose intended configuration differences you
   understand from their `run.json` records.
6. Complete a separate human `review.json` for every batch used in a decision.

The ignored `data/experiments/` directories are operator-owned evidence. Copy
or back them up deliberately if they matter; they are not committed by
default. Never copy `.env` with them.

## Troubleshoot common outcomes

`META_OPENROUTER_API_KEY is absent`
: Add a non-empty key to the repository-root `.env`. Do not pass it on the CLI.

`META_EXPERIMENT_MODELS must contain exactly five unique non-empty models`
: Supply exactly five comma-separated exact IDs with no duplicates.

`refusing to overwrite retrieval index` or `refusing to reuse experiment output directory`
: Choose a new destination. Existing indexes and runs are immutable evidence.

`retrieval index is incompatible with the release or configuration`
: Confirm the explicit manifest, index, and YAML belong together. Build a new
  index when retrieval settings changed.

`provider_authorization_failed`
: The batch stops after retaining the current wave. Check the local key and
  OpenRouter account permissions, then start a new output directory.

`provider_request_failed` or `provider_timeout`
: These are cell-level results after the configured policy is exhausted. Keep
  them in the comparison. Repeated failures may justify a new candidate set or
  a separately configured run; never patch the old JSONL.

`missing_submission`
: The model returned no valid terminal `submit_answer` call. Confirm the model
  supports tool calling. The failure is part of the experiment and should not
  be rewritten as an answer.

No HTML reports after interruption or batch failure
: Expected. Reports publish only after all 100 terminal coordinates reload and
  validate. Inspect the retained envelope and partial JSONL, then start a new
  batch rather than resuming it.

## Verify implementation or configuration changes

After changing experiment code, versioned configuration, or the selected
non-secret default, run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pre-commit run --all-files
```

Before committing, confirm `.env`, indexes, and experiment outputs remain
ignored and no credential appears in staged changes:

```bash
git status --short
git check-ignore .env data/indexes/corpus-v1-rc1.sqlite data/experiments/2026-08-19-baseline-01/run.json
git diff --cached
```
