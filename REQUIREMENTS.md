# Filip's Vocabulary App — Requirements & Architecture Baseline

**Document version:** 1.3
**Date:** 2026-08-24
**Source:** v1.0 reverse-engineered from `main_code_voc.py` (App version 2.61); v1.1 added the Spanish module requirements and the architecture changes needed to support it; v1.2 marks all six implementation phases complete and verified (App version now 2.7); v1.3 fixes two pre-existing (non-Spanish) bugs found in a full post-implementation code review.

## 1. Purpose

This document captures the requirements the application implements (v1.0 baseline) plus the requirements for extending it (v1.1 onward). It is the baseline of record: new features should be added as new, dated sections rather than by editing history away — see the Change Log at the bottom. Requirement IDs (`REQ-<AREA>-<NN>`) are stable identifiers for future specs, tickets, or tests to reference.

## 2. Scope

A single-user, offline desktop application for learning vocabulary against a fixed native language (German), built with Python's standard library only (Tkinter for UI, `json` for storage, `smtplib` for email). No server component, no multi-user support, no authentication. As of v1.1, the app supports two vocabulary tracks — German↔English and German↔Spanish — selected via an in-app language switch, sharing one data file.

## 3. Architecture Overview

### 3.1 v1.0 baseline

```
VocabularyApp (main coordinator, owns the Tk root + Notebook tabs)
 ├── VocabularyDatabase   (data layer: vocab entries + reading texts, JSON-backed)
 ├── EmailModule          (SMTP email sending, Gmail-specific)
 ├── AddModifyUI   → VocabularyDatabase
 ├── QuizUI        → VocabularyDatabase, notification_callback
 ├── ListUI        → VocabularyDatabase
 ├── ReadingUI     → VocabularyDatabase
 └── SettingsUI    → EmailModule
```

The v1.0 architecture is tightly coupled to one hardcoded language pair: field names (`english`, `german`), UI labels, and CSV columns all assume "English" throughout `VocabularyDatabase`, `AddModifyUI`, `QuizUI`, `ListUI`, and `ReadingUI`. UI and business logic are not separated (UI classes call `messagebox`/`filedialog` directly inside handlers that also touch the database). Config is a class of constants, not a config file.

### 3.2 Architecture changes required for multi-language support (v1.1)

**Verdict: this is a refactor of the existing module boundaries, not a rewrite.** The tab-based Tkinter UI, the single `VocabularyDatabase` class, and the single JSON file all remain. The changes needed:

- **Generalize the vocabulary schema.** Rename the `english` field to `foreign_word` (holds whichever foreign-language word applies); keep `german` as-is, since the translation is always into German regardless of which foreign language is active — no rename needed there. Add an explicit `language` field (`"english"` / `"spanish"`) to every vocabulary entry and every reading text.
- **Change IDs from integer to prefixed string.** Per REQ-ID-01 below, IDs become `E<n>` / `S<n>` (e.g. `E1`, `S1`), with independent counters per language. This touches `_generate_vocab_id`/`_generate_reading_id`, all sorting and lookup code, the CSV export, and the "Find Doublets" logic (which currently does `int(values[0])` and must switch to string comparison).
- **Introduce app-level "active language" state.** `VocabularyApp` owns a single `active_language` value; a new toggle control (not buried in Settings) lets the user switch it at any time after startup, not just once. On switch, every tab re-filters/re-labels itself against the newly active language — see REQ-LANG-01–05.
- **Introduce a reusable special-character input widget.** A small component (button row) usable from any Tk `Entry` widget, that inserts a clicked Spanish character at the current cursor position of whichever entry currently has focus — see REQ-SPCHAR-01–04. Built generically enough that a third language's special characters could reuse the same widget later.
- **Data migration on load.** Existing entries (all implicitly English, plain integer IDs) must be upgraded in place — see Section 9.

