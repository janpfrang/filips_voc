"""
Phase 6: final end-to-end regression pass.

Not part of the pytest suite -- exercises the real app end-to-end under Xvfb.
Two things this specifically covers that no earlier smoke test does:

  1. Restoring a PRE-MIGRATION backup (legacy plain-integer-ID, no 'language'
     field, 'english' instead of 'foreign_word') through the actual app menu
     flow (File > Restore), not just VocabularyDatabase.load() directly --
     i.e. the full filedialog -> confirm -> shutil.copy -> db.load() ->
     UI-refresh path a real user would hit.
  2. A single continuous session that interleaves BOTH language tracks
     (add / quiz / search / doublets / reading / CSV / backup / restore)
     to catch any cross-language leakage that per-feature smoke tests,
     each usually focused on one language at a time, could miss.
"""
import os
import csv as csv_module
import json
import shutil
import tempfile

import tkinter as tk
from tkinter import messagebox, filedialog

import main_code_voc as m

# --- neutralize blocking modal dialogs -------------------------------------
info_calls = []
warn_calls = []
error_calls = []
yesno_answer = {'value': True}

messagebox.showinfo = lambda title, msg: info_calls.append((title, msg))
messagebox.showwarning = lambda title, msg: warn_calls.append((title, msg))
messagebox.showerror = lambda title, msg: error_calls.append((title, msg))
messagebox.askyesno = lambda title, msg: yesno_answer['value']
m.QuizUI._show_large_message = lambda self, title, message, color: None

save_path_holder = {}
open_path_holder = {'path': None}


def fake_asksaveasfilename(**kwargs):
    path = os.path.join(tempfile.mkdtemp(), kwargs.get('initialfile', 'export.json'))
    save_path_holder['path'] = path
    return path


def fake_askopenfilename(**kwargs):
    return open_path_holder['path']


filedialog.asksaveasfilename = fake_asksaveasfilename
filedialog.askopenfilename = fake_askopenfilename

# --- isolated storage location ----------------------------------------------
tmpdir = tempfile.mkdtemp()
m.Config.STORAGE_FILE = os.path.join(tmpdir, 'vocabulary_data.json')

root = tk.Tk()
app = m.VocabularyApp(root)

failures = []


def check(condition, description):
    status = "OK " if condition else "FAIL"
    print(f"[{status}] {description}")
    if not condition:
        failures.append(description)


add_ui = app.add_modify_ui
list_ui = app.list_ui
quiz_ui = app.quiz_ui
reading_ui = app.reading_ui


def add_word(foreign, german):
    add_ui.english_entry.delete(0, tk.END)
    add_ui.german_entry.delete(0, tk.END)
    add_ui.english_entry.insert(0, foreign)
    add_ui.german_entry.insert(0, german)
    add_ui._add_vocabulary()


# ============================================================================
# PART 1: restore a PRE-MIGRATION legacy backup through the real menu flow
# ============================================================================
legacy_data = {
    "vocabulary": [
        {
            "id": 1,
            "english": "hello",
            "german": "hallo",
            "created_at": "2020-01-01 10:00:00",
            "last_queried": None,
            "last_result": None,
            "correct_count": 0,
            "wrong_count": 0
        },
        {
            "id": 2,
            "english": "cat",
            "german": "Katze",
            "created_at": "2020-01-02 10:00:00",
            "last_queried": None,
            "last_result": None,
            "correct_count": 3,
            "wrong_count": 1
        }
    ],
    "reading_texts": [
        {
            "id": 1,
            "title": "Legacy Text",
            "content": "hello there, a cat sat here",
            "uploaded_at": "2020-01-01 10:00:00",
            "word_count": 6,
            "vocabulary_matches": 2
        }
    ]
}
legacy_path = os.path.join(tmpdir, 'legacy_backup.json')
with open(legacy_path, 'w', encoding='utf-8') as f:
    json.dump(legacy_data, f)

open_path_holder['path'] = legacy_path
yesno_answer['value'] = True
info_calls.clear()
error_calls.clear()
app._restore_data()

check(len(error_calls) == 0, f"restoring a legacy backup through the menu flow raised no error (got {error_calls})")
check(len(info_calls) == 1 and 'restored' in info_calls[-1][1].lower(), "restore success dialog shown")

restored_entries = app.db.get_all_entries()
check(len(restored_entries) == 2, f"both legacy entries present after restore (got {len(restored_entries)})")
check(all(e['id'] in ('E1', 'E2') for e in restored_entries), f"legacy integer IDs migrated to E-prefixed on restore (got {[e['id'] for e in restored_entries]})")
check(all(e['language'] == 'english' for e in restored_entries), "legacy entries defaulted to English on restore")
check(all('english' not in e for e in restored_entries), "legacy 'english' field renamed to 'foreign_word' on restore")
check(all(e['foreign_word'] in ('hello', 'cat') for e in restored_entries), "restored entries carry the original words")

