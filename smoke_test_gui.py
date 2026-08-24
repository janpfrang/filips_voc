"""
Headless GUI smoke test for Phase 2 (English UI re-pointed at the v1.1 schema).
Not part of the pytest suite -- exercises the actual Tkinter widgets/handlers
(no automated coverage existed for these before), with blocking dialogs patched
out so it can run unattended under Xvfb.
"""
import os
import tempfile
import csv as csv_module

import tkinter as tk
from tkinter import messagebox, filedialog

import main_code_voc as m

# --- neutralize blocking modal dialogs -------------------------------------
info_calls = []
warn_calls = []
error_calls = []

messagebox.showinfo = lambda title, msg: info_calls.append((title, msg))
messagebox.showwarning = lambda title, msg: warn_calls.append((title, msg))
messagebox.showerror = lambda title, msg: error_calls.append((title, msg))
messagebox.askyesno = lambda title, msg: True

csv_path_holder = {}


def fake_asksaveasfilename(**kwargs):
    path = os.path.join(tempfile.mkdtemp(), kwargs.get('initialfile', 'export.csv'))
    csv_path_holder['path'] = path
    return path


filedialog.asksaveasfilename = fake_asksaveasfilename

# QuizUI._show_large_message opens its own modal Toplevel (not messagebox) and
# blocks on wait_window() waiting for a click -- neutralize it for headless testing
m.QuizUI._show_large_message = lambda self, title, message, color: None

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


# === AddModifyUI: add ===
add_ui = app.add_modify_ui
add_ui.english_entry.insert(0, "hello")
add_ui.german_entry.insert(0, "hallo")
add_ui._add_vocabulary()

entries = app.db.get_all_entries()
check(len(entries) == 1, "one entry after add")
check(entries[0]['id'] == 'E1', f"first entry got prefixed id E1 (got {entries[0]['id']!r})")
check(entries[0]['foreign_word'] == 'hello', "foreign_word stored correctly")
check(entries[0]['language'] == 'english', "language defaults to english")
check(not error_calls, f"no errors during add (got {error_calls})")

# add a second entry to exercise multi-entry sorting/listing
add_ui.english_entry.delete(0, tk.END)
add_ui.german_entry.delete(0, tk.END)
add_ui.english_entry.insert(0, "world")
add_ui.german_entry.insert(0, "welt")
add_ui._add_vocabulary()
check(len(app.db.get_all_entries()) == 2, "two entries after second add")
check(app.db.get_all_entries()[1]['id'] == 'E2', "second entry got E2")

# === AddModifyUI: load + modify ===
add_ui.modify_id_entry.insert(0, "E1")
add_ui._load_entry()
check(add_ui.modify_english_entry.get() == 'hello', "load populated english field")
check(add_ui.modify_german_entry.get() == 'hallo', "load populated german field")

add_ui.modify_english_entry.delete(0, tk.END)
add_ui.modify_english_entry.insert(0, "hi")
add_ui.modify_german_entry.delete(0, tk.END)
add_ui.modify_german_entry.insert(0, "hi (informal)")
add_ui._modify_vocabulary()
updated = app.db.get_entry_by_id("E1")
check(updated['foreign_word'] == 'hi', f"modify updated foreign_word (got {updated['foreign_word']!r})")

# non-existent ID handling (no crash, clean error path)
add_ui.modify_id_entry.delete(0, tk.END)
add_ui.modify_id_entry.insert(0, "E999")
error_calls.clear()
add_ui._load_entry()
check(len(error_calls) == 1, "loading unknown ID shows a clean error, no crash")

# === QuizUI: full quiz flow (Last 10) ===
quiz_ui = app.quiz_ui
quiz_ui._start_quiz("Last 10")
check(len(quiz_ui.quiz_entries) == 2, "quiz pool has both entries")

# answer question 1 correctly, question 2 incorrectly
first_entry = quiz_ui.quiz_entries[0]
quiz_ui.answer_entry.insert(0, first_entry['foreign_word'])
quiz_ui._submit_answer()