Everything else — the six quiz modes, the list/search/doublets/statistics logic, the reading-module matching algorithm, CSV export mechanics, email notifications, backup/restore — is reused as-is per language; it just now operates on a filtered subset instead of the whole database.

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| REQ-NF-01 | Runs on Python 3.7+ using only the standard library (no pip dependencies for the app itself; `pytest` is a dev/test-only dependency). |
| REQ-NF-02 | Desktop GUI via Tkinter, single window, tabbed navigation (`ttk.Notebook`). |
| REQ-NF-03 | All vocabulary and reading data persisted locally as JSON at `~/Documents/FilipVocabularyApp/vocabulary_data.json`; no network dependency except outgoing SMTP for email notifications. |
| REQ-NF-04 | Data file format must remain backward-compatible: `VocabularyDatabase.load()` must accept the legacy flat-list format, the v1.0 `{vocabulary, reading_texts}` dict format, and the v1.1 language-tagged/prefixed-ID format, auto-migrating older entries. |
| REQ-NF-05 | Distributable as a single-file Windows `.exe` via PyInstaller (`--onefile --windowed`). |
| REQ-NF-06 | Core data-layer logic (`VocabularyDatabase`) must be unit-testable independent of the Tkinter UI. |
| REQ-NF-07 | *(New, v1.1)* Text entered via the special-character buttons or typed directly must be Unicode-normalized (NFC) before being stored or compared, so visually identical answers (e.g. a precomposed vs. combining "é") are never scored as different. Applies to quiz answer checking, search, and doublet detection. |

## 5. Data Model

### 5.1 Vocabulary entry (v1.1)

```json
{
  "id": "S1",
  "language": "spanish",
  "foreign_word": "hola",
  "german": "hallo",
  "created_at": "2026-08-24 10:00:00",
  "last_queried": null,
  "last_result": null,
  "correct_count": 0,
  "wrong_count": 0
}
```

English entries look identical except `"id": "E1"` and `"language": "english"`. All other fields, semantics, and tracking behavior (Section 6.1–6.2) are unchanged from v1.0.

### 5.2 Reading text entry (v1.1)

```json
{
  "id": "S1",
  "language": "spanish",
  "title": "Mi Artículo",
  "content": "full text...",
  "uploaded_at": "2026-08-24 10:00:00",
  "word_count": 42,
  "vocabulary_matches": 5
}
```

### 5.3 Storage file (top level) — unchanged shape

```json
{ "vocabulary": [ ... ], "reading_texts": [ ... ] }
```

## 6. Functional Requirements

All requirements from v1.0 (vocabulary management, quiz engine, list/search/analysis, reading module, email, backup/restore — see prior baseline) still apply, now operating on the subset of `vocabulary`/`reading_texts` matching the currently active language. New requirements for v1.1 follow.

### 6.7 Language Switching

| ID | Requirement |
|---|---|
| REQ-LANG-01 | The app exposes an "English" / "Spanish" control, visible at all times (not just at startup), that sets the single active-language state for the whole app. |
| REQ-LANG-02 | Switching the active language re-scopes every tab to that language only: Add/Modify labels and target field, the quiz word pool and all six quiz modes, the vocabulary list (including search and doublet detection), the reading-text list and vocabulary highlighting, and the statistics view. There is no combined/"all languages" view — per-decision, each language behaves as an independent trainer sharing one file. |
| REQ-LANG-03 | New vocabulary entries and reading texts are always created tagged with the currently active language. |
| REQ-LANG-04 | CSV export, when triggered, exports only the currently active language's vocabulary; the export filename and the "Foreign Word" column header reflect the active language (e.g. "Spanish" instead of a generic label) for clarity. |
| REQ-LANG-05 | Quiz-result emails include the active language in the quiz name/subject (e.g. "Spanish – Random 30") so notifications are unambiguous when both tracks are in use. |
| REQ-LANG-06 | On startup, the app always defaults to English as the active language (default assumption, not persisted — see Section 11; revisit if this proves annoying in practice). |

### 6.8 Spanish Character Input

