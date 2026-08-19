# Research: first vertical pass

## 1. Which command groups and execution paths does the `meta` CLI expose today, and where does its current surface stop short of runtime lore retrieval or question answering?

### Findings

- The package installs one console entry point, `meta`, and exposes one top-level command group, `corpus`.
- `meta corpus` has nine execution paths: `discover`, `acquire`, `backup`, `verify-backup`, `curate`, `export-curation`, `load-curation`, `create-release`, and `validate-release`.
- The command surface ends at offline discovery/acquisition, backup, terminal curation, curation snapshot exchange, and immutable release creation/validation. It has no search, context, retrieve, ask, answer, activation, planning, generation, evaluation, or web-runtime command.
- A validated release is retained content authority only. It is not an active runtime corpus.

### Evidence

- `pyproject.toml:12` defines the `meta` entry point and `pyproject.toml:13` targets `middle_earth_travel_agency.cli:console`.
- `src/middle_earth_travel_agency/cli.py:36` builds the parser, and `src/middle_earth_travel_agency/cli.py:40` creates the sole `corpus` group.
- `src/middle_earth_travel_agency/cli.py:43`, `src/middle_earth_travel_agency/cli.py:55`, `src/middle_earth_travel_agency/cli.py:72`, `src/middle_earth_travel_agency/cli.py:85`, `src/middle_earth_travel_agency/cli.py:90`, `src/middle_earth_travel_agency/cli.py:108`, `src/middle_earth_travel_agency/cli.py:118`, `src/middle_earth_travel_agency/cli.py:126`, and `src/middle_earth_travel_agency/cli.py:134` define the nine subcommands.
- `src/middle_earth_travel_agency/cli.py:343` dispatches only those commands.
- `README.md:17` describes the implemented slice; `README.md:22` states that activation, retrieval indexing, travel planning, guide generation, evaluation, and the web experience are not implemented.
- `docs/runbooks/release-corpus.md:64` documents the current boundary, and `docs/runbooks/release-corpus.md:66` distinguishes validation from activation.

### Unknowns

- The repository does not define a runtime lore-query command name, arguments, output shape, or process boundary.

## 2. Which terminal interaction, rendering, input, status, and error-handling behaviors make up the current curation cockpit?

### Findings

- Both stdin and stdout must be interactive TTYs. The CLI loads the corpus, opens SQLite curation state, runs the cockpit, and closes state on every exit path.
- The cockpit enters raw terminal mode, hides the cursor, clears and homes the display for each frame, reads one character at a time case-insensitively, and restores terminal attributes and cursor visibility in nested `finally` blocks.
- Each frame contains article/passage/overall progress, rubric, article title and heading path, a color-coded status, the curation question, target text, neighboring context, and the key legend. Output is wrapped within terminal width minus one column, with a minimum width of 40 columns, and is normalized to CRLF. `NO_COLOR` disables styling.
- Compact context contains one truncated neighboring passage on each side; expanded context contains up to two full neighboring passages on each side. Space toggles the mode.
- `L/W/A/D/R` classify, `S` defers, `U` appends an undo and returns to the affected passage, `?` shows help, and `Q`, Ctrl-C, or Ctrl-D exits. Undecided and deferred modes retain independent resume cursors.
- Each decision atomically stores its action/classification, question, visible evidence snapshot, semantic answer, timestamp, and supersession link before cursor advancement. Undo is also append-only.
- A SQLite save error changes status to `SAVE FAILED` and retains the current passage. Held repeats of an action key are suppressed for 1.25 seconds, and queued input is flushed after a successful save. Completion prints a classification summary; EOF returns without changing state.
- The console wrapper prints expected `OSError`, `ValueError`, and JSON decoding failures as `error: ...` on stderr and exits with status 1.

### Evidence

- `src/middle_earth_travel_agency/cli.py:289` enforces TTY use and `src/middle_earth_travel_agency/cli.py:294` closes state in `finally`.
- `src/middle_earth_travel_agency/corpus_curation.py:427` renders a frame; `src/middle_earth_travel_agency/corpus_curation.py:442` reserves the final column; `src/middle_earth_travel_agency/corpus_curation.py:451` builds progress; `src/middle_earth_travel_agency/corpus_curation.py:461` builds the visible fields and controls.
- `src/middle_earth_travel_agency/corpus_curation.py:346` selects compact or expanded neighbors, and `src/middle_earth_travel_agency/corpus_curation.py:357` truncates compact snippets.
- `src/middle_earth_travel_agency/corpus_curation.py:486` normalizes output to CRLF; `src/middle_earth_travel_agency/corpus_curation.py:492` determines terminal width; `src/middle_earth_travel_agency/corpus_curation.py:500` honors `NO_COLOR`.
- `src/middle_earth_travel_agency/corpus_curation.py:504` implements repeat suppression, and `src/middle_earth_travel_agency/corpus_curation.py:519` flushes queued input.
- `src/middle_earth_travel_agency/corpus_curation.py:533` runs the cockpit; `src/middle_earth_travel_agency/corpus_curation.py:549` enters raw mode; `src/middle_earth_travel_agency/corpus_curation.py:572` reads one character; `src/middle_earth_travel_agency/corpus_curation.py:578` processes decisions; `src/middle_earth_travel_agency/corpus_curation.py:594` handles save failures; `src/middle_earth_travel_agency/corpus_curation.py:599` handles undo and other controls; `src/middle_earth_travel_agency/corpus_curation.py:625` restores the terminal.
- `src/middle_earth_travel_agency/corpus_curation.py:250` records decisions atomically, and `src/middle_earth_travel_agency/corpus_curation.py:296` records undo.
- `src/middle_earth_travel_agency/cli.py:367` wraps the console and `src/middle_earth_travel_agency/cli.py:370` defines the caught operator-error classes.

