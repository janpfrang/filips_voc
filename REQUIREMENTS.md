# Filip's Vocabulary App — Requirements & Architecture Baseline

**Document version:** 1.1
**Date:** 2026-08-24
**Source:** v1.0 reverse-engineered from `main_code_voc.py` (App version 2.61); v1.1 adds the Spanish module requirements and the architecture changes needed to support it. Not yet implemented — this document is the spec to build against.

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

| Phase | Scope | Touches | Exit criteria |
|---|---|---|---|
| 1 | Data layer schema + migration | `VocabularyDatabase`: `language` field, `english`→`foreign_word` rename, prefixed string IDs with per-language counters, migration logic (REQ-MIG-01–06) | Extended `test_vocabulary_app.py` passes; a legacy data file loads, migrates, and re-saves correctly; no UI touched yet |
| 2 | Re-point existing UI at new schema | `AddModifyUI`, `QuizUI`, `ListUI`, `ReadingUI` updated to use `foreign_word` and string IDs (incl. fixing the `int(values[0])` cast in doublet detection) | App behaves identically to v1.0 for English — no new features yet, this phase is a pure refactor |
| 3 | Active-language state + toggle | New app-level `active_language` state and switch control; every tab filters by it (REQ-LANG-01–04, REQ-LANG-06) | Spanish is selectable and every tab scopes correctly to it, even though Spanish text entry is still keyboard-only |
| 4 | Spanish character input | Reusable special-character widget wired into the Add/Modify Spanish field and Quiz answer field (REQ-SPCHAR-01–04); Unicode normalization (REQ-NF-07) | Typing/inserting accented characters works in both fields; accented quiz answers compare correctly regardless of input method |
| 5 | Polish | Language-aware CSV filename/header, quiz-email subject line (REQ-LANG-04, REQ-LANG-05) | Low-risk, deferrable if time-constrained |
| 6 | Regression pass | Full test suite; manual check that a pre-migration backup still restores correctly; manual smoke test of both language tracks end-to-end | All tests green, both tracks usable |

## 13. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-24 | Initial baseline, reverse-engineered from `main_code_voc.py` v2.61. |
| 1.1 | 2026-08-24 | Added Spanish vocabulary module requirements: language-scoped UI switching, generalized data model (`foreign_word` + `language` field), prefixed per-language IDs, Spanish special-character input widget, migration requirements for existing data, staged implementation plan. Not yet implemented. |