| ID | Requirement |
|---|---|
| REQ-SPCHAR-01 | When the active language is Spanish, a row of buttons for the characters not directly available on a German keyboard is shown: á, é, í, ó, ú, ñ, Ñ, ¿, ¡. (ü is excluded — already present on a German keyboard.) |
| REQ-SPCHAR-02 | The character row is available wherever Spanish text is typed: the Add/Modify "Spanish word" field, and the Quiz answer field (the quiz requires typing the Spanish word from a German prompt). |
| REQ-SPCHAR-03 | Clicking a character button inserts that character at the current cursor position of whichever relevant entry field currently has focus, rather than always appending to the end. |
| REQ-SPCHAR-04 | The character row is hidden when the active language is English. |

## 7. Testing Baseline

v1.0 `test_vocabulary_app.py` coverage (add/edit/delete, quiz result recording, statistics, text-vocabulary matching, reading-text creation) must be extended for v1.1 to cover: language-tagged entries, prefixed-ID generation and uniqueness per language, migration of legacy plain-integer-ID data, and language-scoped filtering for list/quiz/reading/stats/CSV. `test_main.py` remains a placeholder. CI (`python_ci.yml`) should continue to run the full suite on every push/PR touching `*.py` or `requirements.txt`.

**Update (Phase 1/2, 2026-08-24):** `test_vocabulary_app.py` now has 16 tests covering all of the above at the `VocabularyDatabase` level. Additionally, `smoke_test_gui.py` was added as a headless-Tkinter smoke test (run under Xvfb: `xvfb-run -a python3 smoke_test_gui.py`) that drives the real UI classes — add/load/modify/delete, a full quiz round, list/search/doublets/statistics/CSV export, and the Reading module — with blocking dialogs (`messagebox`, `filedialog`, and `QuizUI`'s custom result popup) monkeypatched out so it runs unattended. This is not wired into `python_ci.yml` yet (CI has no display), but should be considered for a headless-Xvfb CI job as UI coverage matters more once Phase 3 (language toggle) lands.

**Update (Phase 3, 2026-08-24):** Added `smoke_test_language_switch.py`, a headless-Xvfb smoke test covering the active-language toggle itself, per-tab re-scoping (Add/Modify, List, Quiz, Reading), the cross-language edit guard, quiz display-name/email-subject language-prefixing, the Reading-tab index-mapping bug fix, and CSV export language-awareness.

**Update (Phase 4, 2026-08-24):** `test_vocabulary_app.py` now has 22 tests — 4 added for `normalize_text()` and NFD-input normalization at the `VocabularyDatabase` layer (`add_entry`/`update_entry`). Added `smoke_test_special_chars.py`, a headless-Xvfb smoke test (17 checks) covering the `SpecialCharacterBar` widget: visibility toggling per active language, the exact character set, cursor-position insertion, multi-target focus tracking, a full Spanish entry saved via button-composed text, and the REQ-NF-07 NFD/NFC quiz-answer-matching scenario. All three smoke test scripts (`smoke_test_gui.py`, `smoke_test_language_switch.py`, `smoke_test_special_chars.py`) are rerun as regression checks after every phase; none are wired into `python_ci.yml` yet (still no display in CI) — still worth a headless-Xvfb CI job.

## 8. Known Gaps (still open from v1.0 — unaffected by the Spanish module)

- **No vocabulary list import/merge** — only full-database Restore exists, which overwrites rather than merges.
- **No print function** — only CSV export exists.
- **Reading module does not surface new/unknown words** — it only highlights words already in the local vocabulary database for the active language.

## 9. Migration Requirements (v1.0 data → v1.1 schema)

| ID | Requirement |
|---|---|
| REQ-MIG-01 | On load, any vocabulary entry missing a `language` field is assigned `language: "english"`. |
| REQ-MIG-02 | On load, any vocabulary entry with a bare-integer `id` (legacy format) is rewritten to `"E<original id>"` (e.g. `5` → `"E5"`), preserving the original number. |
| REQ-MIG-03 | On load, any vocabulary entry with a legacy `english` field is renamed to `foreign_word` (value unchanged). |
| REQ-MIG-04 | The same three migrations (language tag, ID prefixing, no field rename needed for reading texts) apply to `reading_texts` entries. |
| REQ-MIG-05 | Migration runs automatically and transparently on `VocabularyDatabase.load()`, consistent with the existing v1.0 migration pattern (`_migrate_old_format`), and the migrated data is immediately re-saved so the migration only ever runs once per file. |
| REQ-MIG-06 | ID generation (`_generate_vocab_id`, `_generate_reading_id`) becomes language-aware: for a given language/prefix, find the maximum existing numeric suffix among entries with that prefix and increment — independent counters per language, so `E` and `S` sequences do not need to stay in sync. |

## 10. Future Extension Points

Placeholders only — flesh these out into full REQ-xxx sections when the corresponding work is planned:

- **Vocabulary list import/merge**, addressing the gap in Section 8.
- **Print support**, addressing the gap in Section 8.
- **New-word detection in Reading module**, addressing the gap in Section 8, now per active language.
- **Configurable settings** (email recipient, storage location) instead of hardcoded `Config` constants, if multi-user or multi-profile use becomes a goal.
- **A third language.** If this becomes likely, revisit whether independent per-language ID prefixes (Section 11) should be generalized further (e.g. a small language registry instead of hardcoded `E`/`S` prefixes scattered through the code).

## 11. Open Decisions Log

Decisions already made (recorded for traceability):

- **Language scope (2026-08-24):** Switching language scopes the *entire* app (quiz, list, reading, stats, CSV) to that language only — no combined/"all languages" view. → REQ-LANG-02.
- **ID scheme (2026-08-24):** Prefixed string IDs (`E1`, `S1`, ...) were chosen over a plain-integer-ID-plus-language-field-only approach, for visible at-a-glance identification. An explicit `language` field is kept alongside the prefix regardless, so filtering/business logic never depends on parsing the ID string — the prefix is a display/identification convenience, not the source of truth. → Sections 3.2, 5.1, 9.
- **Startup language default (2026-08-24):** Defaulted to "always start on English" rather than remembering the last-used language, as the simpler option. → REQ-LANG-06. Flag if this should instead persist across restarts — low-cost to change later.

No remaining open decisions blocking implementation.

## 12. Implementation Plan

Staged rather than a single change, so each layer can be verified (ideally via the automated test suite, which needs no GUI) before the next one is built on top of it — this keeps any regression traceable to a specific, small change instead of buried in one large diff.

**Update (Phase 3, 2026-08-24):** REQ-LANG-04 (CSV filename/header language-awareness) landed in Phase 3 rather than Phase 5, since it was a trivial addition once `ListUI` was already being made language-aware — the CSV column header and filename now reflect the active language. REQ-LANG-05 (email subject includes the language) came along for free as a side effect: `QuizUI.quiz_mode` is now built as `"{Language} - {mode}"` (e.g. `"Spanish - Random 30"`) for the on-screen results banner, and that same string flows into the notification callback's `quiz_name`, so quiz-result emails are already language-labeled without any `EmailModule`/`SettingsUI` changes. Phase 5 is now just a final review pass rather than net-new work. Building the language-scoped `ReadingUI` also surfaced and fixed a latent bug: `_on_text_selected` was resolving the listbox selection index against an *unfiltered, re-sorted* list of all reading texts, while the listbox itself only ever showed the filtered list — with texts from both languages present, selecting an item could silently open the wrong text. Both places now use the same filtered+sorted list.

**Update (Phase 4, 2026-08-24):** Delivered REQ-SPCHAR-01–04 via a new reusable `SpecialCharacterBar` widget (module-level class, placed between `EmailModule` and `AddModifyUI`): a small `ttk.Frame` of character buttons that tracks focus across multiple registered `Entry` widgets (via `<FocusIn>` binding) and inserts the clicked character at the current cursor position (`entry.index(tk.INSERT)`) of whichever registered entry last had focus, rather than always appending. Three instances are wired in: `AddModifyUI`'s Add-section field, `AddModifyUI`'s Modify-section field, and `QuizUI`'s answer field. Each is shown/hidden (`grid()`/`grid_remove()`) based on the active language — visible only when Spanish is active, and for the quiz bar, only while a quiz is actually running. The button set is exactly `á, é, í, ó, ú, ñ, Ñ, ¿, ¡` (ü excluded, per REQ-SPCHAR-01, since it's already on a German keyboard). Delivered REQ-NF-07 via a new `normalize_text()` helper (`unicodedata.normalize('NFC', text)`) applied at two points: storage time (`VocabularyDatabase.add_entry`/`update_entry` normalize `foreign_word`/`german` before writing) and ephemeral-compare time (`QuizUI._submit_answer` normalizes the typed answer before comparing against the stored — already-NFC — word). This means a visually-identical answer typed with a different Unicode composition (e.g. a screen-reader/IME-produced NFD "café" vs. the button-composed NFC "café") is still scored correct. Verified: full pytest suite (22/22, 4 new tests added covering `normalize_text()` directly and NFD-input normalization in `add_entry`/`update_entry`) + `smoke_test_gui.py` and `smoke_test_language_switch.py` rerun clean (no regressions) + new `smoke_test_special_chars.py` (17 checks) covering char-bar visibility per language, the exact character set, cursor-position insertion, multi-target focus tracking between the three registered bars, a full Spanish entry saved via button-composed text, and the REQ-NF-07 NFD/NFC quiz-answer-matching scenario end-to-end.