### Unknowns

- Terminal-emulator-specific display of ANSI control sequences is outside repository behavior.
- Exceptions outside the console wrapper's three caught categories follow ordinary Python propagation.

## 3. How does the current release builder determine the effective classification of each passage and admit only internal-lore passages to a release?

### Findings

- An event is ineffective when an `undo` event points to its ID. Remaining `classify` and `defer` events are processed in audit order into a passage-ID map, so the last remaining event for a passage is effective.
- The builder binds the snapshot to the loaded corpus fingerprint and rejects snapshot events for unknown passage IDs.
- Release creation requires an effective event for every corpus passage and rejects any effective defer or undecided passage.
- Only passages whose effective classification is exactly `internal lore` are grouped into the release's article-to-passage selection. An empty lore selection is rejected.
- The manifest's `articles` list contains only articles with at least one selected lore passage. The immutable release directory still retains exact copies of every source article artifact and the curation snapshot; non-lore material is excluded from admission by the manifest's ordered `lore_passage_ids`, not removed from retained JSON.

### Evidence

- `src/middle_earth_travel_agency/corpus_release.py:18` fixes schema and selection constants, and `src/middle_earth_travel_agency/corpus_release.py:20` defines the admitted classification.
- `src/middle_earth_travel_agency/corpus_release.py:68` computes effective events.
- `src/middle_earth_travel_agency/corpus_release.py:84` loads and binds corpus and snapshot; `src/middle_earth_travel_agency/corpus_release.py:89` rejects unknown passage IDs.
- `src/middle_earth_travel_agency/corpus_release.py:95` counts deferred and undecided passages and `src/middle_earth_travel_agency/corpus_release.py:98` rejects incomplete curation.
- `src/middle_earth_travel_agency/corpus_release.py:103` groups internal-lore passage IDs by article; `src/middle_earth_travel_agency/corpus_release.py:107` rejects an empty selection.
- `src/middle_earth_travel_agency/corpus_release.py:139` excludes articles with no lore passage, and `src/middle_earth_travel_agency/corpus_release.py:141` emits lore-bearing article records.
- `src/middle_earth_travel_agency/corpus_release.py:193` stages every article and `src/middle_earth_travel_agency/corpus_release.py:200` retains the curation snapshot.

### Unknowns

- The builder validates structure and identity but does not independently reassess the semantic correctness of an operator's effective classification.

## 4. What article, passage, section, ordering, and normalized-text fields are currently available for constructing a lexical search projection from a retained release?

### Findings

- Article identity and searchable title are available as `article_artifact_id` and `canonical_title`.
- Each extracted passage has `passage_id`, `article_artifact_id`, full hierarchical `heading_path`, per-heading `paragraph_ordinal`, `normalized_text`, and `structure` (`prose paragraph`). The in-memory `Passage` model pairs those values with the article title.
- Headingless content is represented by the synthetic path `Lead`. Paragraph ordinals increment independently for each exact heading path.
- Text normalization removes `<ref>` tags, strips wiki markup with normalized/collapsed rendering, and collapses whitespace.
- Corpus order is deterministic by case-folded article title and article ID. Within an article, extracted-passage array order remains source order; paragraph ordinals are not global and restart under each heading.
- The manifest supplies the exact admitted lore passage IDs. Projection inputs therefore require a join from manifest membership to retained article and passage records.

### Evidence

- `src/middle_earth_travel_agency/corpus_curation.py:47` defines `Passage` and its retained fields.
- `src/middle_earth_travel_agency/corpus_curation.py:88` loads article artifacts; `src/middle_earth_travel_agency/corpus_curation.py:102` reads article ID/title; `src/middle_earth_travel_agency/corpus_curation.py:111` validates passage fields.
- `src/middle_earth_travel_agency/corpus_curation.py:131` creates deterministic corpus order, and `src/middle_earth_travel_agency/corpus_curation.py:136` records that extraction order is source order while ordinals restart.
- `src/middle_earth_travel_agency/corpus_acquisition.py:434` emits blocks in source order; `src/middle_earth_travel_agency/corpus_acquisition.py:444` creates `Lead`; `src/middle_earth_travel_agency/corpus_acquisition.py:446` increments per-heading ordinals.
- `src/middle_earth_travel_agency/corpus_acquisition.py:483` normalizes prose.
- `src/middle_earth_travel_agency/corpus_acquisition.py:530` creates passage identity and `src/middle_earth_travel_agency/corpus_acquisition.py:531` writes the passage fields.
- `src/middle_earth_travel_agency/corpus_release.py:141` emits each lore-bearing article and `src/middle_earth_travel_agency/corpus_release.py:146` emits its selected passage IDs.

