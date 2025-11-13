# test_vocabulary_app.py
import unittest
import tempfile
import os
from vocabulary_app_with_reading import VocabularyDatabase


class TestVocabularyDatabase(unittest.TestCase):
    """Tests für die VocabularyDatabase-Klasse"""
    
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
    
    def test_add_entry(self):
        """Test: Vokabel hinzufügen"""
        success, msg = self.db.add_entry("hello", "hallo")
        
        self.assertTrue(success, "Entry sollte erfolgreich hinzugefügt werden")
        self.assertEqual(len(self.db.get_all_entries()), 1, "Es sollte genau 1 Entry geben")
        
        entry = self.db.get_all_entries()[0]
        self.assertEqual(entry['english'], "hello")
        self.assertEqual(entry['german'], "hallo")
    
    def test_get_all_entries_empty(self):
        """Test: Leere Datenbank"""
        entries = self.db.get_all_entries()
        self.assertEqual(len(entries), 0, "Neue DB sollte leer sein")
    
    def test_update_entry(self):
        """Test: Vokabel bearbeiten"""
        # Zuerst hinzufügen
        self.db.add_entry("hello", "hallo")
        entry = self.db.get_all_entries()[0]
        entry_id = entry['id']
        
        # Dann ändern
        success, msg = self.db.update_entry(entry_id, "goodbye", "tschüss")
        
        self.assertTrue(success, "Update sollte erfolgreich sein")
        
        updated_entry = self.db.get_entry_by_id(entry_id)
        self.assertEqual(updated_entry['english'], "goodbye")
        self.assertEqual(updated_entry['german'], "tschüss")
    
    def test_delete_entry(self):
        """Test: Vokabel löschen"""
        # Hinzufügen
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']
        
        # Löschen
        success, msg = self.db.delete_entry(entry_id)
        
        self.assertTrue(success, "Delete sollte erfolgreich sein")
        self.assertEqual(len(self.db.get_all_entries()), 0, "DB sollte nach Delete leer sein")
    
    def test_record_quiz_result_correct(self):
        """Test: Quiz-Ergebnis speichern (korrekt)"""
        self.db.add_entry("hello", "hallo")
        entry_id = self.db.get_all_entries()[0]['id']
        
        # Korrekte Antwort aufzeichnen
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
        
        # Falsche Antwort aufzeichnen
        success, msg = self.db.record_quiz_result(entry_id, False)
        
        self.assertTrue(success)
        
        entry = self.db.get_entry_by_id(entry_id)
        self.assertEqual(entry['correct_count'], 0)
        self.assertEqual(entry['wrong_count'], 1)
        self.assertFalse(entry['last_result'])
    
    def test_get_statistics(self):
        """Test: Statistiken berechnen"""
        # Mehrere Entries hinzufügen
        self.db.add_entry("hello", "hallo")
        self.db.add_entry("world", "welt")
        self.db.add_entry("test", "test")
        
        # Quiz-Ergebnisse aufzeichnen
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
        # Vokabeln hinzufügen
        self.db.add_entry("hello", "hallo")
        self.db.add_entry("world", "welt")
        
        # Text mit Vokabeln
        text = "Hello world! This is a hello world test."
        
        matches = self.db.find_vocabulary_in_text(text)
        
        # Es sollten 2 verschiedene Vokabeln gefunden werden
        self.assertEqual(len(matches), 2)
        
        # "hello" sollte 2x vorkommen
        hello_match = [m for m in matches if m['vocab']['english'] == 'hello'][0]
        self.assertEqual(len(hello_match['positions']), 2)
        
        # "world" sollte 2x vorkommen
        world_match = [m for m in matches if m['vocab']['english'] == 'world'][0]
        self.assertEqual(len(world_match['positions']), 2)
    
    def test_add_reading_text(self):
        """Test: Lesetext hinzufügen"""
        # Erst Vokabeln hinzufügen
        self.db.add_entry("hello", "hallo")
        
        # Dann Text hinzufügen
        success, msg = self.db.add_reading_text(
            "Test Title",
            "Hello world! This is a test text with hello in it."
        )
        
        self.assertTrue(success)
        
        texts = self.db.get_all_reading_texts()
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0]['title'], "Test Title")
        self.assertEqual(texts[0]['vocabulary_matches'], 1)  # nur "hello" ist Vokabel


if __name__ == '__main__':
    unittest.main()
