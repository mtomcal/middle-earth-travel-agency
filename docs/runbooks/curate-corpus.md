# Curate extracted passages

Use the curation cockpit to classify each extracted Wikipedia passage under the
current Tolkien corpus rubric. This is an offline, keyboard-driven operator
workflow. A classification is saved before the cockpit advances, so normal
progress does not depend on reaching the end of a session.

## Understand the inputs and output

The command requires two paths:

- `--articles-dir` is the directory of immutable JSON article artifacts created
  by corpus acquisition. The repository's current acquisition is under
  `data/corpus/articles/`.
- `--state-db` is the SQLite working file that holds decisions, audit events,
  and resume positions while the cockpit runs. Choose this path once and reuse
  the exact same path for every session over that acquisition.

The state database is created automatically, including its parent directory.
For the current repository layout, use:

```text
data/curation/initial.sqlite
```

Files below `data/curation/` are operator working state and are ignored by Git's
broad `data/**` rule except for JSONL snapshots. The SQLite file is an
operational projection of the versioned curation evidence, not a disposable
cache while it contains decisions that have not yet been exported.

Do not point `--state-db` at an existing database from another acquisition, and
do not give two running cockpit processes the same state database.

## Restore the SQLite working state

The tracked curation record is `data/curation/initial.jsonl`. If the SQLite
working file does not exist, reconstruct it before starting the cockpit:

```bash
uv run meta corpus load-curation \
  --input data/curation/initial.jsonl \
  --state-db data/curation/initial.sqlite
```

The loader validates the JSONL schema, metadata, audit-event supersession
relationships, and resulting SQLite integrity before publishing the database.
It refuses to overwrite an existing SQLite file. The cockpit subsequently
checks that the reconstructed database belongs to the supplied article
artifacts and current rubric.

## Prepare the project

From the repository root, install the locked dependencies and confirm that the
article artifacts exist:

```bash
uv sync
test -d data/corpus/articles
```

The cockpit must run in an interactive terminal. It intentionally refuses
pipes, redirected output, background jobs without a terminal, and other
non-interactive use.

To inspect the available command options without starting a session:

```bash
uv run meta corpus curate --help
```

## Start the first session

Run from the repository root:

```bash
uv run meta corpus curate \
  --articles-dir data/corpus/articles \
  --state-db data/curation/initial.sqlite
```

On the first run, the command:

1. loads every article artifact in deterministic article order while preserving
   passage order within each article;
2. fingerprints the exact artifact set, including articles with no passages;
3. creates the SQLite state database;
4. binds it to that fingerprint and to rubric
   `tolkien-corpus-rubric-v1`; and
5. displays the first passage without a current decision.

Later runs with the same arguments resume the ordinary-review cursor. Passages
already classified or deferred are skipped in ordinary review.

## Read the cockpit

A frame resembles:

```text
CORPUS CURATION
Progress · Article 1/69 · Passage 1/13 · Overall 1/605
Rubric · tolkien-corpus-rubric-v1
Source · Aragorn › Lead
STATUS · Ready — choose L/W/A/D/R, or S to defer.
Question · Classify this passage under the current corpus-curation rubric.
──────────────────────────────────────────────────────────────────────────────
TARGET PASSAGE
│ Aragorn leads the Company of the Ring ...
──────────────────────────────────────────────────────────────────────────────
After · Tolkien developed the character of Aragorn ... [truncated]
[L] Lore  [W] Writing  [A] Analysis  [D] Adaptation
[R] Reference  [S] Defer  [U] Undo  [Space] Context  [?] Help  [Q] Quit
```

The fields mean:

- `Articles` is the current article number and total number of articles that
  contribute passages.
- `Article passages` is the current passage position within that article.
- `Overall` is the current position among all extracted passages. It is source
  position, not the number of decisions completed.
- `Source` combines the article title and heading path to identify where the
  target came from.
- `Before` and `After` are surrounding passages from the same article. They are
  context only; the passage below `TARGET` is the one receiving the decision.
- `STATUS` reports whether the cockpit is ready, saved, undone, or unable to
  save. Read it whenever anything unexpected happens.

The cockpit reserves one terminal column and wraps its own lines, so it does
not rely on terminal auto-wrapping. Compact mode shows at most one
width-aware, truncated neighboring snippet on each available side. Press Space
to show up to two full neighboring passages on each side. The target passage is
always shown in full and explicitly wrapped inside its delineated block.

## Classify a passage

Press one key; do not press Enter afterward.

| Key | Classification | Use when the passage principally contains |
|---|---|---|
| `L` | internal lore | fictional setting, chronology, characters, peoples, places, objects, languages, or events |
| `W` | external creation history | drafting, authorship, publication, textual development, influences, naming, or creative intent |
| `A` | analysis or reception | interpretation, themes, criticism, scholarship, reviews, popularity, awards, or cultural impact |
| `D` | adaptation material | film, television, radio, stage, game, casting, production, or adaptation-specific depictions |
| `R` | reference or administrative | bibliography, navigation, disambiguation, source administration, or prose without a self-contained evidentiary claim |
| `S` | deferred, not classified | a decision needs more context or deliberate later review |