### Unknowns

- No current projection schema defines a derived section string, global passage ordinal, index row shape, or searchable-field storage layout.

## 5. What does the current `corpus-v1-rc1` manifest identify directly, and which passage text and section details require joining its lore passage identifiers back to retained article artifacts?

### Findings

- Each lore-bearing manifest article directly identifies its article artifact ID and digest, canonical title, ordered lore passage IDs, page ID, revision ID, and revision timestamp.
- The complete `corpus_articles` inventory maps every retained article artifact ID to its filename and SHA-256, including articles with no admitted lore.
- The manifest also directly identifies release ID, schema version, selection policy, counts, corpus fingerprint, rubric ID, curation snapshot digest, and pinned source snapshot.
- It does not inline passage text, heading path, paragraph ordinal, or structure. Resolving those requires mapping article ID to `corpus_articles[].artifact_filename`, opening that retained JSON, and matching each manifest `lore_passage_ids` value to `extracted_passages[].passage_id`.
- The matched passage provides `heading_path`, `normalized_text`, `paragraph_ordinal`, and `structure`. The article artifact additionally provides permanent revision and history URLs, source snapshot, extractor identity/configuration, and raw wikitext, none of which is in a lore-passage manifest record.

### Evidence

- `data/releases/corpus-v1-rc1/manifest.json:2` begins the lore-bearing article list; `data/releases/corpus-v1-rc1/manifest.json:4` identifies the first article; `data/releases/corpus-v1-rc1/manifest.json:7` lists its lore passage IDs; `data/releases/corpus-v1-rc1/manifest.json:14` records page and revision identity.
- `data/releases/corpus-v1-rc1/manifest.json:696` begins the complete article inventory and `data/releases/corpus-v1-rc1/manifest.json:698` maps ID, filename, and digest.
- `data/releases/corpus-v1-rc1/manifest.json:1043` records counts; `data/releases/corpus-v1-rc1/manifest.json:1047` records curation identity; `data/releases/corpus-v1-rc1/manifest.json:1052` records release identity and policy; `data/releases/corpus-v1-rc1/manifest.json:1055` records source identity.
- `data/releases/corpus-v1-rc1/articles/article_04bca56fb73e830f1908e048ad6671216e2af97892b5d91480dca8ee46842352.json:5` begins Aragorn's passage records; `data/releases/corpus-v1-rc1/articles/article_04bca56fb73e830f1908e048ad6671216e2af97892b5d91480dca8ee46842352.json:8` supplies heading path; `data/releases/corpus-v1-rc1/articles/article_04bca56fb73e830f1908e048ad6671216e2af97892b5d91480dca8ee46842352.json:11` supplies normalized text; `data/releases/corpus-v1-rc1/articles/article_04bca56fb73e830f1908e048ad6671216e2af97892b5d91480dca8ee46842352.json:12` supplies ordinal; `data/releases/corpus-v1-rc1/articles/article_04bca56fb73e830f1908e048ad6671216e2af97892b5d91480dca8ee46842352.json:13` supplies the joined passage ID.
- `src/middle_earth_travel_agency/corpus_release.py:132` defines the complete inventory and `src/middle_earth_travel_agency/corpus_release.py:141` defines direct lore-bearing article fields.

### Unknowns

- The manifest has no standalone passage-to-filename table or precomputed display section label.

## 6. Which lore-bearing subjects, titles, headings, terms, and cross-article relationships are represented by the 51 articles and 182 lore passages in the current release?

### Findings