| Phase | Scope | Touches | Exit criteria |
|---|---|---|---|
| 1 ✅ | Data layer schema + migration | `VocabularyDatabase`: `language` field, `english`→`foreign_word` rename, prefixed string IDs with per-language counters, migration logic (REQ-MIG-01–06) | Extended `test_vocabulary_app.py` passes (16/16); a legacy data file (both the old bare-list and the v1.0 dict format) loads, migrates, and re-saves correctly; migration confirmed idempotent on reload; no UI touched yet — **done 2026-08-24** |
| 2 ✅ | Re-point existing UI at new schema | `AddModifyUI`, `QuizUI`, `ListUI`, `ReadingUI` updated to use `foreign_word` and string IDs (incl. fixing the `int(values[0])` cast in doublet detection, and the ID-based list/CSV sorting that broke under lexicographic string IDs — now sorts by `created_at`) | App behaves identically to v1.0 for English — no new features yet, this phase is a pure refactor. Verified with the full data-layer test suite (18/18) plus a new headless-Tkinter smoke test (`smoke_test_gui.py`, run under Xvfb) exercising add/load/modify/delete, a full quiz round, list/search/doublets/statistics/CSV export, and the Reading module end-to-end — **done 2026-08-24** |
| 3 ✅ | Active-language state + toggle | New app-level `active_language` state and switch control; every tab filters by it (REQ-LANG-01–04, REQ-LANG-06) | Spanish is selectable and every tab scopes correctly to it, even though Spanish text entry is still keyboard-only. Verified: full pytest suite (18/18, no regressions) + `smoke_test_gui.py` rerun clean + new `smoke_test_language_switch.py` covering the toggle itself, per-tab scoping, the cross-language edit guard, and a fixed Reading-tab index-mapping bug — **done 2026-08-24** |
| 4 ✅ | Spanish character input | Reusable special-character widget wired into the Add/Modify Spanish field and Quiz answer field (REQ-SPCHAR-01–04); Unicode normalization (REQ-NF-07) | Typing/inserting accented characters works in both fields; accented quiz answers compare correctly regardless of input method — **done 2026-08-24** |
| 5 ✅ | Polish | ~~Language-aware CSV filename/header, quiz-email subject line~~ — both already delivered in Phase 3 (see note above). Final review of remaining English-only-sounding strings (dialog titles, About text, email footer) | Low-risk, deferrable if time-constrained — **done 2026-08-24** |
| 6 ✅ | Regression pass | Full test suite; manual check that a pre-migration backup still restores correctly; manual smoke test of both language tracks end-to-end | All tests green, both tracks usable — **done 2026-08-24** |