# migration must have been persisted back to STORAGE_FILE, not just in memory
with open(m.Config.STORAGE_FILE, 'r', encoding='utf-8') as f:
    on_disk = json.load(f)
check(on_disk['vocabulary'][0]['id'] == 'E1' and 'language' in on_disk['vocabulary'][0],
      "migrated data was persisted to disk immediately, not just held in memory")

# No STORAGE_FILE existed yet at app startup ("No existing data file found"),
# so _restore_data()'s own `if os.path.exists(...)` guard correctly skips
# making a safety-backup copy here -- there was nothing to back up. The
# safety-backup path itself is exercised (and checked) in Part 3 below,
# once STORAGE_FILE genuinely has prior content at restore time.
safety_backups_after_first_restore = [fn for fn in os.listdir(tmpdir) if fn.startswith('vocabulary_data.json.backup_')]
check(len(safety_backups_after_first_restore) == 0,
      f"no safety backup made on the very first restore, since no prior data file existed (got {safety_backups_after_first_restore})")

# UI must reflect the restored+migrated data without a manual refresh
list_ui._refresh_list()  # active language is English by default, matches restored data
rows_after_restore = [list_ui.tree.item(i, 'values') for i in list_ui.tree.get_children()]
check(len(rows_after_restore) == 2, f"List tab shows the restored entries after app._restore_data() (got {len(rows_after_restore)})")

reading_ui._refresh_text_list()
items_after_restore = reading_ui.text_listbox.get(0, tk.END)
check(len(items_after_restore) == 1 and 'Legacy Text' in items_after_restore[0],
      f"Reading tab shows the restored legacy text (got {items_after_restore})")

# ============================================================================
# PART 2: continuous mixed-language end-to-end session
# ============================================================================
# We keep the two migrated English entries from Part 1 and build on top of
# them, deliberately interleaving Spanish work to look for cross-language
# leakage anywhere in the app.

# --- add more English entries ---
for foreign, german in [("dog", "Hund"), ("house", "Haus")]:
    add_word(foreign, german)
check(len(app.db.get_all_entries(language='english')) == 4, "English track now has 4 entries (2 restored + 2 new)")

# --- switch to Spanish, add entries incl. one via the char bar ---
app._set_active_language('spanish')
for foreign, german in [("perro", "Hund"), ("casa", "Haus")]:
    add_word(foreign, german)

add_ui.english_entry.delete(0, tk.END)
add_ui.german_entry.delete(0, tk.END)
add_ui.english_entry.insert(0, "nio")
add_ui.english_entry.icursor(0)
add_ui.english_entry.focus_set()
root.update()
add_ui.add_char_bar._insert_character('ñ')
check(add_ui.english_entry.get() == "ñnio", f"Spanish char bar still composes correctly mid-Phase-6 session (got {add_ui.english_entry.get()!r})")
add_ui.german_entry.insert(0, "Kind")
add_ui._add_vocabulary()

spanish_entries = app.db.get_all_entries(language='spanish')
check(len(spanish_entries) == 3, f"Spanish track has 3 entries (got {len(spanish_entries)})")
check({e['id'] for e in spanish_entries} == {'S1', 'S2', 'S3'}, f"Spanish IDs independent of English's E-counter (got {[e['id'] for e in spanish_entries]})")
check(app.db.get_all_entries(language='english')[0]['id'] == 'E1', "English E-counter untouched by Spanish adds in this session")

# --- quiz both tracks, verify no cross-contamination in results ---
quiz_ui._start_quiz("Last 10")
check(len(quiz_ui.quiz_entries) == 3 and all(e['language'] == 'spanish' for e in quiz_ui.quiz_entries),
      "Spanish quiz pool contains only Spanish entries")
for i, entry in enumerate(quiz_ui.quiz_entries):
    quiz_ui.answer_entry.delete(0, tk.END)
    quiz_ui.answer_entry.insert(0, entry['foreign_word'])
    quiz_ui._submit_answer()
check(quiz_ui.quiz_results == [True, True, True], "all 3 Spanish quiz answers scored correctly in the mixed session")

app._set_active_language('english')
quiz_ui._start_quiz("Last 10")
check(len(quiz_ui.quiz_entries) == 4 and all(e['language'] == 'english' for e in quiz_ui.quiz_entries),
      "English quiz pool (post-switch) contains only English entries -- no Spanish leakage")