- The release contains 51 lore-bearing article titles and 182 admitted lore passages.
- People, creatures, and peoples: Aragorn, Arwen, Bard the Bowman, Beorn, Boromir, Denethor, Drúedain, Elendil, Ent, Faramir, Frodo Baggins, Galadriel, Gandalf, Glorfindel, Gollum, Húrin, Isildur, Melian, Morgoth, Nazgûl, Samwise Gamgee, Saruman, Shelob, Smaug, Thingol, Thorin Oakenshield, Treebeard, Túrin Turambar, Éomer, and Éowyn.
- Places, realms, and history: Beleriand, Forests in Middle-earth, Gondolin, Gondor, History of Arda, Isengard, Lothlórien, Middle-earth, Mirkwood, Mordor, Númenor, Old Forest, `Rohan, Middle-earth`, and Valinor.
- Events: Battle of Helm's Deep, Battle of the Morannon, and Battle of the Pelennor Fields.
- Works and adaptation records: The Hobbit, The Lord of the Rings, The Lord of the Rings: The Return of the King, and List of original characters in The Lord of the Rings film series.
- The 81 distinct full heading paths include lead material; fictional biography, history, geography, role, and account; plot, narrative, and appearances; First, Second, and Third Ages; War of the Ring; battles and aftermath; realms and landmarks; language, names, steeds, Entwives, Barad-dûr, the White Council, Númenórean kingdom, Quenta Silmarillion, and Years of the Trees. Admitted passages also occur under source headings including `Analysis`, `Concept and creation`, `Comparison to the source material`, and `In William Morris's fantasies`; heading labels are source structure and are independent of curation classification.
- Terms are unstructured content in `normalized_text`, not controlled entities. Recurring represented clusters include Arda's creation and Ages; Valar, Maiar, Elves, Men, Dwarves, Hobbits, Ents, and Orcs; Númenor, Gondor, Rohan, Mordor, and Elven realms; Sauron, Morgoth, the Rings, and the War of the Ring; the Hobbit expedition and Smaug; First-Age Beleriand and Gondolin; forests and their inhabitants; and named battles and routes.
- Cross-article relationships exist only as prose. Examples include Arwen's ancestry and marriage links among Aragorn, Elrond, Númenor/Gondor, and Melian, and plot prose that connects Frodo, Gandalf, Aragorn, Gollum, the Old Forest, Rivendell, and the wider Ring journey. There is no stored edge type or relationship record.

### Evidence

- `data/releases/corpus-v1-rc1/manifest.json:2` begins the ordered 51-title inventory; `data/releases/corpus-v1-rc1/manifest.json:1043` records 51 articles and 182 lore passages; `data/releases/corpus-v1-rc1/manifest.json:1054` records the selection policy.
- `src/middle_earth_travel_agency/corpus_curation.py:47` shows that retained passages have no term or relationship fields.
- `src/middle_earth_travel_agency/corpus_acquisition.py:531` defines the complete extracted-passage record, whose content field is `normalized_text` and whose structure field is `heading_path`.
- `data/releases/corpus-v1-rc1/articles/article_09fbe31cc1da4059ac96a29f55a6b74fd1299706052dfdc35d2c58ce55b16c9b.json:43` contains the admitted Arwen relationship passage.
- `data/releases/corpus-v1-rc1/articles/article_07fcfc6ba904346775aefcd6de6e7c88d834755f94e7a0af7d834980ddc78534.json:23` contains a joined plot passage spanning multiple released people and places.

### Unknowns

- The repository defines no canonical entity catalog, alias normalization, relationship types, or rule for treating a textual mention as an edge.

## 7. Which current files or records, if any, designate one validated corpus release as active, and how is the absence of release activation represented today?

### Findings

- No current file, manifest field, database record, configuration value, or CLI command designates an active release.
- `corpus-v1-rc1` identifies itself and its retained contents but has no active-state field.
- Curation SQLite metadata is exactly `corpus_fingerprint` and `rubric_id`; it contains no activation key.
- The absence of activation is represented as absence of runtime state plus explicit documentation that activation and retrieval indexing are not implemented. A validated manifest remains retained content authority rather than a runtime corpus.
- Product documents describe an intended invariant of at most one active validated release, but no executable mechanism currently enforces or represents it.

### Evidence

- `data/releases/corpus-v1-rc1/manifest.json:1052` records release ID through source snapshot without an active field.
- `src/middle_earth_travel_agency/curation_snapshot.py:16` defines snapshot metadata and `src/middle_earth_travel_agency/curation_snapshot.py:17` restricts it to corpus fingerprint and rubric ID.
- `src/middle_earth_travel_agency/cli.py:316` creates releases and `src/middle_earth_travel_agency/cli.py:330` validates them; no activation handler exists in the dispatcher at `src/middle_earth_travel_agency/cli.py:343`.
- `README.md:22`, `docs/runbooks/index.md:13`, and `docs/runbooks/release-corpus.md:64` explicitly record the absent implementation.
- `docs/product/capabilities/corpus-curation.md:48` states the intended at-most-one-active invariant, and `docs/adr/0002-use-immutable-curated-corpus-releases.md:21` describes activation intent.

### Unknowns

- Activation record location, schema, locking/transaction behavior, and the stored representation of “no active release” are not fixed.

## 8. What tables and responsibilities belong to the existing curation SQLite database, and what retrieval-index schema or FTS tables already exist in the repository?

### Findings

- `curation_meta(key, value)` binds working state to a corpus fingerprint and rubric ID.
- `audit_events` is the append-only history of classify, defer, and undo actions, with passage, classification, rubric, question, visible evidence, semantic answer, timestamp, and supersession identity.
- `session_state` is a singleton row with general, undecided, and deferred resume cursors.
- Snapshot export/load treats those three tables and their exact columns as the complete supported curation schema. Article and passage content remains in immutable JSON and is loaded into memory rather than copied into curation SQLite.
- No retrieval database, index schema, FTS virtual table, BM25 invocation, search module, or compatibility table exists. SQLite FTS is present only as an accepted product/architecture decision.
- Acquisition creates a temporary `redirects(source_key, target_title)` SQLite table while scanning the dump. It is acquisition-only, temporary, and unrelated to retrieval.