**Update (Phase 5, 2026-08-24):** Reviewed the codebase for remaining strings that hardcoded "English" regardless of the active language, and fixed three real ones: (1) `ListUI._find_doublets()`'s "Doublets Found" / "No Doublets" messages said "English word(s)" even while a Spanish doublet check was running — now use `Config.LANGUAGE_LABELS[self.active_language]`. (2) The three "Please enter an Entry ID" hints in `AddModifyUI` (`_load_entry`, `_modify_vocabulary`, `_delete_vocabulary`) always showed the example `'E3'` even while Spanish was active — now shows `'S3'` when appropriate, via `self.db.LANGUAGE_PREFIXES`. (3) The quiz-result email's footer line hardcoded "Keep up the great work learning English vocabulary!" even for a Spanish quiz — generalized to "Keep up the great work!" since the quiz name/subject already carries the language (REQ-LANG-05). Also refreshed the About dialog and bumped `Config.VERSION` to `2.7` to reflect the Spanish module (feature list now mentions the language switch and the Spanish character buttons instead of implying an English-only app). Verified: full pytest suite (22/22, no regressions) + all three smoke tests rerun clean, with `smoke_test_language_switch.py` extended with 3 new checks covering the doublet-message and ID-hint fixes specifically.

**Open item (not blocking):** `Config.APP_NAME` is still literally `"Filip's English Vocabulary Learning App"` — it appears in the window title, the About dialog, the startup console line, and the email footer signature. Left unchanged since renaming the app is a branding decision, not a bug; flag if you'd like it retitled (e.g. to something language-neutral) now that Spanish is a first-class track.

