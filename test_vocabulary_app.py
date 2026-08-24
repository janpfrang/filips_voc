# test_vocabulary_app.py
import unittest
import tempfile
import os
import json
import unicodedata
from main_code_voc import VocabularyDatabase, normalize_text


class TestVocabularyDatabase(unittest.TestCase):
    """Tests für die VocabularyDatabase-Klasse (v1.1: sprachbewusst)"""

    def setUp(self):
        """Erstellt temporäre Test-Datenbank vor jedem Test"""
        # Temporäre Datei für Tests erstellen
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.db = VocabularyDatabase(self.temp_file.name)

    def tearDown(self):
        """Räumt nach jedem Test auf"""
        # Temporäre Datei löschen
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    # === Basic CRUD (default language: english) ===

    def test_add_entry_defaults_to_english(self):
        """Test: Vokabel hinzufügen ohne language-Argument -> English, ID-Präfix 'E'"""
        success, msg = self.db.add_entry("hello", "hallo")

        self.assertTrue(success, "Entry sollte erfolgreich hinzugefügt werden")
        self.assertEqual(len(self.db.get_all_entries()), 1, "Es sollte genau 1 Entry geben")

        entry = self.db.get_all_entries()[0]
        self.assertEqual(entry['foreign_word'], "hello")
        self.assertEqual(entry['german'], "hallo")
        self.assertEqual(entry['language'], "english")
        self.assertEqual(entry['id'], "E1")

    def test_add_entry_spanish(self):
        """Test: Vokabel mit language='spanish' hinzufügen -> ID-Präfix 'S'"""
        success, msg = self.db.add_entry("hola", "hallo", language="spanish")

        self.assertTrue(success)
        entry = self.db.get_all_entries()[0]
        self.assertEqual(entry['foreign_word'], "hola")
        self.assertEqual(entry['language'], "spanish")
        self.assertEqual(entry['id'], "S1")

    def test_add_entry_unknown_language_rejected(self):
        """Test: Unbekannte Sprache wird abgelehnt statt still zu übernehmen"""
        success, msg = self.db.add_entry("bonjour", "hallo", language="french")

        self.assertFalse(success)
        self.assertEqual(len(self.db.get_all_entries()), 0)

    def test_get_all_entries_empty(self):
        """Test: Leere Datenbank"""
        entries = self.db.get_all_entries()
        self.assertEqual(len(entries), 0, "Neue DB sollte leer sein")

    def test_update_entry(self):
        """Test: Vokabel bearbeiten (foreign_word statt english)"""
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']

        success, msg = self.db.update_entry(entry_id, foreign_word="goodbye", german="tschüss")

        self.assertTrue(success, "Update sollte erfolgreich sein")

        updated_entry = self.db.get_entry_by_id(entry_id)
        self.assertEqual(updated_entry['foreign_word'], "goodbye")
        self.assertEqual(updated_entry['german'], "tschüss")

    def test_delete_entry(self):
        """Test: Vokabel löschen"""
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']

        success, msg = self.db.delete_entry(entry_id)

        self.assertTrue(success, "Delete sollte erfolgreich sein")
        self.assertEqual(len(self.db.get_all_entries()), 0, "DB sollte nach Delete leer sein")

    def test_record_quiz_result_correct(self):
        """Test: Quiz-Ergebnis speichern (korrekt)"""
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']

        success, msg = self.db.record_quiz_result(entry_id, True)

        self.assertTrue(success)

        entry = self.db.get_entry_by_id(entry_id)
        self.assertEqual(entry['correct_count'], 1)
        self.assertEqual(entry['wrong_count'], 0)
        self.assertTrue(entry['last_result'])

    def test_record_quiz_result_wrong(self):
        """Test: Quiz-Ergebnis speichern (falsch)"""
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']

        success, msg = self.db.record_quiz_result(entry_id, False)

        self.assertTrue(success)

        entry = self.db.get_entry_by_id(entry_id)
        self.assertEqual(entry['correct_count'], 0)
        self.assertEqual(entry['wrong_count'], 1)
        self.assertFalse(entry['last_result'])

    def test_get_statistics(self):
        """Test: Statistiken berechnen (über alle Sprachen)"""
        self.db.add_entry("hello", "hallo")
        self.db.add_entry("world", "welt")
        self.db.add_entry("test", "test")

        entries = self.db.get_all_entries()
        self.db.record_quiz_result(entries[0]['id'], True)
        self.db.record_quiz_result(entries[1]['id'], False)
        # entries[2] bleibt ungetestet

        stats = self.db.get_statistics()

        self.assertEqual(stats['total_entries'], 3)
        self.assertEqual(stats['queried_entries'], 2)
        self.assertEqual(stats['never_queried'], 1)
        self.assertEqual(stats['total_correct'], 1)
        self.assertEqual(stats['total_wrong'], 1)
        self.assertEqual(stats['success_rate'], 50.0)

    def test_find_vocabulary_in_text(self):
        """Test: Vokabeln in Text finden"""
        self.db.add_entry("hello", "hallo")
        self.db.add_entry("world", "welt")

        text = "Hello world! This is a hello world test."

        matches = self.db.find_vocabulary_in_text(text)

        self.assertEqual(len(matches), 2)

        hello_match = [m for m in matches if m['vocab']['foreign_word'] == 'hello'][0]
        self.assertEqual(len(hello_match['positions']), 2)

        world_match = [m for m in matches if m['vocab']['foreign_word'] == 'world'][0]
        self.assertEqual(len(world_match['positions']), 2)

    def test_add_reading_text(self):
        """Test: Lesetext hinzufügen"""
        self.db.add_entry("hello", "hallo")

        success, msg = self.db.add_reading_text(
            "Test Title",
            "Hello world! This is a test text with hello in it."
        )

        self.assertTrue(success)

        texts = self.db.get_all_reading_texts()
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0]['title'], "Test Title")
        self.assertEqual(texts[0]['language'], "english")
        self.assertEqual(texts[0]['id'], "E1")
        self.assertEqual(texts[0]['vocabulary_matches'], 1)  # nur "hello" ist Vokabel

    # === v1.1: Language scoping ===

    def test_language_scoped_filtering(self):
        """Test: get_all_entries(language=...) liefert nur die passende Sprache"""
        self.db.add_entry("hello", "hallo", language="english")
        self.db.add_entry("world", "welt", language="english")
        self.db.add_entry("hola", "hallo", language="spanish")

        english_only = self.db.get_all_entries(language="english")
        spanish_only = self.db.get_all_entries(language="spanish")
        combined = self.db.get_all_entries()

        self.assertEqual(len(english_only), 2)
        self.assertEqual(len(spanish_only), 1)
        self.assertEqual(len(combined), 3)
        self.assertTrue(all(e['language'] == 'english' for e in english_only))
        self.assertTrue(all(e['language'] == 'spanish' for e in spanish_only))

    def test_independent_id_counters_per_language(self):
        """Test: Englische und spanische Einträge haben unabhängige ID-Zähler"""
        self.db.add_entry("hello", "hallo", language="english")
        self.db.add_entry("hola", "hallo", language="spanish")
        self.db.add_entry("world", "welt", language="english")
        self.db.add_entry("adios", "tschüss", language="spanish")

        ids = [e['id'] for e in self.db.get_all_entries()]
        self.assertIn("E1", ids)
        self.assertIn("E2", ids)
        self.assertIn("S1", ids)
        self.assertIn("S2", ids)

    def test_reading_text_matches_only_same_language_vocab(self):
        """Test: Ein spanischer Text matched nicht gegen englische Vokabeln"""
        self.db.add_entry("hello", "hallo", language="english")
        self.db.add_entry("hola", "hallo", language="spanish")

        # Text enthält beide Wörter, ist aber als Spanisch getaggt
        success, msg = self.db.add_reading_text(
            "Texto de prueba", "Hola, hello!", language="spanish"
        )

        self.assertTrue(success)
        text = self.db.get_all_reading_texts(language="spanish")[0]
        self.assertEqual(text['vocabulary_matches'], 1)  # nur "hola" zählt

    def test_get_statistics_scoped_by_language(self):
        """Test: Statistiken lassen sich pro Sprache filtern"""
        self.db.add_entry("hello", "hallo", language="english")
        self.db.add_entry("hola", "hallo", language="spanish")
        self.db.add_entry("adios", "tschüss", language="spanish")

        stats_all = self.db.get_statistics()
        stats_spanish = self.db.get_statistics(language="spanish")
        stats_english = self.db.get_statistics(language="english")

        self.assertEqual(stats_all['total_entries'], 3)
        self.assertEqual(stats_spanish['total_entries'], 2)
        self.assertEqual(stats_english['total_entries'], 1)

    # === v1.1: Migration from legacy (pre-language) data ===

    def test_migration_from_legacy_format(self):
        """Test: Alte Daten (Integer-IDs, 'english'-Feld, keine 'language') werden migriert"""
        legacy_data = {
            "vocabulary": [
                {
                    "id": 1,
                    "english": "hello",
                    "german": "hallo",
                    "created_at": "2026-01-01 10:00:00",
                    "last_queried": None,
                    "last_result": None,
                    "correct_count": 0,
                    "wrong_count": 0
                }
            ],
            "reading_texts": [
                {
                    "id": 1,
                    "title": "Old Text",
                    "content": "hello there",
                    "uploaded_at": "2026-01-01 10:00:00",
                    "word_count": 2,
                    "vocabulary_matches": 1
                }
            ]
        }

        legacy_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(legacy_data, legacy_file)
        legacy_file.close()

        try:
            migrated_db = VocabularyDatabase(legacy_file.name)

            entry = migrated_db.get_all_entries()[0]
            self.assertEqual(entry['id'], "E1")
            self.assertEqual(entry['language'], "english")
            self.assertEqual(entry['foreign_word'], "hello")
            self.assertNotIn('english', entry)

            text = migrated_db.get_all_reading_texts()[0]
            self.assertEqual(text['id'], "E1")
            self.assertEqual(text['language'], "english")

            # Nach der Migration muss eine neue englische Vokabel nahtlos E2 erhalten
            migrated_db.add_entry("world", "welt")
            new_entry = [e for e in migrated_db.get_all_entries() if e['foreign_word'] == 'world'][0]
            self.assertEqual(new_entry['id'], "E2")

            # Migration muss auf Disk persistiert worden sein (nur einmalig nötig)
            with open(legacy_file.name, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            self.assertEqual(saved['vocabulary'][0]['id'], "E1")
            self.assertIn('language', saved['vocabulary'][0])
        finally:
            os.remove(legacy_file.name)

    # === v1.1: Unicode NFC normalization (REQ-NF-07) ===

    def test_normalize_text_converts_nfd_to_nfc(self):
        """Test: normalize_text() wandelt NFD-Text (Basiszeichen + Kombinationszeichen) in NFC um"""
        nfd_cafe = unicodedata.normalize('NFD', 'café')
        self.assertNotEqual(nfd_cafe, 'café', "Sanity check: NFD-Form ist eine andere Byte-Sequenz als NFC")

        result = normalize_text(nfd_cafe)

        self.assertEqual(result, unicodedata.normalize('NFC', 'café'))
        self.assertEqual(result, 'café')

    def test_normalize_text_leaves_nfc_unchanged(self):
        """Test: normalize_text() lässt bereits NFC-normalisierten Text unverändert"""
        self.assertEqual(normalize_text('café'), 'café')
        self.assertEqual(normalize_text('hello'), 'hello')

    def test_add_entry_normalizes_nfd_input(self):
        """Test: add_entry() speichert NFD-Eingabe als NFC (foreign_word und german)"""
        nfd_cafe = unicodedata.normalize('NFD', 'café')
        nfd_tschuess = unicodedata.normalize('NFD', 'tschüss')

        success, msg = self.db.add_entry(nfd_cafe, nfd_tschuess, language="spanish")

        self.assertTrue(success)
        entry = self.db.get_all_entries()[0]
        self.assertEqual(entry['foreign_word'], unicodedata.normalize('NFC', 'café'))
        self.assertEqual(entry['german'], unicodedata.normalize('NFC', 'tschüss'))
        # stored bytes must match NFC, not the original NFD input
        self.assertNotEqual(entry['foreign_word'], nfd_cafe)

    def test_update_entry_normalizes_nfd_input(self):
        """Test: update_entry() normalisiert NFD-Eingabe beim Bearbeiten ebenfalls auf NFC"""
        self.db.add_entry("hola", "hallo", language="spanish")
        entry_id = self.db.get_all_entries()[0]['id']

        nfd_cafe = unicodedata.normalize('NFD', 'café')
        success, msg = self.db.update_entry(entry_id, foreign_word=nfd_cafe)

        self.assertTrue(success)
        updated = self.db.get_entry_by_id(entry_id)
        self.assertEqual(updated['foreign_word'], unicodedata.normalize('NFC', 'café'))


if __name__ == '__main__':
    unittest.main()