### Evidence

- `src/middle_earth_travel_agency/corpus_curation.py:32` defines the curation schema; `src/middle_earth_travel_agency/corpus_curation.py:33` defines `curation_meta`; `src/middle_earth_travel_agency/corpus_curation.py:34` defines `audit_events`; `src/middle_earth_travel_agency/corpus_curation.py:40` defines `session_state`.
- `src/middle_earth_travel_agency/corpus_curation.py:180` initializes metadata, `src/middle_earth_travel_agency/corpus_curation.py:205` reads active audit events, and `src/middle_earth_travel_agency/corpus_curation.py:250` records events.
- `src/middle_earth_travel_agency/curation_snapshot.py:16` defines the supported snapshot schema and `src/middle_earth_travel_agency/curation_snapshot.py:36` enumerates all three tables and columns.
- `src/middle_earth_travel_agency/corpus_curation.py:88` loads article JSON into memory.
- `src/middle_earth_travel_agency/corpus_acquisition.py:598` opens the temporary redirects database and `src/middle_earth_travel_agency/corpus_acquisition.py:604` creates its sole table.
- `docs/adr/0003-use-sqlite-full-text-search-for-initial-retrieval.md:12` begins the accepted decision and `docs/adr/0003-use-sqlite-full-text-search-for-initial-retrieval.md:14` specifies SQLite full-text search as intent.
- `README.md:22` states retrieval indexing is not implemented.

### Unknowns

- Retrieval table names, FTS version/layout, status and compatibility metadata, migration rules, and index database location are all undefined.

## 9. What narrow search and immediate-context operations are established in the current product documents, including their authority boundaries and permitted result data?

### Findings

- Product intent defines two agent operations: plain-text search over approved passages and immediate context for a passage the agent found.
- Retrieval owns the rebuildable projection, internal active-release resolution, plain-text search, immediate context, and the controlled retrieval-disabled condition. It does not curate, select the active release, write answers, decide whether results support claims, or construct traveler-facing citations.
- Search is scoped internally to the sole active release. The caller and agent cannot select, enumerate, or override releases. Plain-text input cannot alter fields, filters, ranking configuration, release scope, or result limits.
- Permitted results are approved passage text and stable evidence identity. Raw wikitext, internal paths, curation history, and license presentation are excluded.
- Context remains within the same article and section and cannot skip excluded material. The retrieval-disabled evaluation condition causes both operations to return no evidence.
- An unavailable or incompatible index is an explicit failure, not an empty result, repair attempt, or fallback to another release.
- These are documentary contracts only; neither operation currently has executable code.

### Evidence

- `docs/product/capabilities/corpus-retrieval.md:19` defines capability ownership and `docs/product/capabilities/corpus-retrieval.md:25` defines excluded authority.
- `docs/product/capabilities/corpus-retrieval.md:30` binds the index to one release; `docs/product/capabilities/corpus-retrieval.md:32` removes release choice from callers; `docs/product/capabilities/corpus-retrieval.md:34` limits indexed results; `docs/product/capabilities/corpus-retrieval.md:36` defines permitted and withheld result data; `docs/product/capabilities/corpus-retrieval.md:38` restricts query authority.
- `docs/product/capabilities/corpus-retrieval.md:40` defines immediate-context boundaries; `docs/product/capabilities/corpus-retrieval.md:42` defines index failure; `docs/product/capabilities/corpus-retrieval.md:47` defines disabled behavior.
- `docs/product/capabilities/corpus-retrieval.md:60` names the two narrow agent operations.
- `README.md:22` records their absence from the implementation.

### Unknowns

- Tool names and signatures, result schema, score exposure, context cardinality, and error types are not defined.

## 10. Which tokenizer, indexed fields, weights, ranking behavior, result bounds, and compatibility metadata are fixed by the current repository, and which are only identified as implementation-owned configuration?

### Findings

- Fixed intent: SQLite full-text lexical retrieval indexes approved article title, heading/section, and passage text from one immutable release.
- Fixed boundaries: only passages admitted as internal lore are searchable; runtime resolves the sole active release; results are deterministic and bounded; the caller cannot change fields, filters, ranking, scope, or limits; ranking does not impose a per-article diversity quota; unavailable/incompatible indexes fail explicitly without fallback.
- The repository fixes no concrete tokenizer or tokenizer options, field weights, ranking expression, query translation, numeric result limit, score normalization, tie breaker, or compatibility/readiness metadata schema.
- Tokenizer, weights, and exact ranking are explicitly implementation-owned code plus rebuildable index metadata. The requirement to retain enough configuration with the index for reproduction is fixed; the configuration values and metadata fields are absent.

### Evidence

