"""
Filip's English Vocabulary Learning App - Desktop Version (Refactored)
Version 2.61 - Added Reading Module
- Reading texts upload and display
- Vocabulary highlighting in texts
- Reading statistics

Requirements:
- Python 3.7+
- No additional packages needed (uses only standard library)

To create .exe:
    pyinstaller --onefile --windowed --name "FilipVocabularyApp" vocabulary_app_with_reading.py

Architecture:
    VocabularyApp (Main)
      ├── VocabularyDatabase (standalone) - EXTENDED with reading texts
      ├── EmailModule (standalone)
      ├── AddModifyUI → VocabularyDatabase
      ├── QuizUI → VocabularyDatabase, notification_callback
      ├── ListUI → VocabularyDatabase
      ├── ReadingUI → VocabularyDatabase (NEW)
      └── SettingsUI → EmailModule
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import os
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, List, Optional, Callable, Dict
import re
import csv
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalisiert Text auf Unicode NFC (REQ-NF-07).

    Text, der über die Sonderzeichen-Buttons eingefügt wird, und Text, der
    direkt getippt oder eingefügt wird, können unterschiedliche, aber optisch
    identische Unicode-Repräsentationen ergeben (z.B. vorkomponiertes 'é' vs.
    'e' + Akzent als eigenes Zeichen). Ohne Normalisierung könnten zwei
    optisch gleiche Wörter als unterschiedlich gelten (Quiz-Auswertung,
    Suche, Doublet-Erkennung). NFC wird sowohl beim Speichern (VocabularyDatabase)
    als auch beim Vergleich frisch eingegebenen Textes (Quiz-Antwort, Suche)
    angewendet.

    Args:
        text: Eingabetext

    Returns:
        NFC-normalisierter Text
    """
    return unicodedata.normalize('NFC', text)


# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """
    Zentrale Konfiguration der Vocabulary App.

    Hier können alle wichtigen Einstellungen angepasst werden,
    ohne den Code zu ändern.
    """
    # Datei-Speicherung
    STORAGE_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "FilipVocabularyApp")
    STORAGE_FILE = os.path.join(STORAGE_FOLDER, "vocabulary_data.json")

    # Email-Einstellungen
    EMAIL_RECIPIENT = "janpfrang@hotmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    # App-Version
    VERSION = "2.61"
    APP_NAME = "Filip's English Vocabulary Learning App"

    # UI-Einstellungen
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 700

    # Sprachen (v1.1) — Anzeigename je unterstützter Sprache, zentrale Quelle
    # für alle UI-Module (Labels, Spaltenüberschriften, Dateinamen, ...)
    LANGUAGE_LABELS = {
        'english': 'English',
        'spanish': 'Spanish',
    }
    DEFAULT_LANGUAGE = 'english'  # REQ-LANG-06: App startet immer auf Englisch


# ============================================================================
# MODULE: DATABASE
# ============================================================================
class VocabularyDatabase:
    """
    Vocabulary Database Module - Verwaltet alle Daten-Operationen
    EXTENDED (v1.1): Multi-language aware (English/Spanish), manages reading texts

    Every vocabulary entry and reading text now carries a 'language' field
    ('english' | 'spanish') and an ID prefixed per language (E<n> / S<n>),
    with independent numbering per language. See REQUIREMENTS.md v1.1,
    Section 5 (Data Model) and Section 9 (Migration Requirements).

    PUBLIC API:
    ===========

    Vocabulary CRUD Operations:
    - add_entry(foreign_word: str, german: str, language: str = 'english') → Tuple[bool, str]
    - update_entry(id: str, foreign_word: str, german: str) → Tuple[bool, str]
    - delete_entry(id: str) → Tuple[bool, str]

    Vocabulary Query Operations (all accept optional language filter):
    - get_all_entries(language: Optional[str] = None) → List[dict]
    - get_entry_by_id(id: str) → Optional[dict]
    - get_recent_entries(count: int = 10, language: Optional[str] = None) → List[dict]
    - get_random_entries(count: int = 30, language: Optional[str] = None) → List[dict]
    - get_incorrect_entries(language: Optional[str] = None) → List[dict]
    - get_never_tested_entries(language: Optional[str] = None) → List[dict]
    - get_sorted_entries(sort_by: str = 'foreign_word', language: Optional[str] = None) → List[dict]
    - get_entries_by_date(date_str: str, language: Optional[str] = None) → List[dict]

    Reading Text Operations:
    - add_reading_text(title: str, content: str, language: str = 'english') → Tuple[bool, str]
    - get_all_reading_texts(language: Optional[str] = None) → List[dict]
    - get_reading_text_by_id(id: str) → Optional[dict]
    - delete_reading_text(id: str) → Tuple[bool, str]
    - find_vocabulary_in_text(text_content: str, language: Optional[str] = None) → List[dict]
    - get_reading_statistics(language: Optional[str] = None) → Dict

    Statistics & Tracking:
    - get_statistics(language: Optional[str] = None) → Dict
    - record_quiz_result(id: str, is_correct: bool) → Tuple[bool, str]

    Data Management:
    - load() → Tuple[bool, str]
    - save() → Tuple[bool, str]
    """

    # Supported languages and their ID prefixes (REQUIREMENTS.md REQ-MIG-02/06)
    LANGUAGE_PREFIXES = {
        'english': 'E',
        'spanish': 'S',
    }

    def __init__(self, storage_path: str):
        """
        Initialisiert die Datenbank.

        Args:
            storage_path: Pfad zur JSON-Datei für Datenspeicherung
        """
        self.storage_path = storage_path
        self.vocabulary: List[Dict] = []
        self.reading_texts: List[Dict] = []  # NEW
        self.load()

    # === PUBLIC API - Data Management ===

    def load(self) -> Tuple[bool, str]:
        """
        Lädt Vocabulary-Daten und Reading Texts aus der Datei.
        Führt automatisch Migration für alte Formate durch.

        Returns:
            (True, "Loaded X entries") bei Erfolg
            (False, "Error: ...") bei Fehler
        """
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle both old format (list) and new format (dict)
                if isinstance(data, list):
                    # Old format: just vocabulary list
                    self.vocabulary = data
                    self.reading_texts = []
                elif isinstance(data, dict):
                    # New format: dict with vocabulary and reading_texts
                    self.vocabulary = data.get('vocabulary', [])
                    self.reading_texts = data.get('reading_texts', [])
                else:
                    self.vocabulary = []
                    self.reading_texts = []

                # Migration von altem Format (fehlende IDs etc.)
                migrated_legacy = self._migrate_old_format()
                # Migration zum sprachbewussten v1.1-Schema (language, foreign_word, prefixierte IDs)
                migrated_schema = self._migrate_to_language_schema()
                migrated = migrated_legacy or migrated_schema
                if migrated:
                    self.save()
                    return True, f"Loaded and migrated {len(self.vocabulary)} vocabulary entries, {len(self.reading_texts)} reading texts"

                return True, f"Loaded {len(self.vocabulary)} vocabulary entries, {len(self.reading_texts)} reading texts"
            else:
                self.vocabulary = []
                self.reading_texts = []
                return False, "No existing data file found"
        except Exception as e:
            self.vocabulary = []
            self.reading_texts = []
            return False, f"Error loading: {e}"

    def save(self) -> Tuple[bool, str]:
        """
        Speichert Vocabulary-Daten und Reading Texts in die Datei.
        Uses new format with backward compatibility.

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Error: ...") bei Fehler
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            # New format: dict with both vocabulary and reading_texts
            data = {
                'vocabulary': self.vocabulary,
                'reading_texts': self.reading_texts
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True, "Saved successfully"
        except Exception as e:
            return False, f"Error saving: {e}"

    # === PUBLIC API - Vocabulary CRUD Operations ===

    def add_entry(self, foreign_word: str, german: str,
                  language: str = 'english') -> Tuple[bool, str]:
        """
        Fügt einen neuen Vokabel-Eintrag hinzu.

        Args:
            foreign_word: Wort in der Fremdsprache (Englisch oder Spanisch)
            german: Deutsche Übersetzung
            language: 'english' oder 'spanish' (siehe LANGUAGE_PREFIXES)

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Error: ...") bei Fehler (z.B. unbekannte Sprache)
        """
        if language not in self.LANGUAGE_PREFIXES:
            return False, f"Error: Unsupported language '{language}'"

        entry = {
            'id': self._generate_vocab_id(language),
            'language': language,
            'foreign_word': normalize_text(foreign_word),  # REQ-NF-07
            'german': normalize_text(german),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_queried': None,
            'last_result': None,
            'correct_count': 0,
            'wrong_count': 0
        }
        self.vocabulary.append(entry)
        return self.save()

    def update_entry(self, entry_id: str, foreign_word: Optional[str] = None,
                     german: Optional[str] = None) -> Tuple[bool, str]:
        """
        Aktualisiert einen existierenden Vokabel-Eintrag.
        Die Sprache eines Eintrags kann nicht nachträglich geändert werden.

        Args:
            entry_id: ID des zu aktualisierenden Eintrags (z.B. 'E3', 'S7')
            foreign_word: Neues fremdsprachiges Wort (optional)
            german: Neuer deutscher Text (optional)

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Entry not found") wenn ID nicht existiert
        """
        for entry in self.vocabulary:
            if entry['id'] == entry_id:
                if foreign_word is not None:
                    entry['foreign_word'] = normalize_text(foreign_word)  # REQ-NF-07
                if german is not None:
                    entry['german'] = normalize_text(german)
                return self.save()
        return False, "Entry not found"

    def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """
        Löscht einen Vokabel-Eintrag.

        Args:
            entry_id: ID des zu löschenden Eintrags

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Entry not found") wenn ID nicht existiert
        """
        original_length = len(self.vocabulary)
        self.vocabulary = [v for v in self.vocabulary if v['id'] != entry_id]
        if len(self.vocabulary) < original_length:
            return self.save()
        return False, "Entry not found"

    # === PUBLIC API - Vocabulary Query Operations ===

    def _filter_by_language(self, items: List[Dict], language: Optional[str]) -> List[Dict]:
        """
        Interner Helper: filtert eine Liste von Einträgen/Texten nach Sprache.
        language=None bedeutet "keine Filterung" (alle Sprachen).
        """
        if language is None:
            return items
        return [item for item in items if item.get('language') == language]

    def get_all_entries(self, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt alle Vokabel-Einträge zurück, optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste der Einträge (Kopien, nicht das Original)
        """
        return [entry.copy() for entry in self._filter_by_language(self.vocabulary, language)]

    def get_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        """
        Gibt einen spezifischen Eintrag zurück.

        Args:
            entry_id: ID des gesuchten Eintrags (z.B. 'E3', 'S7')

        Returns:
            Entry-Dictionary oder None wenn nicht gefunden
        """
        for entry in self.vocabulary:
            if entry['id'] == entry_id:
                return entry.copy()
        return None

    def get_recent_entries(self, count: int = 10, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt die zuletzt hinzugefügten Einträge zurück, optional nach Sprache gefiltert.

        Args:
            count: Anzahl der gewünschten Einträge
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste der letzten 'count' Einträge (in Einfügereihenfolge)
        """
        filtered = self._filter_by_language(self.vocabulary, language)
        recent = filtered[-count:] if len(filtered) >= count else filtered
        return [entry.copy() for entry in recent]

    def get_random_entries(self, count: int = 30, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt zufällige Vokabel-Einträge zurück, optional nach Sprache gefiltert.

        Args:
            count: Anzahl der gewünschten Einträge
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste von zufälligen Einträgen
        """
        filtered = self._filter_by_language(self.vocabulary, language)
        if len(filtered) <= count:
            return [entry.copy() for entry in filtered]
        return [entry.copy() for entry in random.sample(filtered, count)]

    def get_incorrect_entries(self, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt alle Einträge zurück, die zuletzt falsch beantwortet wurden,
        optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste von Einträgen mit last_result == False
        """
        filtered = self._filter_by_language(self.vocabulary, language)
        return [entry.copy() for entry in filtered if entry.get('last_result') == False]


    def get_never_tested_entries(self, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt alle Einträge zurück, die noch nie getestet wurden,
        optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste von Einträgen mit last_queried == None
        """
        filtered = self._filter_by_language(self.vocabulary, language)
        return [entry.copy() for entry in filtered if entry.get('last_queried') is None]

    def get_sorted_entries(self, sort_by: str = 'foreign_word',
                           language: Optional[str] = None) -> List[Dict]:
        """
        Gibt sortierte Einträge zurück, optional nach Sprache gefiltert.

        Args:
            sort_by: Feld nach dem sortiert werden soll (Default: 'foreign_word')
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Sortierte Liste von Einträgen
        """
        filtered = self._filter_by_language(self.vocabulary, language)
        sorted_entries = sorted(filtered, key=lambda x: str(x.get(sort_by, '')).lower())
        return [entry.copy() for entry in sorted_entries]

    def get_entries_by_date(self, date_str: str, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt alle Einträge zurück, die an einem bestimmten Datum erstellt wurden,
        optional nach Sprache gefiltert.

        Args:
            date_str: Datum im Format YYYY-MM-DD
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste von Einträgen die an diesem Tag erstellt wurden
        """
        entries = []
        for entry in self._filter_by_language(self.vocabulary, language):
            created_at = entry.get('created_at', '')
            # Extrahiere nur das Datum (erste 10 Zeichen: YYYY-MM-DD)
            entry_date = created_at[:10] if len(created_at) >= 10 else ''
            if entry_date == date_str:
                entries.append(entry.copy())
        return entries

    # === PUBLIC API - Reading Text Operations (NEW) ===

    def add_reading_text(self, title: str, content: str,
                         language: str = 'english') -> Tuple[bool, str]:
        """
        Fügt einen neuen Lesetext hinzu.

        Args:
            title: Titel des Textes
            content: Textinhalt
            language: 'english' oder 'spanish' — bestimmt, gegen welche
                      Vokabeln der Text auf Treffer geprüft wird

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Error: ...") bei Fehler (z.B. unbekannte Sprache)
        """
        if language not in self.LANGUAGE_PREFIXES:
            return False, f"Error: Unsupported language '{language}'"

        # Analyse: Finde Vokabeln (derselben Sprache) im Text
        matches = self.find_vocabulary_in_text(content, language=language)
        word_count = len(content.split())

        text_entry = {
            'id': self._generate_reading_id(language),
            'language': language,
            'title': title,
            'content': content,
            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'word_count': word_count,
            'vocabulary_matches': len(matches)
        }
        self.reading_texts.append(text_entry)
        return self.save()

    def get_all_reading_texts(self, language: Optional[str] = None) -> List[Dict]:
        """
        Gibt alle Lesetexte zurück, optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Liste der Reading Texts (Kopie)
        """
        return [text.copy() for text in self._filter_by_language(self.reading_texts, language)]

    def get_reading_text_by_id(self, text_id: str) -> Optional[Dict]:
        """
        Gibt einen spezifischen Reading Text zurück.

        Args:
            text_id: ID des gesuchten Textes

        Returns:
            Text-Dictionary oder None wenn nicht gefunden
        """
        for text in self.reading_texts:
            if text['id'] == text_id:
                return text.copy()
        return None

    def delete_reading_text(self, text_id: str) -> Tuple[bool, str]:
        """
        Löscht einen Reading Text.

        Args:
            text_id: ID des zu löschenden Textes

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Text not found") wenn ID nicht existiert
        """
        original_length = len(self.reading_texts)
        self.reading_texts = [t for t in self.reading_texts if t['id'] != text_id]
        if len(self.reading_texts) < original_length:
            return self.save()
        return False, "Text not found"

    def find_vocabulary_in_text(self, text_content: str,
                                language: Optional[str] = None) -> List[Dict]:
        """
        Findet alle Vokabeln aus der Database im gegebenen Text.

        Args:
            text_content: Text in dem gesucht werden soll
            language: Wenn gesetzt, werden nur Vokabeln dieser Sprache
                      berücksichtigt (verhindert z.B. dass ein spanischer
                      Text fälschlich gegen englische Vokabeln matcht)

        Returns:
            Liste von Dictionaries mit gefundenen Vokabeln und deren Positionen
            Format: [{'vocab': entry, 'positions': [(start, end), ...]}, ...]
        """
        matches = []
        text_lower = text_content.lower()

        for entry in self._filter_by_language(self.vocabulary, language):
            foreign_word = entry['foreign_word'].lower()
            # Find all occurrences of this word
            positions = []

            # Use word boundary regex for exact word matching
            pattern = r'\b' + re.escape(foreign_word) + r'\b'
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                positions.append((match.start(), match.end()))

            if positions:
                matches.append({
                    'vocab': entry,
                    'positions': positions
                })

        return matches

    def get_reading_statistics(self, language: Optional[str] = None) -> Dict:
        """
        Gibt Statistiken über Reading Texts zurück, optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Dictionary mit Statistiken
        """
        texts = self._filter_by_language(self.reading_texts, language)

        if not texts:
            return {
                'total_texts': 0,
                'total_words': 0,
                'average_words': 0,
                'total_vocab_matches': 0,
                'average_vocab_matches': 0
            }

        total_words = sum(t.get('word_count', 0) for t in texts)
        total_matches = sum(t.get('vocabulary_matches', 0) for t in texts)

        return {
            'total_texts': len(texts),
            'total_words': total_words,
            'average_words': total_words / len(texts),
            'total_vocab_matches': total_matches,
            'average_vocab_matches': total_matches / len(texts)
        }

    # === PUBLIC API - Statistics & Tracking ===

    def get_statistics(self, language: Optional[str] = None) -> Dict:
        """
        Gibt Statistiken über das Vocabulary zurück, optional nach Sprache gefiltert.

        Args:
            language: 'english', 'spanish', oder None für alle Sprachen

        Returns:
            Dictionary mit Statistiken
        """
        entries = self._filter_by_language(self.vocabulary, language)
        total = len(entries)
        queried = sum(1 for v in entries if v.get('last_queried') is not None)
        total_correct = sum(v.get('correct_count', 0) for v in entries)
        total_wrong = sum(v.get('wrong_count', 0) for v in entries)

        return {
            'total_entries': total,
            'queried_entries': queried,
            'never_queried': total - queried,
            'total_correct': total_correct,
            'total_wrong': total_wrong,
            'success_rate': total_correct / (total_correct + total_wrong) * 100 if (total_correct + total_wrong) > 0 else 0
        }

    def record_quiz_result(self, entry_id: str, is_correct: bool) -> Tuple[bool, str]:
        """
        Speichert das Ergebnis einer Quiz-Frage.

        Args:
            entry_id: ID des Eintrags
            is_correct: True wenn korrekt beantwortet, False sonst

        Returns:
            (True, "Saved successfully") bei Erfolg
            (False, "Entry not found") wenn ID nicht existiert
        """
        for entry in self.vocabulary:
            if entry['id'] == entry_id:
                entry['last_queried'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry['last_result'] = is_correct
                if is_correct:
                    entry['correct_count'] += 1
                else:
                    entry['wrong_count'] += 1
                return self.save()
        return False, "Entry not found"

    # === PRIVATE METHODS ===

    def _migrate_old_format(self) -> bool:
        """
        Migriert alte Vocabulary-Formate zum neuen Format mit Tracking-Feldern.

        Returns:
            True wenn Migration durchgeführt wurde, False sonst
        """
        migrated = False

        for i, entry in enumerate(self.vocabulary):
            if 'id' not in entry:
                migrated = True
                entry['id'] = i + 1

                if 'timestamp' in entry:
                    entry['created_at'] = entry['timestamp']
                    del entry['timestamp']
                elif 'created_at' not in entry:
                    entry['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if 'last_queried' not in entry:
                    entry['last_queried'] = None
                if 'last_result' not in entry:
                    entry['last_result'] = None
                if 'correct_count' not in entry:
                    entry['correct_count'] = 0
                if 'wrong_count' not in entry:
                    entry['wrong_count'] = 0

        return migrated

    def _migrate_to_language_schema(self) -> bool:
        """
        Migriert Vokabel- und Reading-Einträge zum sprachbewussten v1.1-Schema
        (REQUIREMENTS.md Section 9, REQ-MIG-01 bis REQ-MIG-04):

        - fügt 'language' hinzu (Default: 'english'), falls nicht vorhanden
        - benennt das alte Feld 'english' zu 'foreign_word' um (Vokabeln)
        - wandelt reine Integer-IDs in präfigierte String-IDs um (z.B. 5 -> 'E5'),
          basierend auf der (ggf. neu gesetzten) Sprache des Eintrags

        Returns:
            True wenn Migration durchgeführt wurde, False sonst
        """
        migrated = False

        for entry in self.vocabulary:
            if 'language' not in entry:
                entry['language'] = 'english'
                migrated = True
            if 'english' in entry:
                entry['foreign_word'] = entry.pop('english')
                migrated = True
            elif 'foreign_word' not in entry:
                entry['foreign_word'] = ''
                migrated = True
            if isinstance(entry.get('id'), int):
                prefix = self.LANGUAGE_PREFIXES.get(entry['language'], 'E')
                entry['id'] = f"{prefix}{entry['id']}"
                migrated = True

        for text in self.reading_texts:
            if 'language' not in text:
                text['language'] = 'english'
                migrated = True
            if isinstance(text.get('id'), int):
                prefix = self.LANGUAGE_PREFIXES.get(text['language'], 'E')
                text['id'] = f"{prefix}{text['id']}"
                migrated = True

        return migrated

    def _generate_vocab_id(self, language: str = 'english') -> str:
        """
        Generiert eine eindeutige, präfigierte ID für einen neuen Vokabel-Eintrag.
        Jede Sprache hat ihre eigene, unabhängige Nummerierung (REQ-MIG-06).

        Args:
            language: 'english' oder 'spanish'

        Returns:
            Neue eindeutige ID, z.B. 'E12' oder 'S4'
        """
        prefix = self.LANGUAGE_PREFIXES.get(language, 'E')
        max_id = 0
        for entry in self.vocabulary:
            entry_id = entry.get('id', '')
            if isinstance(entry_id, str) and entry_id.startswith(prefix):
                suffix = entry_id[len(prefix):]
                if suffix.isdigit():
                    max_id = max(max_id, int(suffix))
        return f"{prefix}{max_id + 1}"

    def _generate_reading_id(self, language: str = 'english') -> str:
        """
        Generiert eine eindeutige, präfigierte ID für einen neuen Reading Text.
        Jede Sprache hat ihre eigene, unabhängige Nummerierung (REQ-MIG-06).

        Args:
            language: 'english' oder 'spanish'

        Returns:
            Neue eindeutige ID, z.B. 'E3' oder 'S1'
        """
        prefix = self.LANGUAGE_PREFIXES.get(language, 'E')
        max_id = 0
        for text in self.reading_texts:
            text_id = text.get('id', '')
            if isinstance(text_id, str) and text_id.startswith(prefix):
                suffix = text_id[len(prefix):]
                if suffix.isdigit():
                    max_id = max(max_id, int(suffix))
        return f"{prefix}{max_id + 1}"


# ============================================================================
# MODULE: EMAIL
# ============================================================================
class EmailModule:
    """
    Email Module - Versendet Quiz-Ergebnisse per Email

    PUBLIC API:
    ===========
    - configure_email(sender_email: str, sender_password: str) → None
    - is_configured() → bool
    - send_quiz_results(...) → Tuple[bool, str]
    """

    def __init__(self):
        """Initialisiert das Email-Modul."""
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.sender_email: Optional[str] = None
        self.sender_password: Optional[str] = None
        self.recipient_email = Config.EMAIL_RECIPIENT

    # === PUBLIC API ===

    def configure_email(self, sender_email: str, sender_password: str) -> None:
        """
        Konfiguriert Email-Credentials.

        Args:
            sender_email: Gmail-Adresse des Senders
            sender_password: App-Passwort (nicht reguläres Passwort!)
        """
        self.sender_email = sender_email
        self.sender_password = sender_password

    def is_configured(self) -> bool:
        """
        Prüft ob Email-Credentials konfiguriert sind.

        Returns:
            True wenn Email und Passwort gesetzt sind, False sonst
        """
        return bool(self.sender_email and self.sender_password)

    def send_quiz_results(self, quiz_name: str, quiz_tested: int, quiz_wrong: int,
                         quiz_correct: int, quiz_success_rate: float,
                         overall_stats: Dict) -> Tuple[bool, str]:
        """
        Sendet Quiz-Ergebnisse per Email.

        Args:
            quiz_name: Name des Quiz
            quiz_tested: Anzahl getesteter Vokabeln
            quiz_wrong: Anzahl falscher Antworten
            quiz_correct: Anzahl korrekter Antworten
            quiz_success_rate: Erfolgsrate in Prozent
            overall_stats: Gesamtstatistiken aus get_statistics()

        Returns:
            (True, "Email sent successfully") bei Erfolg
            (False, "Error: ...") bei Fehler
        """
        if not self.is_configured():
            return False, "Email not configured. Please set credentials in Settings."

        try:
            # HTML-Email erstellen
            html_body = self._create_email_html(
                quiz_name, quiz_tested, quiz_wrong, quiz_correct,
                quiz_success_rate, overall_stats
            )

            # Email-Nachricht erstellen
            message = MIMEMultipart('alternative')
            message['Subject'] = f"📚 Vocabulary Quiz Results: {quiz_name}"
            message['From'] = self.sender_email
            message['To'] = self.recipient_email

            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)

            # Email versenden
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            return True, f"Email sent successfully to {self.recipient_email}"

        except Exception as e:
            return False, f"Failed to send email: {str(e)}"

    # === PRIVATE METHODS ===

    def _create_email_html(self, quiz_name: str, quiz_tested: int, quiz_wrong: int,
                          quiz_correct: int, quiz_success_rate: float,
                          overall_stats: Dict) -> str:
        """
        Erstellt HTML-Body für Email.
        """
        emoji = "🎉" if quiz_success_rate >= 80 else "👍" if quiz_success_rate >= 60 else "💪"

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; }}
                .stats-box {{ background-color: white; border-left: 4px solid #4CAF50; padding: 15px; margin: 10px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{emoji} Vocabulary Quiz Results</h1>
                    <h2>{quiz_name}</h2>
                </div>

                <div class="content">
                    <div class="stats-box">
                        <h3>📊 Quiz Performance</h3>
                        <p><strong>Words Tested:</strong> {quiz_tested}</p>
                        <p><strong>Correct:</strong> ✅ {quiz_correct}</p>
                        <p><strong>Wrong:</strong> ❌ {quiz_wrong}</p>
                        <p><strong>Success Rate:</strong> {quiz_success_rate:.1f}%</p>
                    </div>

                    <div class="stats-box">
                        <h3>📈 Overall Statistics</h3>
                        <p><strong>Total Vocabulary:</strong> {overall_stats['total_entries']} words</p>
                        <p><strong>Total Correct (All Time):</strong> {overall_stats['total_correct']}</p>
                        <p><strong>Total Wrong (All Time):</strong> {overall_stats['total_wrong']}</p>
                        <p><strong>Overall Success Rate:</strong> {overall_stats['success_rate']:.1f}%</p>
                    </div>
                </div>

                <div class="footer">
                    <p><em>Keep up the great work learning English vocabulary! 🎯</em></p>
                    <p>Sent from {Config.APP_NAME} v{Config.VERSION}</p>
                </div>
            </div>
        </body>
        </html>
        """


# ============================================================================
# UI WIDGET: SPECIAL CHARACTER BAR (v1.1)
# ============================================================================
class SpecialCharacterBar:
    """
    Wiederverwendbares Button-Reihe-Widget für Sonderzeichen, die auf einer
    deutschen Tastatur nicht direkt erreichbar sind (REQ-SPCHAR-01–04).

    Aktuell nur für Spanisch befüllt (á é í ó ú ñ Ñ ¿ ¡ — 'ü' ist auf einer
    deutschen Tastatur bereits vorhanden und daher ausgenommen). Der Aufbau
    ist bewusst sprachparametrisiert, damit eine dritte Sprache später
    einfach eine weitere CHARACTERS-Liste ergänzen kann, statt ein neues
    Widget zu bauen.

    Ein Klick fügt das Zeichen an der aktuellen Cursor-Position des zuletzt
    fokussierten registrierten Ziel-Entry ein (REQ-SPCHAR-03). Mehrere Ziele
    können registriert werden (z.B. das "Add"- und das "Modify"-Feld), das
    Widget merkt sich per Fokus-Tracking, welches davon aktuell gemeint ist.

    PUBLIC API:
    ===========
    - grid(**kwargs) → None                 (initiale Platzierung)
    - show() / hide() → None                 (REQ-SPCHAR-01/04)
    - register_target(entry: tk.Entry) → None
    """

    CHARACTERS = {
        'spanish': ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'Ñ', '¿', '¡'],
    }

    def __init__(self, parent: tk.Widget, language: str = 'spanish'):
        """
        Baut die Buttonreihe für die angegebene Sprache.

        Args:
            parent: Parent-Widget
            language: Sprache, deren Sonderzeichen angezeigt werden (aktuell nur 'spanish')
        """
        self.frame = ttk.Frame(parent)
        for char in self.CHARACTERS.get(language, []):
            ttk.Button(self.frame, text=char, width=2,
                      command=lambda c=char: self._insert_character(c)).pack(side=tk.LEFT, padx=1)

        self._targets: List[tk.Entry] = []
        self._active_target: Optional[tk.Entry] = None
        self._grid_kwargs: Optional[Dict] = None

    # === PUBLIC API ===

    def grid(self, **kwargs) -> None:
        """Platziert die Buttonreihe im Grid-Layout des Parents (einmalig)."""
        self._grid_kwargs = kwargs
        self.frame.grid(**kwargs)

    def show(self) -> None:
        """Blendet die Buttonreihe ein (an der zuletzt via grid() gesetzten Position)."""
        if self._grid_kwargs is not None:
            self.frame.grid(**self._grid_kwargs)

    def hide(self) -> None:
        """Blendet die Buttonreihe aus, ohne die Grid-Platzierung zu vergessen."""
        self.frame.grid_remove()

    def register_target(self, entry: tk.Entry) -> None:
        """
        Registriert ein Entry-Feld als mögliches Einfüge-Ziel. Das zuletzt
        fokussierte registrierte Feld empfängt Klicks auf die Buttons.

        Args:
            entry: Tk/ttk Entry-Widget, in das Zeichen eingefügt werden können
        """
        self._targets.append(entry)
        if self._active_target is None:
            self._active_target = entry
        entry.bind('<FocusIn>', lambda e, ent=entry: setattr(self, '_active_target', ent), add='+')

    # === PRIVATE METHODS ===

    def _insert_character(self, char: str) -> None:
        """Fügt das Zeichen an der aktuellen Cursor-Position des aktiven Ziels ein."""
        entry = self._active_target
        if entry is None:
            return
        pos = entry.index(tk.INSERT)
        entry.insert(pos, char)
        entry.icursor(pos + len(char))
        entry.focus_set()


# ============================================================================
# UI MODULE: ADD/MODIFY
# ============================================================================
class AddModifyUI:
    """
    Add/Modify UI Module - Hinzufügen und Bearbeiten von Vokabeln
    EXTENDED (v1.1): sprachbewusst — Feld-Labels und neu angelegte Einträge
    folgen der aktiven Sprache (REQ-LANG-01–03).

    PUBLIC API:
    ===========
    - get_ui(parent) → ttk.Frame
    - set_active_language(language: str) → None
    """

    def __init__(self, db: VocabularyDatabase):
        """
        Initialisiert Add/Modify-Modul.

        Args:
            db: VocabularyDatabase Instanz
        """
        self.db = db
        self.active_language = Config.DEFAULT_LANGUAGE

    # === PUBLIC API ===

    def get_ui(self, parent: tk.Widget) -> ttk.Frame:
        """
        Erstellt und gibt das UI-Widget zurück.

        Args:
            parent: Parent-Widget

        Returns:
            ttk.Frame mit Add/Modify-UI
        """
        frame = ttk.Frame(parent, padding="10")

        # Title
        title = ttk.Label(frame, text="➕ Add New Vocabulary", font=('Arial', 14, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Foreign-word input (label text depends on active language)
        self.foreign_label = ttk.Label(frame, text="English Word:")
        self.foreign_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.english_entry = ttk.Entry(frame, width=40)
        self.english_entry.grid(row=1, column=1, pady=5, padx=5)
        self.english_entry.bind('<Return>', lambda e: self.german_entry.focus())

        # Spanish special-character row (REQ-SPCHAR-01/02) — only shown while
        # Spanish is the active language; inserts into whichever of this
        # bar's registered fields last had focus
        self.add_char_bar = SpecialCharacterBar(frame)
        self.add_char_bar.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.add_char_bar.register_target(self.english_entry)

        # German input
        ttk.Label(frame, text="German Translation:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.german_entry = ttk.Entry(frame, width=40)
        self.german_entry.grid(row=3, column=1, pady=5, padx=5)
        self.german_entry.bind('<Return>', lambda e: self._add_vocabulary())

        # Add button
        add_button = ttk.Button(frame, text="➕ Add Vocabulary",
                               command=self._add_vocabulary)
        add_button.grid(row=4, column=0, columnspan=2, pady=20)

        # Separator
        ttk.Separator(frame, orient='horizontal').grid(row=5, column=0, columnspan=2,
                                                       sticky='ew', pady=20)

        # Modify section
        modify_title = ttk.Label(frame, text="✏️ Modify Existing Vocabulary",
                                font=('Arial', 14, 'bold'))
        modify_title.grid(row=6, column=0, columnspan=2, pady=(0, 20))

        # ID input for modify
        ttk.Label(frame, text="Entry ID:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.modify_id_entry = ttk.Entry(frame, width=40)
        self.modify_id_entry.grid(row=7, column=1, pady=5, padx=5)
        self.modify_id_entry.bind('<Return>', lambda e: self._load_entry())

        # Load button
        load_button = ttk.Button(frame, text="🔍 Load Entry",
                                command=self._load_entry)
        load_button.grid(row=8, column=0, columnspan=2, pady=10)

        # Modify foreign word (label text depends on active language)
        self.modify_foreign_label = ttk.Label(frame, text="New English:")
        self.modify_foreign_label.grid(row=9, column=0, sticky=tk.W, pady=5)
        self.modify_english_entry = ttk.Entry(frame, width=40)
        self.modify_english_entry.grid(row=9, column=1, pady=5, padx=5)
        self.modify_english_entry.bind('<Return>', lambda e: self.modify_german_entry.focus())

        # Spanish special-character row for the Modify field
        self.modify_char_bar = SpecialCharacterBar(frame)
        self.modify_char_bar.grid(row=10, column=1, sticky=tk.W, padx=5)
        self.modify_char_bar.register_target(self.modify_english_entry)

        # Modify German
        ttk.Label(frame, text="New German:").grid(row=11, column=0, sticky=tk.W, pady=5)
        self.modify_german_entry = ttk.Entry(frame, width=40)
        self.modify_german_entry.grid(row=11, column=1, pady=5, padx=5)
        self.modify_german_entry.bind('<Return>', lambda e: self._modify_vocabulary())

        # Modify and Delete buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="💾 Save Changes",
                  command=self._modify_vocabulary).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Delete Entry",
                  command=self._delete_vocabulary).pack(side=tk.LEFT, padx=5)

        self._apply_language_labels()

        return frame

    def set_active_language(self, language: str) -> None:
        """
        Wechselt die aktive Sprache (REQ-LANG-01/02/03).
        Aktualisiert Feld-Labels und leert offene Eingaben, damit kein
        halb getipptes Wort der falschen Sprache versehentlich gespeichert wird.

        Args:
            language: 'english' oder 'spanish'
        """
        self.active_language = language
        self._apply_language_labels()
        self.english_entry.delete(0, tk.END)
        self.german_entry.delete(0, tk.END)
        self.modify_id_entry.delete(0, tk.END)
        self.modify_english_entry.delete(0, tk.END)
        self.modify_german_entry.delete(0, tk.END)

    # === PRIVATE METHODS ===

    def _apply_language_labels(self) -> None:
        """Aktualisiert Feld-Labels und Sonderzeichen-Leisten entsprechend der aktiven Sprache."""
        label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language.title())
        self.foreign_label.config(text=f"{label} Word:")
        self.modify_foreign_label.config(text=f"New {label}:")

        # REQ-SPCHAR-01/04: nur bei aktiver Sprache Spanisch sichtbar
        if self.active_language == 'spanish':
            self.add_char_bar.show()
            self.modify_char_bar.show()
        else:
            self.add_char_bar.hide()
            self.modify_char_bar.hide()

    # === PRIVATE METHODS - Event Handlers ===

    def _add_vocabulary(self) -> None:
        """Fügt neue Vokabel hinzu (in der aktuell aktiven Sprache)."""
        foreign_word = self.english_entry.get().strip()
        german = self.german_entry.get().strip()

        if not foreign_word or not german:
            messagebox.showwarning("⚠️ Warning", "Please fill in both fields")
            return

        success, msg = self.db.add_entry(foreign_word, german, language=self.active_language)

        if success:
            messagebox.showinfo("✅ Success", f"Added: {foreign_word} → {german}")
            self.english_entry.delete(0, tk.END)
            self.german_entry.delete(0, tk.END)
            self.english_entry.focus()
        else:
            messagebox.showerror("❌ Error", msg)

    def _load_entry(self) -> None:
        """Lädt Eintrag zum Bearbeiten (muss zur aktiven Sprache gehören)."""
        entry_id = self.modify_id_entry.get().strip()
        if not entry_id:
            messagebox.showwarning("⚠️ Warning", "Please enter an Entry ID (e.g. 'E3')")
            return

        entry = self.db.get_entry_by_id(entry_id)

        if not entry:
            messagebox.showerror("❌ Error", f"Entry #{entry_id} not found")
            return

        if entry['language'] != self.active_language:
            active_label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language)
            entry_label = Config.LANGUAGE_LABELS.get(entry['language'], entry['language'])
            messagebox.showerror(
                "❌ Error",
                f"Entry #{entry_id} belongs to {entry_label}, not {active_label}.\n\n"
                f"Switch the active language first."
            )
            return

        self.modify_english_entry.delete(0, tk.END)
        self.modify_english_entry.insert(0, entry['foreign_word'])
        self.modify_german_entry.delete(0, tk.END)
        self.modify_german_entry.insert(0, entry['german'])
        messagebox.showinfo("✅ Loaded", f"Loaded entry #{entry_id}")
        self.modify_english_entry.focus()

    def _modify_vocabulary(self) -> None:
        """Ändert existierenden Eintrag (muss zur aktiven Sprache gehören)."""
        entry_id = self.modify_id_entry.get().strip()
        foreign_word = self.modify_english_entry.get().strip()
        german = self.modify_german_entry.get().strip()

        if not entry_id:
            messagebox.showwarning("⚠️ Warning", "Please enter an Entry ID (e.g. 'E3')")
            return

        if not foreign_word or not german:
            messagebox.showwarning("⚠️ Warning", "Please fill in both fields")
            return

        entry = self.db.get_entry_by_id(entry_id)
        if entry and entry['language'] != self.active_language:
            active_label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language)
            entry_label = Config.LANGUAGE_LABELS.get(entry['language'], entry['language'])
            messagebox.showerror(
                "❌ Error",
                f"Entry #{entry_id} belongs to {entry_label}, not {active_label}.\n\n"
                f"Switch the active language first."
            )
            return

        success, msg = self.db.update_entry(entry_id, foreign_word, german)

        if success:
            messagebox.showinfo("✅ Success", f"Modified entry #{entry_id}")
        else:
            messagebox.showerror("❌ Error", msg)

    def _delete_vocabulary(self) -> None:
        """Löscht Eintrag (muss zur aktiven Sprache gehören)."""
        entry_id = self.modify_id_entry.get().strip()
        if not entry_id:
            messagebox.showwarning("⚠️ Warning", "Please enter an Entry ID (e.g. 'E3')")
            return

        entry = self.db.get_entry_by_id(entry_id)
        if entry and entry['language'] != self.active_language:
            active_label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language)
            entry_label = Config.LANGUAGE_LABELS.get(entry['language'], entry['language'])
            messagebox.showerror(
                "❌ Error",
                f"Entry #{entry_id} belongs to {entry_label}, not {active_label}.\n\n"
                f"Switch the active language first."
            )
            return

        confirm = messagebox.askyesno("⚠️ Confirm Delete",
                                     f"Are you sure you want to delete entry #{entry_id}?")
        if not confirm:
            return

        success, msg = self.db.delete_entry(entry_id)

        if success:
            messagebox.showinfo("✅ Success", f"Deleted entry #{entry_id}")
            self.modify_id_entry.delete(0, tk.END)
            self.modify_english_entry.delete(0, tk.END)
            self.modify_german_entry.delete(0, tk.END)
        else:
            messagebox.showerror("❌ Error", msg)


# ============================================================================
# UI MODULE: QUIZ
# ============================================================================
class QuizUI:
    """
    Quiz UI Module - Quiz-Funktionalität mit verschiedenen Modi
    EXTENDED (v1.1): sprachbewusst — der Vokabel-Pool jedes Quiz-Modus ist
    auf die aktive Sprache beschränkt (REQ-LANG-02).

    PUBLIC API:
    ===========
    - get_ui(parent) → ttk.Frame
    - set_active_language(language: str) → None
    """

    def __init__(self, db: VocabularyDatabase,
                 notification_callback: Optional[Callable[[Dict], None]] = None):
        """
        Initialisiert Quiz-Modul.

        Args:
            db: VocabularyDatabase Instanz
            notification_callback: Optional callback für Quiz-Ergebnisse
        """
        self.db = db
        self.notification_callback = notification_callback
        self.active_language = Config.DEFAULT_LANGUAGE

        # Quiz state
        self.quiz_entries: List[Dict] = []
        self.current_index = 0
        self.quiz_results: List[bool] = []
        self.quiz_mode = ""

    # === PUBLIC API ===

    def get_ui(self, parent: tk.Widget) -> ttk.Frame:
        """
        Erstellt und gibt das UI-Widget zurück.

        Args:
            parent: Parent-Widget

        Returns:
            ttk.Frame mit Quiz-UI
        """
        frame = ttk.Frame(parent, padding="10")

        # Title
        title = ttk.Label(frame, text="🧠 Vocabulary Quiz", font=('Arial', 14, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Quiz mode buttons - Row 1
        ttk.Button(frame, text="📚 Quiz: Last 10 Words",
                  command=lambda: self._start_quiz("Last 10")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(frame, text="📖 Quiz: Last 30 Words",
                  command=lambda: self._start_quiz("Last 30")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="🎲 Quiz: Random 30 Words",
                  command=lambda: self._start_quiz("Random 30")).grid(row=1, column=2, padx=5, pady=5)

        # Quiz mode buttons - Row 2
        ttk.Button(frame, text="❌ Quiz: Incorrect Only",
                  command=lambda: self._start_quiz("Incorrect")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(frame, text="📅 Quiz: Today's Words",
                  command=lambda: self._start_quiz("Today")).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame, text="🆕 Quiz: Never tested Words",
                  command=lambda: self._start_quiz("Never Tested")).grid(row=2, column=2, padx=5, pady=5)

        # Quiz container
        self.quiz_container = ttk.Frame(frame)
        self.quiz_container.grid(row=3, column=0, columnspan=3, pady=20)

        # Question label
        self.question_label = ttk.Label(self.quiz_container, text="",
                                       font=('Arial', 16, 'bold'))
        self.question_label.grid(row=0, column=0, pady=20)

        # Answer entry
        self.answer_entry = ttk.Entry(self.quiz_container, width=40, font=('Arial', 12))
        self.answer_entry.grid(row=1, column=0, pady=10)
        self.answer_entry.bind('<Return>', lambda e: self._submit_answer())

        # Spanish special-character row (REQ-SPCHAR-01/02) — only shown while
        # a Spanish quiz is active, since the answer must be typed here
        self.char_bar = SpecialCharacterBar(self.quiz_container)
        self.char_bar.grid(row=2, column=0)
        self.char_bar.register_target(self.answer_entry)

        # Submit button
        self.submit_button = ttk.Button(self.quiz_container, text="✅ Submit Answer",
                                       command=self._submit_answer)
        self.submit_button.grid(row=3, column=0, pady=10)

        # Progress label
        self.progress_label = ttk.Label(self.quiz_container, text="", font=('Arial', 10))
        self.progress_label.grid(row=4, column=0, pady=5)

        # Result text area
        self.result_text = scrolledtext.ScrolledText(frame, width=80, height=15,
                                                     font=('Arial', 10))
        self.result_text.grid(row=4, column=0, columnspan=3, pady=20)

        self._hide_quiz_ui()

        return frame

    def set_active_language(self, language: str) -> None:
        """
        Wechselt die aktive Sprache (REQ-LANG-01/02).
        Ein laufendes Quiz wird dabei abgebrochen, um keine Fragen aus der
        vorherigen Sprache stehen zu lassen.

        Args:
            language: 'english' oder 'spanish'
        """
        self.active_language = language
        self.quiz_entries = []
        self.current_index = 0
        self.quiz_results = []
        self._hide_quiz_ui()
        self.result_text.delete('1.0', tk.END)

    # === PRIVATE METHODS - Quiz Logic ===

    def _start_quiz(self, mode: str) -> None:
        """Startet Quiz im gewählten Modus, beschränkt auf die aktive Sprache."""
        self.current_index = 0
        self.quiz_results = []
        language = self.active_language

        # Get entries based on mode
        if mode == "Last 10":
            self.quiz_entries = self.db.get_recent_entries(10, language=language)
        elif mode == "Last 30":
            self.quiz_entries = self.db.get_recent_entries(30, language=language)
        elif mode == "Random 30":
            all_entries = self.db.get_all_entries(language=language)
            filtered_entries = [e for e in all_entries if e.get('correct_count', 0) < 5]

            if len(filtered_entries) == 0:
                messagebox.showinfo("🎉 Congratulations!",
                                  "All vocabulary words have been answered correctly 5+ times!\n\n"
                                  "You've mastered your vocabulary!")
                return
            elif len(filtered_entries) < 30:
                messagebox.showinfo("ℹ️ Info",
                                  f"Only {len(filtered_entries)} words with less than 5 correct answers available.\n"
                                  f"Quiz will include all of them.")
                self.quiz_entries = filtered_entries
            else:
                self.quiz_entries = random.sample(filtered_entries, 30)
        elif mode == "Incorrect":
            self.quiz_entries = self.db.get_incorrect_entries(language=language)
        elif mode == "Today":
            today = datetime.now().strftime("%Y-%m-%d")
            self.quiz_entries = self.db.get_entries_by_date(today, language=language)
        elif mode == "Never Tested":
            self.quiz_entries = self.db.get_never_tested_entries(language=language)

        if not self.quiz_entries:
            messagebox.showinfo("ℹ️ Info", f"No vocabulary entries available for '{mode}' mode.")
            return

        # Display name includes the active language (also flows into the
        # quiz-result email subject via notification_callback — REQ-LANG-05)
        language_label = Config.LANGUAGE_LABELS.get(language, language.title())
        self.quiz_mode = f"{language_label} - {mode}"

        random.shuffle(self.quiz_entries)
        self._show_quiz_ui()
        self._show_question()

    def _show_question(self) -> None:
        """Zeigt aktuelle Frage an."""
        if self.current_index < len(self.quiz_entries):
            entry = self.quiz_entries[self.current_index]
            self.question_label.config(text=f"Translate: {entry['german']}")
            self.answer_entry.delete(0, tk.END)
            self.answer_entry.focus()
            self.progress_label.config(
                text=f"Question {self.current_index + 1} of {len(self.quiz_entries)}"
            )
        else:
            self._finish_quiz()

    def _submit_answer(self) -> None:
        """Verarbeitet eingegebene Antwort."""
        if self.current_index >= len(self.quiz_entries):
            return

        entry = self.quiz_entries[self.current_index]
        user_answer = normalize_text(self.answer_entry.get().strip().lower())  # REQ-NF-07
        correct_answer = entry['foreign_word'].lower()

        is_correct = user_answer == correct_answer
        self.quiz_results.append(is_correct)

        self.db.record_quiz_result(entry['id'], is_correct)

        if is_correct:
            self._show_large_message("✅ Correct!",
                                    f"'{entry['foreign_word']}' is correct!",
                                    "green")
        else:
            self._show_large_message("❌ Wrong",
                                    f"Correct answer: '{entry['foreign_word']}'\n\nYour answer: '{user_answer}'",
                                    "red")

        self.current_index += 1
        self._show_question()

    def _show_large_message(self, title: str, message: str, color: str) -> None:
        """Zeigt eine Nachricht mit großer Schrift."""
        dialog = tk.Toplevel()
        dialog.title(title)
        dialog.transient()
        dialog.grab_set()
        dialog.geometry("500x250")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(frame, text=title,
                              font=('Arial', 20, 'bold'),
                              fg=color)
        title_label.pack(pady=(0, 20))

        message_label = tk.Label(frame, text=message,
                                font=('Arial', 16),
                                justify=tk.CENTER,
                                wraplength=450)
        message_label.pack(pady=10)

        ok_button = ttk.Button(frame, text="OK",
                              command=dialog.destroy)
        ok_button.pack(pady=(20, 0))
        ok_button.focus()

        dialog.bind('<Return>', lambda e: dialog.destroy())

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.wait_window()

    def _finish_quiz(self) -> None:
        """Beendet Quiz und zeigt Ergebnisse."""
        self._hide_quiz_ui()

        correct = sum(self.quiz_results)
        wrong = len(self.quiz_results) - correct
        success_rate = (correct / len(self.quiz_results) * 100) if self.quiz_results else 0

        overall_stats = self.db.get_statistics(language=self.active_language)

        result_text = f"""
{'='*60}
QUIZ RESULTS - {self.quiz_mode}
{'='*60}

Questions Tested: {len(self.quiz_results)}
Correct Answers: ✅ {correct}
Wrong Answers: ❌ {wrong}
Success Rate: {success_rate:.1f}%

{'='*60}
OVERALL STATISTICS
{'='*60}

Total Vocabulary: {overall_stats['total_entries']} words
Total Correct (All Time): {overall_stats['total_correct']}
Total Wrong (All Time): {overall_stats['total_wrong']}
Overall Success Rate: {overall_stats['success_rate']:.1f}%

{'='*60}
"""

        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', result_text)

        if self.notification_callback:
            self.notification_callback({
                'quiz_name': self.quiz_mode,
                'quiz_tested': len(self.quiz_results),
                'quiz_correct': correct,
                'quiz_wrong': wrong,
                'quiz_success_rate': success_rate,
                'overall_stats': overall_stats
            })

    def _show_quiz_ui(self) -> None:
        """Zeigt Quiz-UI-Elemente."""
        self.question_label.grid()
        self.answer_entry.grid()
        if self.active_language == 'spanish':  # REQ-SPCHAR-01/04
            self.char_bar.show()
        self.submit_button.grid()
        self.progress_label.grid()

    def _hide_quiz_ui(self) -> None:
        """Versteckt Quiz-UI-Elemente."""
        self.question_label.grid_remove()
        self.answer_entry.grid_remove()
        self.char_bar.hide()
        self.submit_button.grid_remove()
        self.progress_label.grid_remove()


# ============================================================================
# UI MODULE: LIST
# ============================================================================
class ListUI:
    """
    List UI Module - Anzeige und Verwaltung der Vokabelliste
    EXTENDED (v1.1): sprachbewusst — Liste, Suche, Doublets, Statistik und
    CSV-Export sind auf die aktive Sprache beschränkt (REQ-LANG-02/04).

    PUBLIC API:
    ===========
    - get_ui(parent) → ttk.Frame
    - set_active_language(language: str) → None
    """

    def __init__(self, db: VocabularyDatabase):
        """
        Initialisiert List-Modul.

        Args:
            db: VocabularyDatabase Instanz
        """
        self.db = db
        self.active_language = Config.DEFAULT_LANGUAGE

    # === PUBLIC API ===

    def get_ui(self, parent: tk.Widget) -> ttk.Frame:
        """
        Erstellt und gibt das UI-Widget zurück.
        """
        frame = ttk.Frame(parent, padding="10")

        # Title and buttons
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        self.title_label = ttk.Label(title_frame, text="📜 Vocabulary List",
                 font=('Arial', 14, 'bold'))
        self.title_label.pack(side=tk.LEFT)

        ttk.Button(title_frame, text="🔄 Refresh List",
                  command=self._refresh_list).pack(side=tk.RIGHT, padx=5)
        ttk.Button(title_frame, text="📊 Show Statistics",
                  command=self._show_statistics).pack(side=tk.RIGHT, padx=5)
        ttk.Button(title_frame, text="🔍 Find Doublets",
                  command=self._find_doublets).pack(side=tk.RIGHT, padx=5)
        ttk.Button(title_frame, text="💾 Export to CSV",
                  command=self._export_to_csv).pack(side=tk.RIGHT, padx=5)

        # Search frame
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="🔍 Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self._search_vocabulary())

        ttk.Button(search_frame, text="🔍 Search",
                  command=self._search_vocabulary).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="✖️ Clear Search",
                  command=self._clear_search).pack(side=tk.LEFT, padx=5)

        # Treeview
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ('ID', 'English', 'German', 'Last', 'Date', 'C/W')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set)

        self.tree.heading('ID', text='ID')
        self.tree.heading('English', text='English')
        self.tree.heading('German', text='German')
        self.tree.heading('Last', text='Last Result')
        self.tree.heading('Date', text='Last Quiz')
        self.tree.heading('C/W', text='Correct/Wrong')

        self.tree.column('ID', width=50)
        self.tree.column('English', width=200)
        self.tree.column('German', width=200)
        self.tree.column('Last', width=80)
        self.tree.column('Date', width=100)
        self.tree.column('C/W', width=100)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)

        self.tree.tag_configure('doublet', background='#ffcccc', foreground='#cc0000')
        self.tree.tag_configure('search_result', background='#ffffcc')

        self._apply_language_labels()
        self._refresh_list()

        return frame

    def set_active_language(self, language: str) -> None:
        """
        Wechselt die aktive Sprache (REQ-LANG-01/02).
        Setzt die Suche zurück und lädt die Liste für die neue Sprache neu.

        Args:
            language: 'english' oder 'spanish'
        """
        self.active_language = language
        self.search_entry.delete(0, tk.END)
        self._apply_language_labels()
        self._refresh_list()

    # === PRIVATE METHODS ===

    def _apply_language_labels(self) -> None:
        """Aktualisiert Titel und Spaltenüberschrift entsprechend der aktiven Sprache."""
        label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language.title())
        self.title_label.config(text=f"📜 Vocabulary List — {label}")
        self.tree.heading('English', text=label)

    def _export_to_csv(self) -> None:
        """Exportiert die Vokabeldatenbank der aktiven Sprache als CSV-Datei."""
        import csv

        language = self.active_language
        language_label = Config.LANGUAGE_LABELS.get(language, language.title())

        # Get entries for the active language only (REQ-LANG-04)
        entries = self.db.get_all_entries(language=language)

        if not entries:
            messagebox.showwarning("⚠️ Warning", f"No {language_label} vocabulary entries to export!")
            return

        # Ask for filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"vocabulary_export_{language}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not filename:
            return

        try:
            # Write CSV file
            with open(filename, 'w', encoding='utf-8', newline='') as csvfile:
                # Define CSV columns (column header reflects the active language)
                fieldnames = [
                    'ID',
                    language_label,
                    'German',
                    'Created At',
                    'Last Queried',
                    'Last Result',
                    'Correct Count',
                    'Wrong Count',
                    'Success Rate (%)'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')

                # Write header
                writer.writeheader()

                # Write data (chronological order; IDs are prefixed strings and
                # don't sort correctly as plain text, so sort by creation time instead)
                for entry in sorted(entries, key=lambda x: x.get('created_at', '')):
                    # Calculate success rate
                    correct = entry.get('correct_count', 0)
                    wrong = entry.get('wrong_count', 0)
                    total = correct + wrong
                    success_rate = (correct / total * 100) if total > 0 else 0

                    # Format last result
                    last_result = entry.get('last_result')
                    if last_result is True:
                        last_result_str = 'Correct'
                    elif last_result is False:
                        last_result_str = 'Wrong'
                    else:
                        last_result_str = 'Never tested'

                    # Write row
                    writer.writerow({
                        'ID': entry.get('id', ''),
                        language_label: entry.get('foreign_word', ''),
                        'German': entry.get('german', ''),
                        'Created At': entry.get('created_at', ''),
                        'Last Queried': entry.get('last_queried', 'Never'),
                        'Last Result': last_result_str,
                        'Correct Count': correct,
                        'Wrong Count': wrong,
                        'Success Rate (%)': f"{success_rate:.1f}"
                    })

            messagebox.showinfo("✅ Success",
                              f"Exported {len(entries)} {language_label} vocabulary entries to:\n\n{filename}\n\n"
                              f"Format: CSV with semicolon delimiter\nEncoding: UTF-8")

        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to export CSV:\n\n{e}")

    def _refresh_list(self) -> None:
        """Aktualisiert die Vokabelliste (nur aktive Sprache)."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        entries = self.db.get_all_entries(language=self.active_language)

        if not entries:
            return

        # IDs are prefixed strings and don't sort correctly as plain text
        # ("E10" < "E2" lexicographically), so use creation time for "newest first" instead
        entries_sorted = sorted(entries, key=lambda x: x.get('created_at', ''), reverse=True)

        for entry in entries_sorted:
            last_result = "✅" if entry.get('last_result') == True else \
                         "❌" if entry.get('last_result') == False else "➖"

            last_quiz = entry.get('last_queried', 'Never')
            if last_quiz and last_quiz != 'Never':
                last_quiz = last_quiz[:10]

            cw = f"{entry.get('correct_count', 0)}/{entry.get('wrong_count', 0)}"

            self.tree.insert('', tk.END, values=(
                entry.get('id'),
                entry['foreign_word'],
                entry['german'],
                last_result,
                last_quiz,
                cw
            ))

    def _search_vocabulary(self) -> None:
        """Sucht nach Vokabeln."""
        search_term = normalize_text(self.search_entry.get().strip().lower())  # REQ-NF-07

        if not search_term:
            messagebox.showwarning("⚠️ Warning", "Please enter a search term")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        all_entries = self.db.get_all_entries(language=self.active_language)

        matching_entries = []
        for entry in all_entries:
            foreign_word = entry['foreign_word'].lower()
            german = entry['german'].lower()

            if search_term in foreign_word or search_term in german:
                matching_entries.append(entry)

        if not matching_entries:
            messagebox.showinfo("ℹ️ No Results",
                              f"No vocabulary found matching '{search_term}'")
            return

        matching_entries_sorted = sorted(matching_entries, key=lambda x: x.get('created_at', ''), reverse=True)

        for entry in matching_entries_sorted:
            last_result = "✅" if entry.get('last_result') == True else \
                         "❌" if entry.get('last_result') == False else "➖"

            last_quiz = entry.get('last_queried', 'Never')
            if last_quiz and last_quiz != 'Never':
                last_quiz = last_quiz[:10]

            cw = f"{entry.get('correct_count', 0)}/{entry.get('wrong_count', 0)}"

            item_id = self.tree.insert('', tk.END, values=(
                entry.get('id'),
                entry['foreign_word'],
                entry['german'],
                last_result,
                last_quiz,
                cw
            ), tags=('search_result',))

        messagebox.showinfo("🔍 Search Results",
                          f"Found {len(matching_entries)} matching vocabulary word(s)")

    def _clear_search(self) -> None:
        """Löscht Suchfeld."""
        self.search_entry.delete(0, tk.END)
        self._refresh_list()

    def _show_statistics(self) -> None:
        """Zeigt Statistik-Dialog (nur aktive Sprache)."""
        stats = self.db.get_statistics(language=self.active_language)
        incorrect_count = len(self.db.get_incorrect_entries(language=self.active_language))

        entries_with_attempts = [e for e in self.db.get_all_entries(language=self.active_language)
                                if (e.get('correct_count', 0) + e.get('wrong_count', 0)) > 0]

        difficult_words_text = ""
        if entries_with_attempts:
            difficult = sorted(entries_with_attempts,
                             key=lambda x: x.get('wrong_count', 0) / (x.get('correct_count', 0) + x.get('wrong_count', 0)),
                             reverse=True)[:5]

            difficult_words_text = "\nMOST DIFFICULT WORDS:\n"
            for entry in difficult:
                total = entry.get('correct_count', 0) + entry.get('wrong_count', 0)
                error_rate = entry.get('wrong_count', 0) / total * 100
                last_icon = "✅" if entry.get('last_result') else "❌" if entry.get('last_result') is False else "➖"
                difficult_words_text += f"  {last_icon} {entry['foreign_word']}/{entry['german']}: {error_rate:.0f}% errors ({entry.get('wrong_count', 0)}/{total})\n"

        stats_text = f"""
📊 VOCABULARY STATISTICS

OVERVIEW:
  Total entries: {stats['total_entries']}
  Queried entries: {stats['queried_entries']}
  Never queried: {stats['never_queried']}

QUIZ PERFORMANCE:
  Total correct answers: {stats['total_correct']}
  Total wrong answers: {stats['total_wrong']}
  Overall success rate: {stats['success_rate']:.1f}%

  Words with last answer WRONG: {incorrect_count}
{difficult_words_text}
"""

        messagebox.showinfo("📊 Statistics", stats_text)

    def _find_doublets(self) -> None:
        """Findet und markiert doppelte Vokabeln (nur aktive Sprache)."""
        all_entries = self.db.get_all_entries(language=self.active_language)

        foreign_words = {}
        for entry in all_entries:
            foreign_word = entry['foreign_word'].lower().strip()
            if foreign_word not in foreign_words:
                foreign_words[foreign_word] = []
            foreign_words[foreign_word].append(entry['id'])

        doublets = {word: ids for word, ids in foreign_words.items() if len(ids) > 1}
        doublet_ids = set()
        for ids in doublets.values():
            doublet_ids.update(ids)

        self._refresh_list()

        if doublet_ids:
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                # IDs are strings (e.g. 'E5') — Tkinter Treeview already returns
                # them as strings, so compare directly, no int() conversion
                if values and values[0] in doublet_ids:
                    self.tree.item(item, tags=('doublet',))

            doublet_info = "\n".join([f"  • '{word}' ({len(ids)}x): IDs {', '.join(map(str, ids))}"
                                      for word, ids in sorted(doublets.items())])
            messagebox.showwarning("🔍 Doublets Found",
                                 f"Found {len(doublets)} duplicate English word(s):\n\n{doublet_info}\n\n"
                                 f"Highlighted {len(doublet_ids)} entries in red.")
        else:
            messagebox.showinfo("✅ No Doublets",
                              "No duplicate English words found!\nAll vocabulary entries are unique.")

# ============================================================================
# UI MODULE: READING (NEW)
# ============================================================================
class ReadingUI:
    """
    Reading UI Module - Lesetexte mit Vokabel-Highlighting
    EXTENDED (v1.1): sprachbewusst — Textliste, Hochladen und Vokabel-Matching
    sind auf die aktive Sprache beschränkt (REQ-LANG-02/03).

    PUBLIC API:
    ===========
    - get_ui(parent) → ttk.Frame
    - set_active_language(language: str) → None
    """

    def __init__(self, db: VocabularyDatabase):
        """
        Initialisiert Reading-Modul.

        Args:
            db: VocabularyDatabase Instanz
        """
        self.db = db
        self.current_text_id: Optional[str] = None
        self.active_language = Config.DEFAULT_LANGUAGE

    # === PUBLIC API ===

    def get_ui(self, parent: tk.Widget) -> ttk.Frame:
        """
        Erstellt und gibt das UI-Widget zurück.

        Args:
            parent: Parent-Widget

        Returns:
            ttk.Frame mit Reading-UI
        """
        frame = ttk.Frame(parent, padding="10")

        # Title and controls
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        self.title_label = ttk.Label(title_frame, text="📖 Reading Texts",
                 font=('Arial', 14, 'bold'))
        self.title_label.pack(side=tk.LEFT)

        ttk.Button(title_frame, text="📤 Upload Text File",
                  command=self._upload_text).pack(side=tk.RIGHT, padx=5)
        ttk.Button(title_frame, text="🔄 Refresh",
                  command=self._refresh_text_list).pack(side=tk.RIGHT, padx=5)
        ttk.Button(title_frame, text="📊 Statistics",
                  command=self._show_reading_statistics).pack(side=tk.RIGHT, padx=5)

        # Text list frame
        list_frame = ttk.LabelFrame(frame, text="Available Texts", padding="5")
        list_frame.pack(fill=tk.X, pady=(0, 10))

        # Text listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.X)

        list_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_listbox = tk.Listbox(list_container, height=6,
                                       yscrollcommand=list_scrollbar.set)
        self.text_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.text_listbox.yview)

        self.text_listbox.bind('<<ListboxSelect>>', self._on_text_selected)

        # Buttons for text management
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(button_frame, text="👁️ View Selected",
                  command=self._view_selected_text).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑️ Delete Selected",
                  command=self._delete_selected_text).pack(side=tk.LEFT, padx=2)

        # Text display frame
        display_frame = ttk.LabelFrame(frame, text="Text Viewer", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Info label
        self.info_label = ttk.Label(display_frame, text="", font=('Arial', 9))
        self.info_label.pack(fill=tk.X, pady=(0, 5))

        # Text widget with scrollbar
        text_container = ttk.Frame(display_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        text_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_display = tk.Text(text_container, wrap=tk.WORD,
                                    font=('Arial', 11),
                                    yscrollcommand=text_scrollbar.set)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.config(command=self.text_display.yview)

        # Configure tags for highlighting
        self.text_display.tag_configure('vocab', background='#90EE90',
                                       font=('Arial', 11, 'bold'))

        # Legend
        legend_frame = ttk.Frame(display_frame)
        legend_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(legend_frame, text="Legend:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        legend_text = tk.Text(legend_frame, height=1, width=20, font=('Arial', 9))
        legend_text.pack(side=tk.LEFT)
        legend_text.insert('1.0', 'highlighted')
        legend_text.tag_add('vocab', '1.0', '1.11')
        legend_text.tag_configure('vocab', background='#90EE90', font=('Arial', 9, 'bold'))
        legend_text.config(state=tk.DISABLED)
        ttk.Label(legend_frame, text="= vocabulary word", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)

        # Initial load
        self._apply_language_labels()
        self._refresh_text_list()

        return frame

    def set_active_language(self, language: str) -> None:
        """
        Wechselt die aktive Sprache (REQ-LANG-01/02).
        Leert den Text-Viewer und lädt die Textliste für die neue Sprache neu.

        Args:
            language: 'english' oder 'spanish'
        """
        self.active_language = language
        self.current_text_id = None
        self._apply_language_labels()
        self._refresh_text_list()

        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete('1.0', tk.END)
        self.text_display.config(state=tk.DISABLED)
        self.info_label.config(text="")

    # === PRIVATE METHODS ===

    def _apply_language_labels(self) -> None:
        """Aktualisiert den Titel entsprechend der aktiven Sprache."""
        label = Config.LANGUAGE_LABELS.get(self.active_language, self.active_language.title())
        self.title_label.config(text=f"📖 Reading Texts — {label}")

    def _upload_text(self) -> None:
        """Lädt eine Text-Datei hoch."""
        filename = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:
            # Read file
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                messagebox.showwarning("⚠️ Warning", "The file is empty!")
                return

            # Ask for title
            title = os.path.basename(filename)
            title_dialog = tk.Toplevel()
            title_dialog.title("Enter Title")
            title_dialog.geometry("400x150")
            title_dialog.transient()
            title_dialog.grab_set()

            ttk.Label(title_dialog, text="Enter a title for this text:",
                     font=('Arial', 10)).pack(pady=10)

            title_entry = ttk.Entry(title_dialog, width=50)
            title_entry.insert(0, title)
            title_entry.pack(pady=10)
            title_entry.focus()
            title_entry.select_range(0, tk.END)

            result = {'confirmed': False, 'title': title}

            def confirm():
                result['confirmed'] = True
                result['title'] = title_entry.get().strip()
                title_dialog.destroy()

            def cancel():
                title_dialog.destroy()

            button_frame = ttk.Frame(title_dialog)
            button_frame.pack(pady=10)

            ttk.Button(button_frame, text="✅ OK", command=confirm).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="❌ Cancel", command=cancel).pack(side=tk.LEFT, padx=5)

            title_entry.bind('<Return>', lambda e: confirm())
            title_entry.bind('<Escape>', lambda e: cancel())

            # Center dialog
            title_dialog.update_idletasks()
            x = (title_dialog.winfo_screenwidth() // 2) - (title_dialog.winfo_width() // 2)
            y = (title_dialog.winfo_screenheight() // 2) - (title_dialog.winfo_height() // 2)
            title_dialog.geometry(f"+{x}+{y}")

            title_dialog.wait_window()

            if not result['confirmed'] or not result['title']:
                return

            # Save to database (tagged with the active language)
            success, msg = self.db.add_reading_text(result['title'], content,
                                                     language=self.active_language)

            if success:
                messagebox.showinfo("✅ Success",
                                  f"Text '{result['title']}' uploaded successfully!\n\n"
                                  f"Words: {len(content.split())}")
                self._refresh_text_list()
            else:
                messagebox.showerror("❌ Error", f"Failed to save text:\n{msg}")

        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to read file:\n{e}")

    def _refresh_text_list(self) -> None:
        """Aktualisiert die Liste der Texte (nur aktive Sprache)."""
        self.text_listbox.delete(0, tk.END)

        texts = self.db.get_all_reading_texts(language=self.active_language)

        if not texts:
            self.text_listbox.insert(tk.END, "No texts uploaded yet")
            return

        # Sort by upload date (newest first)
        texts_sorted = sorted(texts, key=lambda x: x.get('uploaded_at', ''), reverse=True)

        for text in texts_sorted:
            display_text = f"ID {text['id']}: {text['title']} ({text['word_count']} words, {text['vocabulary_matches']} vocab)"
            self.text_listbox.insert(tk.END, display_text)

    def _on_text_selected(self, event) -> None:
        """
        Wird aufgerufen wenn ein Text in der Liste ausgewählt wird.
        Muss dieselbe sprachgefilterte + sortierte Liste verwenden wie
        _refresh_text_list(), sonst zeigt die Listbox-Auswahl (Index) auf
        den falschen Text, sobald Texte beider Sprachen existieren.
        """
        selection = self.text_listbox.curselection()
        if not selection:
            return

        texts = self.db.get_all_reading_texts(language=self.active_language)
        if not texts or selection[0] >= len(texts):
            return

        # Get selected text ID
        texts_sorted = sorted(texts, key=lambda x: x.get('uploaded_at', ''), reverse=True)
        selected_text = texts_sorted[selection[0]]
        self.current_text_id = selected_text['id']

    def _view_selected_text(self) -> None:
        """Zeigt den ausgewählten Text mit Highlighting an."""
        if self.current_text_id is None:
            messagebox.showwarning("⚠️ Warning", "Please select a text first")
            return

        text_data = self.db.get_reading_text_by_id(self.current_text_id)

        if not text_data:
            messagebox.showerror("❌ Error", "Text not found")
            return

        # Clear display
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete('1.0', tk.END)

        # Insert text
        content = text_data['content']
        self.text_display.insert('1.0', content)

        # Find and highlight vocabulary (scoped to the text's own language,
        # which matches the active language since the list itself is filtered)
        matches = self.db.find_vocabulary_in_text(
            content, language=text_data.get('language', self.active_language))

        # Apply highlighting
        for match in matches:
            for start, end in match['positions']:
                # Convert character position to tkinter index
                start_index = f"1.0 + {start} chars"
                end_index = f"1.0 + {end} chars"
                self.text_display.tag_add('vocab', start_index, end_index)

        self.text_display.config(state=tk.DISABLED)

        # Update info label
        unique_vocab = len(matches)
        total_occurrences = sum(len(m['positions']) for m in matches)

        self.info_label.config(
            text=f"📄 {text_data['title']} | "
                 f"Words: {text_data['word_count']} | "
                 f"Vocabulary found: {unique_vocab} unique words ({total_occurrences} total occurrences)"
        )

    def _delete_selected_text(self) -> None:
        """Löscht den ausgewählten Text."""
        if self.current_text_id is None:
            messagebox.showwarning("⚠️ Warning", "Please select a text first")
            return

        text_data = self.db.get_reading_text_by_id(self.current_text_id)

        if not text_data:
            messagebox.showerror("❌ Error", "Text not found")
            return

        confirm = messagebox.askyesno("⚠️ Confirm Delete",
                                     f"Are you sure you want to delete:\n\n'{text_data['title']}'?")
        if not confirm:
            return

        success, msg = self.db.delete_reading_text(self.current_text_id)

        if success:
            messagebox.showinfo("✅ Success", f"Text '{text_data['title']}' deleted")
            self.current_text_id = None
            self._refresh_text_list()

            # Clear display
            self.text_display.config(state=tk.NORMAL)
            self.text_display.delete('1.0', tk.END)
            self.text_display.config(state=tk.DISABLED)
            self.info_label.config(text="")
        else:
            messagebox.showerror("❌ Error", f"Failed to delete text:\n{msg}")

    def _show_reading_statistics(self) -> None:
        """Zeigt Reading-Statistiken (nur aktive Sprache)."""
        stats = self.db.get_reading_statistics(language=self.active_language)

        stats_text = f"""
📊 READING STATISTICS

Total texts uploaded: {stats['total_texts']}
Total words in all texts: {stats['total_words']}
Average words per text: {stats['average_words']:.0f}

Total vocabulary matches: {stats['total_vocab_matches']}
Average vocab per text: {stats['average_vocab_matches']:.1f}
"""

        messagebox.showinfo("📊 Reading Statistics", stats_text)


# ============================================================================
# UI MODULE: SETTINGS
# ============================================================================
class SettingsUI:
    """
    Settings UI Module - Email-Konfiguration und App-Einstellungen

    PUBLIC API:
    ===========
    - get_ui(parent) → ttk.Frame
    """

    def __init__(self, email_module: EmailModule):
        """
        Initialisiert Settings-Modul.

        Args:
            email_module: EmailModule Instanz
        """
        self.email = email_module

    # === PUBLIC API ===

    def get_ui(self, parent: tk.Widget) -> ttk.Frame:
        """
        Erstellt und gibt das UI-Widget zurück.

        Args:
            parent: Parent-Widget

        Returns:
            ttk.Frame mit Settings-UI
        """
        frame = ttk.Frame(parent, padding="10")

        # Title
        title = ttk.Label(frame, text="⚙️ Settings", font=('Arial', 14, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Email section
        email_title = ttk.Label(frame, text="📧 Email Notifications",
                               font=('Arial', 12, 'bold'))
        email_title.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))

        # Instructions
        instructions = ("Configure your Gmail credentials to receive quiz results via email.\n"
                       "Important: Use a Gmail App Password, not your regular password.\n\n"
                       "How to get an App Password:\n"
                       "1. Go to Google Account Settings\n"
                       "2. Select Security → 2-Step Verification\n"
                       "3. Scroll down to 'App passwords'\n"
                       "4. Generate a new app password for 'Mail'\n"
                       "5. Copy and paste it below")

        instructions_label = ttk.Label(frame, text=instructions, justify=tk.LEFT)
        instructions_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

        # Email input
        ttk.Label(frame, text="Gmail Address:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(frame, width=40)
        self.email_entry.grid(row=3, column=1, pady=5, padx=5)

        # Password input
        ttk.Label(frame, text="App Password:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(frame, width=40, show="*")
        self.password_entry.grid(row=4, column=1, pady=5, padx=5)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="💾 Save Email Settings",
                  command=self._save_email_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📧 Send Test Email",
                  command=self._send_test_email).pack(side=tk.LEFT, padx=5)

        # Recipient info
        ttk.Separator(frame, orient='horizontal').grid(row=6, column=0, columnspan=2,
                                                       sticky='ew', pady=20)

        recipient_info = ttk.Label(frame,
                                   text=f"Email Recipient: {Config.EMAIL_RECIPIENT}\n"
                                   "Quiz results will be automatically sent to this address.",
                                   justify=tk.LEFT)
        recipient_info.grid(row=7, column=0, columnspan=2, sticky=tk.W)

        return frame

    # === PRIVATE METHODS - Event Handlers ===

    def _save_email_settings(self) -> None:
        """Speichert Email-Einstellungen."""
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()

        if email and password:
            self.email.configure_email(email, password)
            messagebox.showinfo("✅ Success",
                               "Email settings saved!\n\n"
                               f"Sender: {email}\n"
                               f"Recipient: {Config.EMAIL_RECIPIENT}\n\n"
                               "Quiz results will be sent automatically.")
        else:
            messagebox.showwarning("⚠️ Warning", "Please enter both email and password")

    def _send_test_email(self) -> None:
        """Sendet Test-Email."""
        test_stats = {
            'total_entries': 50,
            'queried_entries': 40,
            'never_queried': 10,
            'total_correct': 100,
            'total_wrong': 25,
            'success_rate': 80.0
        }

        messagebox.showinfo("📧 Sending...", "Sending test email...")

        success, msg = self.email.send_quiz_results(
            "Test Email",
            10,
            2,
            8,
            80.0,
            test_stats
        )

        if success:
            messagebox.showinfo("✅ Success",
                               f"Test email sent successfully!\n\n"
                               f"Check inbox: {Config.EMAIL_RECIPIENT}")
        else:
            messagebox.showerror("❌ Error",
                                f"Failed to send email:\n\n{msg}\n\n"
                                "Check your credentials and internet connection.")


# ============================================================================
# MAIN APPLICATION
# ============================================================================
class VocabularyApp:
    """
    Main Application - Koordiniert alle Module
    EXTENDED (v1.1): hält den globalen "active_language"-Zustand (REQ-LANG-01)
    und propagiert Sprachwechsel an alle sprachbewussten Tabs (REQ-LANG-02).

    Dependency Graph:
    ─────────────────
    VocabularyApp
      ├── VocabularyDatabase (standalone) - EXTENDED
      ├── EmailModule (standalone)
      ├── AddModifyUI → VocabularyDatabase
      ├── QuizUI → VocabularyDatabase, notification_callback
      ├── ListUI → VocabularyDatabase
      ├── ReadingUI → VocabularyDatabase (NEW)
      └── SettingsUI → EmailModule
    """

    def __init__(self, root: tk.Tk):
        """
        Initialisiert die Hauptanwendung.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.active_language = Config.DEFAULT_LANGUAGE  # REQ-LANG-06: startet auf Englisch
        self._setup_window()
        self._initialize_modules()
        self._create_language_switcher()
        self._create_ui()
        self._create_menu()

    # === PRIVATE METHODS - Initialization ===

    def _setup_window(self) -> None:
        """Konfiguriert das Hauptfenster."""
        self.root.title(f"{Config.APP_NAME} v{Config.VERSION}")
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")

    def _initialize_modules(self) -> None:
        """Initialisiert alle Module und Dependencies."""
        # Initialize core modules
        self.db = VocabularyDatabase(Config.STORAGE_FILE)
        self.email = EmailModule()

        # Setup notification callback
        def quiz_notification_callback(results: Dict) -> None:
            """Callback für Quiz-Ergebnisse."""
            if self.email.is_configured():
                success, message = self.email.send_quiz_results(
                    quiz_name=results['quiz_name'],
                    quiz_tested=results['quiz_tested'],
                    quiz_wrong=results['quiz_wrong'],
                    quiz_correct=results['quiz_correct'],
                    quiz_success_rate=results['quiz_success_rate'],
                    overall_stats=results['overall_stats']
                )
                if success:
                    print(f"📧 {message}")
                else:
                    print(f"📧 Email not sent: {message}")

        # Initialize UI modules
        self.add_modify_ui = AddModifyUI(self.db)
        self.quiz_ui = QuizUI(self.db, notification_callback=quiz_notification_callback)
        self.list_ui = ListUI(self.db)
        self.reading_ui = ReadingUI(self.db)  # NEW
        self.settings_ui = SettingsUI(self.email)

        # Show initial status
        success, message = self.db.load()
        print(f"📚 {Config.APP_NAME} v{Config.VERSION} Initialized")
        print(f"   {message}")
        print(f"   Storage: {Config.STORAGE_FILE}")

    def _create_language_switcher(self) -> None:
        """
        Erstellt den Sprachumschalter (REQ-LANG-01).
        Sitzt oberhalb der Tabs und ist jederzeit umschaltbar, nicht nur beim
        Start der App. Verwendet Radiobuttons im 'Toolbutton'-Stil, damit die
        aktive Sprache optisch als gedrückt erscheint.
        """
        frame = ttk.Frame(self.root, padding=(10, 10, 10, 0))
        frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(frame, text="Language:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        self.language_var = tk.StringVar(value=self.active_language)
        for language in ('english', 'spanish'):
            label = Config.LANGUAGE_LABELS[language]
            ttk.Radiobutton(
                frame, text=label, value=language, variable=self.language_var,
                style='Toolbutton', command=lambda l=language: self._set_active_language(l)
            ).pack(side=tk.LEFT, padx=2)

    def _set_active_language(self, language: str) -> None:
        """
        Wechselt die aktive Sprache der gesamten App und propagiert den
        Wechsel an jeden Tab (REQ-LANG-01/02). Es gibt bewusst keine
        kombinierte "alle Sprachen"-Ansicht — jede Sprache verhält sich wie
        ein unabhängiger Vokabeltrainer, der sich nur die Datei teilt.

        Args:
            language: 'english' oder 'spanish'
        """
        if language == self.active_language:
            return

        self.active_language = language
        self.language_var.set(language)

        self.add_modify_ui.set_active_language(language)
        self.quiz_ui.set_active_language(language)
        self.list_ui.set_active_language(language)
        self.reading_ui.set_active_language(language)

    def _create_ui(self) -> None:
        """Erstellt die Benutzeroberfläche mit Tabs."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add tabs
        self.notebook.add(self.add_modify_ui.get_ui(self.notebook), text='➕ Add/Modify')
        self.notebook.add(self.quiz_ui.get_ui(self.notebook), text='🧠 Quiz')
        self.notebook.add(self.list_ui.get_ui(self.notebook), text='📜 List')
        self.notebook.add(self.reading_ui.get_ui(self.notebook), text='📖 Reading')  # NEW
        self.notebook.add(self.settings_ui.get_ui(self.notebook), text='⚙️ Settings')

    def _create_menu(self) -> None:
        """Erstellt das Menü."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Data...", command=self._backup_data)
        file_menu.add_command(label="Restore Data...", command=self._restore_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Data Location", command=self._show_data_location)

    # === PRIVATE METHODS - Menu Handlers ===

    def _backup_data(self) -> None:
        """Erstellt Backup der Daten."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"vocabulary_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        if filename:
            try:
                import shutil
                shutil.copy(Config.STORAGE_FILE, filename)
                messagebox.showinfo("✅ Success", f"Backup saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("❌ Error", f"Backup failed:\n{e}")

    def _restore_data(self) -> None:
        """Stellt Daten aus Backup wieder her."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            confirm = messagebox.askyesno("⚠️ Confirm Restore",
                                         "This will replace your current data!\n\n"
                                         "Are you sure you want to restore from backup?")
            if confirm:
                try:
                    import shutil
                    backup_current = Config.STORAGE_FILE + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    if os.path.exists(Config.STORAGE_FILE):
                        shutil.copy(Config.STORAGE_FILE, backup_current)

                    shutil.copy(filename, Config.STORAGE_FILE)
                    self.db.load()

                    messagebox.showinfo("✅ Success",
                                       f"Data restored from:\n{filename}\n\n"
                                       f"Previous data backed up to:\n{backup_current}")

                    self.list_ui._refresh_list()
                    self.reading_ui._refresh_text_list()  # NEW
                except Exception as e:
                    messagebox.showerror("❌ Error", f"Restore failed:\n{e}")

    def _show_about(self) -> None:
        """Zeigt About-Dialog."""
        about_text = f"""
📚 {Config.APP_NAME}

Version: {Config.VERSION} (Reading Module Added)
Platform: Windows

Features:
  • Modular architecture with clear separation
  • Add, modify, and delete vocabulary
  • Search in vocabulary database
  • Six quiz modes with smart filtering
  • Reading texts with vocabulary highlighting (NEW)
  • Upload text files for reading practice (NEW)
  • Automatic vocabulary detection in texts (NEW)
  • Detailed statistics and tracking
  • Email notifications after each quiz
  • Automatic data backup
  • Full backward compatibility

Created for effective vocabulary learning!

Data storage: {Config.STORAGE_FOLDER}
"""
        messagebox.showinfo("About", about_text)

    def _show_data_location(self) -> None:
        """Zeigt Speicherort der Daten."""
        messagebox.showinfo("📁 Data Location",
                           f"Your vocabulary data is stored at:\n\n{Config.STORAGE_FILE}\n\n"
                           "You can backup this file manually using File → Backup Data.")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = VocabularyApp(root)

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()