quiz_ui.answer_entry.delete(0, tk.END)
quiz_ui.answer_entry.insert(0, "WRONG_ANSWER_XYZ")
quiz_ui._submit_answer()
check(quiz_ui.quiz_results[-1] is False, "a deliberately wrong English answer is still scored wrong (sanity check)")

# --- doublets: add an English duplicate, confirm Spanish list is unaffected ---
add_word("dog", "Hund (dup)")
warn_calls.clear()
list_ui._find_doublets()
check(len(warn_calls) == 1 and 'English' in warn_calls[-1][1], f"English doublet detected correctly (got {warn_calls})")
dup_id = [e['id'] for e in app.db.get_all_entries(language='english') if e['foreign_word'] == 'dog'][-1]
app.db.delete_entry(dup_id)  # undo

app._set_active_language('spanish')
info_calls.clear()
list_ui._find_doublets()
check(len(info_calls) == 1 and 'No duplicate Spanish' in info_calls[-1][1],
      f"Spanish track still doublet-free after the English-side duplicate/undo (got {info_calls})")

# --- reading module: one text per language, matches stay language-scoped ---
app.db.add_reading_text("Un Texto", "El perro y la casa", language='spanish')
app._set_active_language('english')
app.db.add_reading_text("A Text", "the dog and the house and the Legacy Text mention", language='english')

reading_ui.set_active_language('english')
english_texts = app.db.get_all_reading_texts(language='english')
check(len(english_texts) == 2, f"English reading texts: restored legacy one + new one (got {len(english_texts)})")

reading_ui.set_active_language('spanish')
spanish_texts = app.db.get_all_reading_texts(language='spanish')
check(len(spanish_texts) == 1 and spanish_texts[0]['title'] == 'Un Texto', f"Spanish reading texts scoped correctly (got {spanish_texts})")

# --- CSV export both tracks, confirm no cross-language rows in either file ---
app._set_active_language('spanish')
list_ui._export_to_csv()
with open(save_path_holder['path'], newline='', encoding='utf-8') as f:
    spanish_csv_rows = list(csv_module.DictReader(f, delimiter=';'))
check(len(spanish_csv_rows) == 3, f"Spanish CSV export has exactly the 3 Spanish entries (got {len(spanish_csv_rows)})")

app._set_active_language('english')
list_ui._export_to_csv()
with open(save_path_holder['path'], newline='', encoding='utf-8') as f:
    english_csv_rows = list(csv_module.DictReader(f, delimiter=';'))
check(len(english_csv_rows) == 4, f"English CSV export has exactly the 4 English entries (got {len(english_csv_rows)})")

# --- statistics stay scoped per language even after all this cross-traffic ---
stats_en = app.db.get_statistics(language='english')
stats_es = app.db.get_statistics(language='spanish')
stats_all = app.db.get_statistics()
check(stats_en['total_entries'] == 4, f"English statistics scoped correctly (got {stats_en['total_entries']})")
check(stats_es['total_entries'] == 3, f"Spanish statistics scoped correctly (got {stats_es['total_entries']})")
check(stats_all['total_entries'] == 7, f"combined statistics count both tracks (got {stats_all['total_entries']})")

# ============================================================================
# PART 3: a fresh (non-legacy) backup/restore round-trip preserves everything
# ============================================================================
backup_path = os.path.join(tmpdir, 'full_backup.json')
shutil.copy(m.Config.STORAGE_FILE, backup_path)

# mutate the live data after the backup was taken
add_word("temporary", "temporaer")  # (English active)
check(len(app.db.get_all_entries(language='english')) == 5, "sanity: post-backup addition present before restore")

open_path_holder['path'] = backup_path
yesno_answer['value'] = True
info_calls.clear()
app._restore_data()

check(len(app.db.get_all_entries(language='english')) == 4, "restoring the pre-mutation backup removes the post-backup addition")
check(len(app.db.get_all_entries(language='spanish')) == 3, "Spanish entries intact after the round-trip restore")
check(len(app.db.get_all_reading_texts()) == 3, "all 3 reading texts (across both languages) intact after restore")

# this time STORAGE_FILE genuinely had prior content, so the safety-backup
# branch in _restore_data() should have fired
safety_backups_after_second_restore = [fn for fn in os.listdir(tmpdir) if fn.startswith('vocabulary_data.json.backup_')]
check(len(safety_backups_after_second_restore) >= 1,
      f"a safety backup of the pre-restore (mutated) data was created this time (got {safety_backups_after_second_restore})")

root.destroy()

print()
if failures:
    print(f"SMOKE TEST: {len(failures)} FAILURE(S):")
    for f_ in failures:
        print(f"  - {f_}")
    raise SystemExit(1)
else:
    print("SMOKE TEST: all checks passed")