- `docs/adr/0003-use-sqlite-full-text-search-for-initial-retrieval.md:14` fixes SQLite FTS and indexed logical fields; `docs/adr/0003-use-sqlite-full-text-search-for-initial-retrieval.md:16` places tokenizer and ranking configuration with the rebuildable index.
- `docs/product/capabilities/corpus-retrieval.md:30` fixes release scope; `docs/product/capabilities/corpus-retrieval.md:34` fixes admitted content; `docs/product/capabilities/corpus-retrieval.md:38` prohibits caller control; `docs/product/capabilities/corpus-retrieval.md:42` fixes explicit incompatibility failure.
- `docs/product/capabilities/corpus-retrieval.md:52` establishes the lexical baseline; `docs/product/capabilities/corpus-retrieval.md:56` assigns tokenizer, weights, and ranking to code and index metadata.
- `docs/product/capabilities/corpus-retrieval.md:66` rejects an artificial source-diversity quota; `docs/product/capabilities/corpus-retrieval.md:74` requires a deterministic bounded result set.
- `README.md:22` confirms that no retrieval implementation or metadata currently exists.

### Unknowns

- It is unresolved whether compatibility identity will include release/manifest digest, manifest schema, index schema, tokenizer/config version, SQLite/FTS version, or another set of fields.

## 11. How can immediate preceding and following context be reconstructed from current article artifacts without crossing article or section boundaries or skipping excluded material?

### Findings

- Extraction emits blocks in source order. Each block receives a `paragraph_ordinal` within its exact full `heading_path` before structural classification.
- Accepted prose retains article ID, heading path, ordinal, normalized text, and passage ID. Structural exclusions retain the same heading path and ordinal with type and reason. The manifest identifies the subset of accepted prose admitted as lore.
- Current coordinates permit immediate context to be determined on each side of a target by staying in its article, requiring the exact same full heading path, and inspecting only ordinal `target - 1` or `target + 1`. A neighbor is eligible only when that exact coordinate is an extracted passage whose passage ID is admitted by the release.
- A structural exclusion, a non-lore extracted passage, an absent ordinal, or a section change stops context on that side. Taking the next item from an admitted-lore-only list would skip material and manufacture continuity.
- Ordinal gaps are meaningful because a block that normalizes to empty is omitted without a structural-exclusion record.
- The current curation `_context` helper is not a retrieval-context implementation: it groups only by article and selects adjacent loaded extracted passages. It does not enforce equal heading path, consecutive ordinal, structural-exclusion boundaries, or release admission.

### Evidence

- `src/middle_earth_travel_agency/corpus_acquisition.py:434` emits source-ordered blocks; `src/middle_earth_travel_agency/corpus_acquisition.py:444` selects the heading path; `src/middle_earth_travel_agency/corpus_acquisition.py:446` assigns ordinals before classification.
- `src/middle_earth_travel_agency/corpus_acquisition.py:516` classifies each coordinate; `src/middle_earth_travel_agency/corpus_acquisition.py:518` records structural exclusions with heading and ordinal; `src/middle_earth_travel_agency/corpus_acquisition.py:527` normalizes accepted prose; `src/middle_earth_travel_agency/corpus_acquisition.py:528` drops normalized-empty blocks; `src/middle_earth_travel_agency/corpus_acquisition.py:530` records passage identity and coordinates.
- `src/middle_earth_travel_agency/corpus_release.py:103` builds the admitted lore set and `src/middle_earth_travel_agency/corpus_release.py:146` stores it in the manifest.
- `src/middle_earth_travel_agency/corpus_curation.py:131` preserves extraction-array order and `src/middle_earth_travel_agency/corpus_curation.py:346` implements the broader article-only curation neighbor logic.
- `docs/product/capabilities/corpus-retrieval.md:40` prohibits context crossing an article/section or skipping excluded material.

### Unknowns

- Runtime context cardinality and whether a stopped side is represented by omission or an explicit boundary marker are not specified.

## 12. Which current modules, dependencies, configuration values, or internal contracts provide model invocation and agent tool orchestration, and where is their present absence or unresolved status recorded?

### Findings

- No current module invokes a model or orchestrates agent tools. Package modules cover acquisition, backup, curation, snapshots, releases, and their CLI.
- Runtime dependencies are `mwparserfromhell`, `python-dotenv`, and `pywikibot`; no model SDK or agent framework is declared.
- The only environment-backed setting read by the current CLI is `META_WIKIMEDIA_CONTACT`, used for Wikimedia access.
- Product intent assigns consultation orchestration, allowed tools, typed output, cancellation, and tool-failure policy to travel planning. It limits intended lore evidence tools to approved-passage search and immediate context.
- Model/provider selection remains an explicit open product question. No invocation API, model configuration, structured-output schema, executable tool schema, or orchestration contract exists in code.

### Evidence