The full rubric and mixed-passage rule are defined in
[Corpus curation](../product/capabilities/corpus-curation.md#use-a-versioned-human-rubric).
In particular, classify the whole extracted passage. If substantive lore and
non-lore claims are mixed, choose the principal non-lore reason rather than
admitting only the lore portion. When the correct exclusion reason is unclear,
press `S` instead of guessing.

After `L`, `W`, `A`, `D`, `R`, or `S`, the cockpit performs one SQLite
transaction that records the evidence frame, question, semantic answer,
rubric, timestamp, and supersession relationship, and then advances the saved
cursor. The next frame shows `STATUS: SAVED: ...` for the answer just recorded.

The same action key is ignored for 1.25 seconds after an answer. This prevents
a held key from classifying a newly displayed passage. Different decision keys
and navigation controls remain immediately responsive.

## Use the remaining controls

| Key | Behavior |
|---|---|
| Space | Toggle compact and expanded surrounding context without changing state |
| `?` | Show the concise classification reminder in the status area |
| `U` | Append an undo event for the most recent active classify/defer action and return to that passage |
| `Q` | Quit after restoring normal terminal behavior |
| Ctrl-C or Ctrl-D | Exit safely and restore normal terminal behavior |

Undo never deletes audit history. After undo returns to the passage, press a
classification key to answer it again or `Q` to leave it undecided for the next
ordinary session.

Because each answer is durable before advancement, it is safe to work in short
sessions. There is no separate save command and no need to finish an article
before quitting.

## Resume ordinary review

Rerun the original command with the same two paths:

```bash
uv run meta corpus curate \
  --articles-dir data/corpus/articles \
  --state-db data/curation/initial.sqlite
```

The cockpit resumes at the saved ordinary-review position. If that position is
complete, it finds the next undecided passage in deterministic corpus order. If
no undecided passages remain, it shows the completion summary and exits.

Do not create a new state filename merely to resume. A new filename starts an
independent decision history rather than continuing the existing one.

## Review deferred passages

Once ordinary review is complete—or whenever you want a focused uncertainty
pass—use the same artifact directory and state database with
`--review-deferred`:

```bash
uv run meta corpus curate \
  --articles-dir data/corpus/articles \
  --state-db data/curation/initial.sqlite \
  --review-deferred
```

This mode shows only passages whose effective state is deferred:

- Pressing `L`, `W`, `A`, `D`, or `R` explicitly supersedes the defer with that
  classification.
- Pressing `S` keeps the passage deferred for a future deferred-review session.
  It will not loop back during the current session.
- Ordinary and deferred review keep separate resume positions. Starting one
  mode does not consume the other mode's saved cursor.

When no deferred passages remain for the session, the cockpit shows the same
summary used at ordinary completion.

## Interpret the completion summary

The summary reports counts for all five classifications plus `deferred`,
`undecided`, and `total`.

For curation to be complete, both `deferred` and `undecided` should be zero.
Only effective internal-lore decisions are eligible for a future corpus
release. This command does not yet create or validate that release.

## Version the curation record

After quitting the cockpit, export the closed SQLite working database:

```bash
uv run meta corpus export-curation \
  --state-db data/curation/initial.sqlite \
  --output data/curation/initial.jsonl
```

The exporter writes deterministic UTF-8 JSON Lines in audit-event ID order and
atomically replaces the prior JSONL snapshot. With unchanged SQLite input,
repeated exports are byte-identical. Review the Git diff and commit the JSONL
after each curation session that changes state.

Treat `data/curation/initial.jsonl` as the portable source of curation evidence
and the SQLite database as its writable operational form:

- Do not edit the JSONL or SQLite tables manually.
- Do not export while the cockpit is running; a consistent export could still
  omit decisions saved after the export transaction begins.
- Do not delete the SQLite working file until its latest decisions have been
  exported and the JSONL has been loaded successfully as a verification check.
- Do not use the acquisition backup command as proof that curation is backed
  up; that command protects acquisition evidence. Git and an external copy of
  the tracked JSONL protect curation evidence.

## Respond to errors

### `corpus curation requires an interactive TTY`

Run the command directly in a terminal. Remove pipes, output redirection, or a
non-interactive job wrapper.

### `curation state belongs to an incompatible artifact set`

The article artifacts no longer match the set bound to the state database.
Return to the original immutable artifact set, or deliberately choose a new
state database for the new acquisition. Do not rename or delete the existing
database as a workaround; retain it with the artifacts it describes.

### `curation state belongs to an incompatible rubric`

The database was created under another rubric. Retain it for audit history and
start the separately governed review required by the new rubric. Do not alter
the rubric identifier inside SQLite.

### `SAVE FAILED`

The answer was not recorded and the cockpit remains on the same passage. Stop
classifying, note the underlying SQLite error shown in the status line, and
check filesystem space, directory permissions, and whether another process is
using the database. Quit safely with `Q` if the problem is not immediately
recoverable. After correcting it, resume with the same command and state file.

### The screen looks corrupted after an abnormal termination

Run this shell command to restore normal terminal settings:

```bash
stty sane
```

Then resume with the same curation command.

## Current limitations

The cockpit is intentionally passage-only. It does not yet provide article or
section bulk decisions, anomaly review, notes, release validation or
publication, activation, or retrieval. The current summary is operational
feedback, not a published corpus release.
