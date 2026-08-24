"""
Headless GUI smoke test for Phase 4 (Spanish special-character input widget
+ Unicode normalization). Not part of the pytest suite -- exercises the real
SpecialCharacterBar widget and REQ-NF-07 normalization, under Xvfb.
"""
import os
import tempfile
import unicodedata

import tkinter as tk
from tkinter import messagebox

import main_code_voc as m

# --- neutralize blocking modal dialogs -------------------------------------
info_calls = []
warn_calls = []
error_calls = []

messagebox.showinfo = lambda title, msg: info_calls.append((title, msg))
messagebox.showwarning = lambda title, msg: warn_calls.append((title, msg))
messagebox.showerror = lambda title, msg: error_calls.append((title, msg))
messagebox.askyesno = lambda title, msg: True
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


# === Visibility: hidden on English, shown on Spanish (REQ-SPCHAR-01/04) ===
add_ui = app.add_modify_ui
def is_gridded(widget):
    # grid_remove() clears grid manager info; grid() restores it. This is a
    # deterministic check of "is this widget currently placed by grid()",
    # unlike winfo_ismapped() which depends on the window manager actually
    # having drawn a frame -- not guaranteed without an event-loop tick.
    return bool(widget.grid_info())


check(not is_gridded(add_ui.add_char_bar.frame), "Add-section char bar hidden while English is active")
check(not is_gridded(add_ui.modify_char_bar.frame), "Modify-section char bar hidden while English is active")

app._set_active_language('spanish')
check(is_gridded(add_ui.add_char_bar.frame), "Add-section char bar shown once Spanish is active")
check(is_gridded(add_ui.modify_char_bar.frame), "Modify-section char bar shown once Spanish is active")

quiz_ui = app.quiz_ui
check(not is_gridded(quiz_ui.char_bar.frame), "Quiz char bar stays hidden until a quiz is actually running")

# === Button set matches REQ-SPCHAR-01 (no ü) ===
expected_chars = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'Ñ', '¿', '¡']
actual_chars = [w.cget('text') for w in add_ui.add_char_bar.frame.winfo_children()]
check(actual_chars == expected_chars, f"character set matches spec, ü excluded (got {actual_chars})")

# === Clicking inserts at cursor position, not just appended (REQ-SPCHAR-03) ===
add_ui.english_entry.delete(0, tk.END)
add_ui.english_entry.insert(0, "hla")
add_ui.english_entry.icursor(1)  # cursor between 'h' and 'l' -> want "hola"
add_ui.english_entry.focus_set()
root.update()  # let the <FocusIn> binding register this as the active target
add_ui.add_char_bar._insert_character('o')
check(add_ui.english_entry.get() == "hola", f"character inserted at cursor position, not appended (got {add_ui.english_entry.get()!r})")

# === Focus tracking picks the right target among multiple registered entries ===
add_ui.modify_english_entry.delete(0, tk.END)
add_ui.modify_english_entry.insert(0, "nio")
add_ui.modify_english_entry.icursor(0)
add_ui.modify_english_entry.focus_set()
root.update()
add_ui.modify_char_bar._insert_character('ñ')
check(add_ui.modify_english_entry.get() == "ñnio", f"modify-field char bar targets the modify field, not the add field (got {add_ui.modify_english_entry.get()!r})")
check(add_ui.english_entry.get() == "hola", "earlier add-field insert was untouched by the modify-field click")

# === Add a Spanish entry via the char bar, save, verify stored correctly ===
add_ui.english_entry.delete(0, tk.END)
add_ui.english_entry.insert(0, "hola")
add_ui.german_entry.delete(0, tk.END)
add_ui.german_entry.insert(0, "hallo")
add_ui._add_vocabulary()
entries = app.db.get_all_entries(language='spanish')
check(any(e['foreign_word'] == 'hola' for e in entries), f"Spanish entry with accented-adjacent word saved correctly (got {[e['foreign_word'] for e in entries]})")

# add one with an actual accent for the normalization test below
add_ui.english_entry.delete(0, tk.END)
add_ui.german_entry.delete(0, tk.END)
add_ui.english_entry.insert(0, "caf")
add_ui.english_entry.icursor(3)
add_ui.english_entry.focus_set()
root.update()
add_ui.add_char_bar._insert_character('é')
check(add_ui.english_entry.get() == "café", f"button-inserted word reads correctly (got {add_ui.english_entry.get()!r})")
add_ui.german_entry.insert(0, "kaffee")
add_ui._add_vocabulary()

stored = [e for e in app.db.get_all_entries(language='spanish') if e['foreign_word'] == 'café']
check(len(stored) == 1, f"'café' (button-composed) stored under the expected key (got {[e['foreign_word'] for e in app.db.get_all_entries(language='spanish')]})")

# === REQ-NF-07: NFC normalization so visually-identical answers compare equal ===
# Build an NFD ("decomposed") version of the same word: e + combining acute accent.
nfd_cafe = unicodedata.normalize('NFD', 'café')
check(nfd_cafe != 'café', "sanity check: NFD form is a different byte sequence than the stored NFC form")

quiz_ui._start_quiz("Last 10")
check(is_gridded(quiz_ui.char_bar.frame), "Quiz char bar appears once a Spanish quiz is running")
cafe_entry = [e for e in quiz_ui.quiz_entries if e['foreign_word'] == 'café'][0]
quiz_ui.current_index = quiz_ui.quiz_entries.index(cafe_entry)
quiz_ui.answer_entry.delete(0, tk.END)
quiz_ui.answer_entry.insert(0, nfd_cafe)  # visually "café" but a different Unicode form
quiz_ui._submit_answer()
check(quiz_ui.quiz_results[-1] is True,
      f"NFD-typed answer matches NFC-stored word after normalization (results: {quiz_ui.quiz_results})")

# === Switching back to English hides all char bars again ===
app._set_active_language('english')
check(not is_gridded(add_ui.add_char_bar.frame), "Add-section char bar hidden again after switching back to English")
check(not is_gridded(add_ui.modify_char_bar.frame), "Modify-section char bar hidden again after switching back to English")

root.destroy()

print()
if failures:
    print(f"SMOKE TEST: {len(failures)} FAILURE(S):")
    for f_ in failures:
        print(f"  - {f_}")
    raise SystemExit(1)
else:
    print("SMOKE TEST: all checks passed")