- `src/middle_earth_travel_agency/cli.py:16` through `src/middle_earth_travel_agency/cli.py:28` import the complete current package-owned workflows.
- `pyproject.toml:6` declares all runtime dependencies and `pyproject.toml:10` closes the list without a model dependency.
- `src/middle_earth_travel_agency/cli.py:37` reads `META_WIKIMEDIA_CONTACT`.
- `README.md:17` describes the implemented modules and `README.md:22` states that retrieval, planning, and generation are absent.
- `docs/product/capabilities/travel-planning.md:23` assigns orchestration and allowed tools to planning; `docs/product/capabilities/travel-planning.md:46` limits lore evidence operations; `docs/product/capabilities/travel-planning.md:48` requires typed application output; `docs/product/capabilities/travel-planning.md:49` defines cancellation/tool-failure behavior as intent.
- `docs/product/capabilities/corpus-retrieval.md:60` identifies the two intended tools.
- `docs/product/open-questions.md:27` leaves model and provider unresolved.

### Unknowns

- Model/provider, model configuration, invocation module/API, typed response contract, and executable tool schemas are all unresolved.

## 13. What factual-answer, abstention, uncertainty, and claim-to-passage binding rules currently constrain a lore answer produced from retrieved passages?

### Findings

- Product rules require every factual lore claim to use retrieved evidence from the attempt's associated corpus release. Pretrained model knowledge can help form queries or explanations but is not evidence and is not a fallback.
- Empty or insufficient evidence leads to explicit qualification, a request for an assumption, omission, or abstention. Related but insufficient results cannot be completed from model memory.
- Conflicting or uncertain evidence remains visibly uncertain rather than being reconciled inventively.
- Travel inference must be grounded in cited facts, conservative, and visibly labeled.
- The planning component that determines a factual claim's meaning also supplies its claim-to-passage binding. Downstream presentation may validate and resolve that binding but cannot invent support.
- Citations are claim-specific and must resolve within the response's immutable release to the exact source revision. Abstentions and claim-free messages need no fabricated citations.
- These constraints are product-document invariants and have no executable enforcement today.

### Evidence

- `docs/product/principles.md:25` requires evidence before fluency; `docs/product/principles.md:31` defines honest insufficient-evidence outcomes; `docs/product/principles.md:37` constrains inference.
- `docs/product/capabilities/travel-planning.md:33` requires release-bound retrieved evidence; `docs/product/capabilities/travel-planning.md:36` rejects model knowledge as fallback; `docs/product/capabilities/travel-planning.md:38` preserves uncertainty; `docs/product/capabilities/travel-planning.md:46` limits evidence tools.
- `docs/product/capabilities/travel-planning.md:63` assigns claim binding to planning and `docs/product/capabilities/travel-planning.md:65` prohibits downstream invented support.
- `docs/product/capabilities/travel-planning.md:87` gives the insufficient-road-condition example and `docs/product/capabilities/travel-planning.md:89` gives the conflicting-chronology example.
- `docs/product/capabilities/evidence-and-attribution.md:30` requires release- and revision-resolved citations; `docs/product/capabilities/evidence-and-attribution.md:34` requires claim specificity; `docs/product/capabilities/evidence-and-attribution.md:38` allows claim-free abstention without fabricated citations.
- `README.md:22` records the absence of planning and answer-generation implementation.

### Unknowns

- Minimum claim segmentation and independently verifiable claim granularity remain open at `docs/product/open-questions.md:19`.
- No typed grounded-answer schema or binding validator exists.

## 14. Which stable evidence and source-revision identities are available from retrieval inputs for later claim support, citation resolution, and attribution?

### Findings

- Source snapshot identity includes wiki database, dated dump run, exact dump filename and source URL, retrieval timestamp, and extraction profile.
- `article_artifact_id` is SHA-256-derived from dump run, page ID, revision ID, extractor identity, and extractor configuration.
- `passage_id` is SHA-256-derived from article artifact ID, heading path, and paragraph ordinal. The passage also carries its article ID, full heading path, ordinal, and normalized text.
- Retained article artifacts carry canonical title, page ID, revision ID, parent revision ID, revision timestamp, permanent revision URL, history URL, source snapshot, and extractor identity/configuration.
- The release adds release ID, admitted lore passage IDs, article digests, corpus fingerprint, rubric ID, curation snapshot digest, and the shared source snapshot. This creates a stable chain from release and passage through artifact and exact Wikipedia revision.
- Product intent exposes approved text plus stable evidence identity to retrieval callers while withholding internal paths, raw wikitext, curation history, and license presentation. Trusted application code later resolves bindings, links, and notices.
- No runtime retrieval-result schema exists, so the exact subset delivered to the agent is not implemented.

### Evidence