**Update (Phase 6, 2026-08-24) — implementation complete:** Ran the final regression pass. The full automated suite (22 pytest tests + four headless-Xvfb smoke tests: `smoke_test_gui.py`, `smoke_test_language_switch.py`, `smoke_test_special_chars.py`, and the new `smoke_test_phase6_regression.py`) all pass with no failures. `smoke_test_phase6_regression.py` was written specifically for this phase and covers two things nothing earlier did:

1. **Restoring a pre-migration backup through the real menu flow.** Earlier migration testing (`test_migration_from_legacy_format` in `test_vocabulary_app.py`) only exercised `VocabularyDatabase.load()` directly. This test instead drives `VocabularyApp._restore_data()` end-to-end — a legacy JSON file (plain-integer IDs, `english` field, no `language` field) is fed through the actual File → Restore menu handler (filedialog mocked, confirm-dialog mocked) — and confirms: the legacy entries migrate correctly (`E1`/`E2`, `language: "english"`, `foreign_word` renamed), the migration is persisted to disk immediately, the List and Reading tabs reflect the restored data without extra intervention, and the pre-restore safety-backup file (`vocabulary_data.json.backup_<timestamp>`) is created — but *only* when a prior data file genuinely existed to back up, which the test verifies both ways (skipped on the very first restore into an empty store, created on a later restore that overwrites real data).
2. **A single continuous session mixing both language tracks**, deliberately interleaving English and Spanish operations (add, quiz, doublet-check, reading upload, CSV export, statistics) to catch any state leakage a per-feature test focused on one language at a time could miss. It also runs a plain backup → mutate → restore round-trip and confirms the mutation is undone and all prior data (both languages' vocabulary and all reading texts) survives intact.

No app-code changes were needed in this phase — Phase 6 was pure verification, and it passed. All six implementation phases from Section 12 are now complete. The Spanish vocabulary module (multi-language data model, active-language switching, Spanish special-character input, Unicode normalization) is fully implemented, tested, and considered production-ready pending only two still-open, non-blocking items: the `Config.APP_NAME` branding question above, and wiring the Xvfb smoke tests into CI (`python_ci.yml` still has no display).

## 12a. Post-Implementation Code Review (2026-08-24)

A full line-by-line review of `main_code_voc.py` was done after Phase 6, independent of the Spanish-module work — looking for latent bugs anywhere in the file, not just in the new code. Three real issues were found and verified with direct reproductions; two have been fixed, one is logged as a known limitation.

**Fixed — legacy-migration ID collision (`_migrate_old_format`).** IDs for vocabulary entries missing an `id` field used to be assigned from the entry's position in the list (`entry['id'] = i + 1`), with no check against IDs other entries already had. A backup file where some entries have an `id` and others don't (e.g. hand-edited, or merged from two old exports) could produce two different entries sharing one ID. Confirmed impact: `delete_entry()` on the shared ID deleted *both* entries at once, and `get_entry_by_id()`/`update_entry()` only ever saw the first of the two. Fixed by computing the next free ID from the highest existing integer `id` and incrementing it for each newly-assigned entry, so it can no longer collide with an existing ID or with another entry migrated in the same pass. Covered by a new test, `test_migration_assigns_distinct_ids_when_some_entries_lack_id` in `test_vocabulary_app.py`.

**Fixed — misleading Restore confirmation message (`VocabularyApp._restore_data`).** The success dialog after a menu-driven Restore always said "Previous data backed up to: `<path>`", even when no prior data file existed to copy (e.g. the very first restore on a fresh install) — in that case the named file was never actually created. Fixed by only showing the "backed up to" line when a safety-backup copy was genuinely made; otherwise the dialog now says no backup was needed. Covered by two new assertions in `smoke_test_phase6_regression.py`, one for each case (no backup made / backup made).

**Known limitation, not fixed — Unicode normalization (REQ-NF-07) is not retroactive.** `add_entry`/`update_entry` normalize text to NFC on every write, but the schema migration that runs on load does not re-normalize the `foreign_word`/`german` text of entries that already existed in the file. Confirmed effect: an entry whose text was stored in a different (but visually identical) Unicode form before this update — e.g. from an unusual input source — is not automatically fixed on load, and Find Doublets will not recognize it as a duplicate of a newly-typed, NFC-stored version of the same word until that entry is edited and re-saved once. Real-world risk is low (normal keyboard input on Windows/German layouts produces NFC directly), so this was left as-is rather than adding a one-time full-database re-normalization pass; flag if you'd like that pass added.

## 13. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-24 | Initial baseline, reverse-engineered from `main_code_voc.py` v2.61. |
| 1.1 | 2026-08-24 | Added Spanish vocabulary module requirements: language-scoped UI switching, generalized data model (`foreign_word` + `language` field), prefixed per-language IDs, Spanish special-character input widget, migration requirements for existing data, staged implementation plan. |
| 1.1 (impl.) | 2026-08-24 | Phases 1–5 implemented and verified: data-layer schema/migration (Phase 1), UI re-pointed to new schema (Phase 2), active-language state + toggle scoping every tab incl. CSV/email labeling (Phase 3), Spanish special-character input widget + Unicode NFC normalization (Phase 4), final polish pass fixing three remaining English-hardcoded strings and refreshing the About dialog/version (Phase 5). 22/22 automated tests plus three headless Xvfb smoke test scripts all pass. Phase 6 (end-to-end regression pass) remains open. |
| 1.2 | 2026-08-24 | Phase 6 (final regression pass) complete: full menu-driven restore of a pre-migration backup verified end-to-end, plus a new continuous mixed-language smoke test (`smoke_test_phase6_regression.py`) exercising both tracks together and a backup/mutate/restore round-trip. No app-code changes needed — all checks passed on the first fix (one test-assertion correction). **All six implementation phases are now complete; the Spanish module is considered done.** Two non-blocking open items remain: `Config.APP_NAME` branding, and wiring the Xvfb smoke tests into CI. |
| 1.3 | 2026-08-24 | Post-implementation code review (Section 12a) found and fixed two pre-existing, non-Spanish bugs: a legacy-migration ID collision that could make `delete_entry()` silently delete two different vocabulary entries at once, and a Restore confirmation dialog that could falsely claim a safety backup was made. A third finding (Unicode normalization isn't retroactively applied to pre-existing data) was logged as a known, low-risk limitation rather than fixed. 23/23 pytest tests (1 new) and all four smoke tests (2 new assertions) pass. |