second_entry = quiz_ui.quiz_entries[1]
quiz_ui.answer_entry.insert(0, "definitely_wrong")
quiz_ui._submit_answer()

check(quiz_ui.quiz_results == [True, False], f"quiz recorded correct/wrong (got {quiz_ui.quiz_results})")
stats = app.db.get_statistics()
check(stats['total_correct'] == 1 and stats['total_wrong'] == 1, "quiz results persisted to DB")

# === ListUI: refresh, search, doublets, statistics ===
list_ui = app.list_ui
list_ui._refresh_list()
rows = [list_ui.tree.item(i, 'values') for i in list_ui.tree.get_children()]
check(len(rows) == 2, f"list shows both entries (got {len(rows)})")
ids_in_list = {r[0] for r in rows}
check(ids_in_list == {'E1', 'E2'}, f"list rows carry correct string IDs (got {ids_in_list})")

list_ui.search_entry.insert(0, "world")
list_ui._search_vocabulary()
search_rows = [list_ui.tree.item(i, 'values') for i in list_ui.tree.get_children()]
check(len(search_rows) == 1 and search_rows[0][1] == 'world', "search finds the right entry")

list_ui._clear_search()

# add a duplicate to test doublets (case-insensitive)
app.db.add_entry("World", "welt (upper)")
list_ui._find_doublets()
tagged = [list_ui.tree.item(i, 'tags') for i in list_ui.tree.get_children()]
check(any('doublet' in t for t in tagged), "doublet detection tags duplicate rows without crashing on string IDs")

warn_calls.clear()
info_calls.clear()
list_ui._show_statistics()
check(len(info_calls) == 1, "statistics dialog rendered without error")

# === ListUI: CSV export ===
list_ui._export_to_csv()
check('path' in csv_path_holder, "CSV export triggered save dialog")
with open(csv_path_holder['path'], newline='', encoding='utf-8') as f:
    reader = csv_module.DictReader(f, delimiter=';')
    csv_rows = list(reader)
check(len(csv_rows) == 3, f"CSV has all 3 entries (got {len(csv_rows)})")
check(all(row['English'] for row in csv_rows), "CSV 'English' column populated from foreign_word field")
check([row['ID'] for row in csv_rows] == sorted([row['ID'] for row in csv_rows], key=lambda x: x),
      "CSV rows in stable order")

# === ReadingUI: upload (direct DB call, dialog-free) + view/select/delete via UI ===
app.db.add_reading_text("My Text", "Hello world, hello again!")
reading_ui = app.reading_ui
reading_ui._refresh_text_list()
items = reading_ui.text_listbox.get(0, tk.END)
check(len(items) == 1 and "My Text" in items[0], f"reading text listed (got {items})")

reading_texts = app.db.get_all_reading_texts()
check(reading_texts[0]['id'] == 'E1', f"reading text got prefixed id E1 (got {reading_texts[0]['id']!r})")
# By this point E1 was renamed hello->hi (modify test above) and a duplicate
# "World" entry exists (doublets test above), so "world" matches 2 distinct
# vocab entries (E2 "world" + E3 "World") -- confirms matching now reads
# foreign_word (not the old 'english' key) and still works correctly.
check(reading_texts[0]['vocabulary_matches'] == 2, f"reading text matched via foreign_word field (got {reading_texts[0]['vocabulary_matches']})")

reading_ui.current_text_id = reading_texts[0]['id']
reading_ui._view_selected_text()
check(reading_ui.text_display.get('1.0', tk.END).strip().startswith("Hello world"),
      "selected reading text rendered in viewer")
tag_ranges = reading_ui.text_display.tag_ranges('vocab')
check(len(tag_ranges) > 0, "vocabulary highlighting applied to reading text")

info_calls.clear()
reading_ui._delete_selected_text()
check(len(app.db.get_all_reading_texts()) == 0, "reading text deleted via UI")

root.destroy()

print()
if failures:
    print(f"SMOKE TEST: {len(failures)} FAILURE(S):")
    for f_ in failures:
        print(f"  - {f_}")
    raise SystemExit(1)
else:
    print("SMOKE TEST: all checks passed")