- `src/middle_earth_travel_agency/corpus_acquisition.py:88` defines `SourceSnapshot`, and `src/middle_earth_travel_agency/corpus_acquisition.py:98` defines its pinned initial values.
- `src/middle_earth_travel_agency/corpus_acquisition.py:492` defines hashed identity; `src/middle_earth_travel_agency/corpus_acquisition.py:503` constructs article identity inputs; `src/middle_earth_travel_agency/corpus_acquisition.py:530` constructs passage identity inputs.
- `src/middle_earth_travel_agency/corpus_acquisition.py:542` emits article and revision identity; `src/middle_earth_travel_agency/corpus_acquisition.py:554` emits permanent revision URL; `src/middle_earth_travel_agency/corpus_acquisition.py:557` emits history URL; `src/middle_earth_travel_agency/corpus_acquisition.py:559` emits extractor identity/configuration.
- `src/middle_earth_travel_agency/corpus_release.py:131` captures artifact digests; `src/middle_earth_travel_agency/corpus_release.py:141` emits lore-bearing article/revision identity; `src/middle_earth_travel_agency/corpus_release.py:160` emits release, curation, and source identities.
- `docs/product/capabilities/corpus-retrieval.md:34` limits retrieved content and `docs/product/capabilities/corpus-retrieval.md:36` defines evidence identity versus withheld data.
- `docs/product/capabilities/evidence-and-attribution.md:30` requires resolution to exact revision, and `docs/product/capabilities/evidence-and-attribution.md:51` assigns presentation resolution to trusted application code.

### Unknowns

- The runtime retrieval-result schema and claim-binding schema are absent.
- Contributor and license data are not stored in the release manifest; attribution resolution is not implemented.

## 15. Which current CLI and release tests establish reusable expectations for parsing, delegation, deterministic output, validation failures, and immutable input handling?

### Findings

- CLI snapshot tests establish parsing of source/output paths, exact delegation order, success status, and count reporting.
- CLI release tests establish separate create/validate syntax, string-to-`Path` conversion, exact keyword delegation, success status, and stable human-readable summaries.
- Release tests establish byte-identical manifests for identical inputs; exact retention of curation and article bytes; manifest selection of only lore-bearing articles and lore passage IDs; and validation against the manifest-recorded inventory rather than unrelated later additions.
- Failure tests establish rejection of deferred/undecided curation, existing output, tampered manifest counts, tampered retained article bytes, invalid release IDs, and mixed source snapshots.
- Concurrent publication tests establish that exactly one creator publishes a complete release directory and that no partial sibling publication remains.

### Evidence

- `tests/test_cli.py:270` tests curation snapshot parsing, delegation, and reporting.
- `tests/test_cli.py:314` tests create/validate release parsing, delegation, and reporting.
- `tests/test_cli.py:392` tests console conversion of expected operator failures to stderr and exit 1.
- `tests/test_corpus_release.py:65` tests deterministic output, exact retained inputs, lore-only selection, and validation independent of unrelated additions.
- `tests/test_corpus_release.py:157` tests incomplete curation rejection.
- `tests/test_corpus_release.py:181` tests overwrite refusal and manifest tamper rejection.
- `tests/test_corpus_release.py:216` tests retained-article digest tamper rejection.
- `tests/test_corpus_release.py:246` tests one-winner atomic concurrent publication.
- `tests/test_corpus_release.py:289` tests release-ID and mixed-source rejection.

### Unknowns

- These tests define corpus CLI and release behavior only. They establish no parsing, delegation, serialization, or error contract for retrieval or agent commands.

## 16. Which retrieval, agent-orchestration, grounded-answer, and unsupported-question behaviors currently have no executable tests?

### Findings

- There are no executable retrieval tests for indexing, lexical matching/ranking, tokenizer and weights, numeric result bounds, deterministic tie breaking, active-release pinning, compatibility/readiness failure, immediate-context boundaries, or retrieval-disabled non-bypass behavior.
- There are no agent-orchestration tests for model invocation, tool allowlisting, search/context sequencing, typed output, streaming, cancellation, or tool failure.
- There are no grounded-answer tests for claim-to-passage bindings, release-bound support, conflict/uncertainty handling, conservative inference labeling, or claim-specific citation eligibility.
- There are no unsupported-question tests proving that empty or insufficient evidence causes qualification, omission, assumption request, or abstention instead of completion from pretrained model knowledge.
- Evaluation requirements for identical live/evaluation policy, matched settings, disabled isolation, randomized concealment, invalid pairs, and human verdicts are documentary only. No executable evaluation case schema or suite exists.

### Evidence

- `README.md:17` enumerates the implemented slice and `README.md:22` lists retrieval, planning, generation, evaluation, and web experience as unimplemented.
- `tests/test_cli.py:314` is the furthest current CLI test surface; it covers release commands, not retrieval or answers.
- `docs/product/capabilities/corpus-retrieval.md:28` defines unimplemented retrieval invariants, including scope, boundaries, failure, concurrency, and disabled behavior.
- `docs/product/capabilities/travel-planning.md:33` defines unimplemented grounding, uncertainty, tool, output, cancellation, and policy invariants.
- `docs/product/capabilities/evaluation.md:34` defines unimplemented evaluation invariants.
- `docs/product/open-questions.md:9` leaves evaluation success thresholds unresolved.

### Unknowns

- Executable case inputs, fixtures, expected result schemas, evaluation storage, and quantitative or qualitative thresholds are not defined.
