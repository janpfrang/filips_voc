"""
Headless GUI smoke test for Phase 3 (active-language state + toggle).
Not part of the pytest suite -- exercises the real VocabularyApp language
switcher and the resulting scoping across all tabs, under Xvfb.
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


# === Startup default (REQ-LANG-06) ===
check(app.active_language == 'english', f"app starts on English by default (got {app.active_language})")
check(app.language_var.get() == 'english', "language switcher reflects English on startup")

# === Add English entries (default language) ===
add_ui = app.add_modify_ui
for word, translation in [("hello", "hallo"), ("world", "welt")]:
    add_ui.english_entry.delete(0, tk.END)
    add_ui.german_entry.delete(0, tk.END)
    add_ui.english_entry.insert(0, word)
    add_ui.german_entry.insert(0, translation)
    add_ui._add_vocabulary()

check(len(app.db.get_all_entries(language='english')) == 2, "two English entries added")
check(add_ui.foreign_label.cget('text') == 'English Word:', "Add/Modify label shows 'English Word:' while English active")

# === Upload an English reading text before switching ===
app.db.add_reading_text("English Text", "hello there", language='english')

# === Switch to Spanish ===
app._set_active_language('spanish')
check(app.active_language == 'spanish', "app switched to Spanish")
check(add_ui.active_language == 'spanish', "AddModifyUI propagated language switch")
check(add_ui.foreign_label.cget('text') == 'Spanish Word:', f"Add/Modify label now 'Spanish Word:' (got {add_ui.foreign_label.cget('text')!r})")
check(add_ui.english_entry.get() == '', "switching language cleared the add-entry input field")

# === Add Spanish entries ===
for word, translation in [("hola", "hallo"), ("adios", "tschüss")]:
    add_ui.english_entry.delete(0, tk.END)
    add_ui.german_entry.delete(0, tk.END)
    add_ui.english_entry.insert(0, word)
    add_ui.german_entry.insert(0, translation)
    add_ui._add_vocabulary()

spanish_entries = app.db.get_all_entries(language='spanish')
check(len(spanish_entries) == 2, "two Spanish entries added")
check({e['id'] for e in spanish_entries} == {'S1', 'S2'}, f"Spanish entries got S-prefixed ids (got {[e['id'] for e in spanish_entries]})")
check(len(app.db.get_all_entries(language='english')) == 2, "English entries untouched by Spanish adds")

# add a Spanish reading text too, interleaved with the earlier English one
app.db.add_reading_text("Texto en Espanol", "hola amigo", language='spanish')

# === List tab scoping ===
list_ui = app.list_ui
list_ui._refresh_list()
rows = [list_ui.tree.item(i, 'values') for i in list_ui.tree.get_children()]
check(len(rows) == 2, f"List tab shows only the 2 Spanish entries while Spanish is active (got {len(rows)})")
check(all(r[0].startswith('S') for r in rows), "all visible list rows are Spanish (S-prefixed)")
check(list_ui.title_label.cget('text') == '📜 Vocabulary List — Spanish', f"list title reflects active language (got {list_ui.title_label.cget('text')!r})")
check(list_ui.tree.heading('English')['text'] == 'Spanish', "list column header relabeled to 'Spanish'")

# === Cross-language edit is rejected (AddModifyUI language guard) ===
english_id = app.db.get_all_entries(language='english')[0]['id']
error_calls.clear()
add_ui.modify_id_entry.delete(0, tk.END)
add_ui.modify_id_entry.insert(0, english_id)
add_ui._load_entry()
check(len(error_calls) == 1, f"loading an English entry ID while Spanish is active is rejected cleanly (got {error_calls})")

# === Quiz tab scoping ===
quiz_ui = app.quiz_ui
quiz_ui._start_quiz("Last 10")
check(len(quiz_ui.quiz_entries) == 2, "quiz pool contains only the 2 Spanish entries")
check(all(e['language'] == 'spanish' for e in quiz_ui.quiz_entries), "all quiz entries are Spanish")
check(quiz_ui.quiz_mode.startswith("Spanish -"), f"quiz display name is language-prefixed (got {quiz_ui.quiz_mode!r})")

# answer both questions to exercise recording + finish
quiz_ui.answer_entry.insert(0, quiz_ui.quiz_entries[0]['foreign_word'])
quiz_ui._submit_answer()
quiz_ui.answer_entry.insert(0, quiz_ui.quiz_entries[1]['foreign_word'])
quiz_ui._submit_answer()
check(quiz_ui.quiz_results == [True, True], "quiz recorded both Spanish answers correctly")

# === Reading tab scoping + the _on_text_selected index-mapping fix ===
reading_ui = app.reading_ui
reading_ui._refresh_text_list()
items = reading_ui.text_listbox.get(0, tk.END)
check(len(items) == 1 and "Texto en Espanol" in items[0], f"Reading tab shows only the Spanish text (got {items})")

# select index 0 in the (Spanish-only) listbox and confirm it resolves to the
# correct Spanish text, not an English one interleaved earlier in upload order
reading_ui.text_listbox.selection_set(0)
reading_ui._on_text_selected(None)
selected = app.db.get_reading_text_by_id(reading_ui.current_text_id)
check(selected is not None and selected['language'] == 'spanish' and selected['title'] == 'Texto en Espanol',
      f"selecting listbox index 0 resolves to the correct Spanish text (got {selected})")

# === CSV export is language-aware (REQ-LANG-04) ===
list_ui._export_to_csv()
with open(csv_path_holder['path'], newline='', encoding='utf-8') as f:
    reader = csv_module.DictReader(f, delimiter=';')
    header = reader.fieldnames
    csv_rows = list(reader)
check('Spanish' in header, f"CSV header uses 'Spanish' column instead of 'English' (got {header})")
check(len(csv_rows) == 2, f"CSV export contains only the 2 Spanish entries (got {len(csv_rows)})")
check('spanish' in csv_path_holder['path'], f"CSV filename is language-tagged (got {csv_path_holder['path']})")

# === Switch back to English: everything re-scopes back ===
app._set_active_language('english')
list_ui._refresh_list()
rows_en = [list_ui.tree.item(i, 'values') for i in list_ui.tree.get_children()]
check(len(rows_en) == 2 and all(r[0].startswith('E') for r in rows_en), "switching back to English re-scopes the list correctly")

reading_ui._refresh_text_list()
items_en = reading_ui.text_listbox.get(0, tk.END)
check(len(items_en) == 1 and "English Text" in items_en[0], "switching back to English re-scopes the reading list correctly")

root.destroy()

print()
if failures:
    print(f"SMOKE TEST: {len(failures)} FAILURE(S):")
    for f_ in failures:
        print(f"  - {f_}")
    raise SystemExit(1)
else:
    print("SMOKE TEST: all checks passed")
