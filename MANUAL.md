# 📚 Filip's English Vocabulary Learning App - Benutzerhandbuch

**Version 2.61**

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Installation & Start](#installation--start)
3. [Funktionen](#funktionen)
   - [Vokabeln hinzufügen/bearbeiten](#-vokabeln-hinzufügenbearbeiten)
   - [Quiz-Modi](#-quiz-modi)
   - [Vokabelliste](#-vokabelliste)
   - [Reading-Modul](#-reading-modul)
   - [Einstellungen](#-einstellungen)
4. [Datenverwaltung](#datenverwaltung)
5. [Tipps & Tricks](#tipps--tricks)
6. [FAQ](#häufige-fragen-faq)

---

## Übersicht

Die Vocabulary Learning App ist eine Desktop-Anwendung zum Lernen englischer Vokabeln mit folgenden Hauptfunktionen:

- ✅ Vokabeln hinzufügen, bearbeiten und löschen
- 🧠 6 verschiedene Quiz-Modi mit Fortschrittsverfolgung
- 📊 Detaillierte Statistiken und Analysen
- 📖 Reading-Modul mit automatischer Vokabel-Markierung
- 📧 Email-Benachrichtigungen nach jedem Quiz
- 💾 CSV-Export der Vokabeldatenbank
- 🔍 Such- und Filterfunktionen

---

## Installation & Start

### Voraussetzungen

- Python 3.7 oder höher
- Keine zusätzlichen Pakete erforderlich (nur Python Standard-Bibliothek)

### Starten der Anwendung
```bash
python vocabulary_app_with_reading.py
```

### Daten-Speicherort

Die Vokabeldaten werden automatisch gespeichert unter:
```
C:\Users\[Benutzername]\Documents\FilipVocabularyApp\vocabulary_data.json
```

---

## Funktionen

### ➕ Vokabeln hinzufügen/bearbeiten

#### Neue Vokabel hinzufügen

1. Wechseln zum Tab **"➕ Add/Modify"**
2. **English Word** eingeben (z.B. "apple")
3. **German Translation** eingeben (z.B. "Apfel")
4. Klick auf **"➕ Add Vocabulary"** oder Enter-Taste drücken

**Tastatur-Shortcuts:**
- `Enter` im English-Feld → springt zum German-Feld
- `Enter` im German-Feld → speichert die Vokabel

#### Vokabel bearbeiten

1. **Entry ID** eingeben (ID aus der Vokabelliste)
2. Klick auf **"🔍 Load Entry"**
3. **New English** und **New German** bearbeiten
4. Klick auf **"💾 Save Changes"**

#### Vokabel löschen

1. **Entry ID** eingeben
2. Klick auf **"🗑️ Delete Entry"**
3. Löschvorgang bestätigen

---

### 🧠 Quiz-Modi

Die App bietet 6 verschiedene Quiz-Modi:

#### 1. 📚 Quiz: Last 10 Words

- Testet die letzten 10 hinzugefügten Vokabeln
- Ideal für tägliches Üben neuer Wörter

#### 2. 📖 Quiz: Last 30 Words

- Testet die letzten 30 hinzugefügten Vokabeln
- Für umfangreicheres Üben

#### 3. 🎲 Quiz: Random 30 Words

- Wählt 30 zufällige Vokabeln aus
- Filtert automatisch Wörter mit weniger als 5 korrekten Antworten
- Perfekt für regelmäßiges Training

#### 4. ❌ Quiz: Incorrect Only

- Testet nur Vokabeln, die zuletzt falsch beantwortet wurden
- Gezieltes Üben schwieriger Wörter

#### 5. 📅 Quiz: Today's Words

- Testet alle heute hinzugefügten Vokabeln
- Ideal für Tagesrückblick

#### 6. 🆕 Quiz: Never Tested Words

- Testet alle noch nie abgefragten Vokabeln
- Für systematisches Lernen

#### Quiz durchführen

1. Gewünschten Modus wählen
2. Deutsche Übersetzung wird angezeigt
3. Englisches Wort eingeben
4. `Enter` drücken oder **"✅ Submit Answer"** klicken
5. Feedback erscheint (✅ Richtig / ❌ Falsch)
6. Nach dem Quiz: Detaillierte Ergebnisse und Gesamtstatistik

**Quiz-Ergebnisse:**
- Anzahl getesteter Wörter
- Korrekte/falsche Antworten
- Erfolgsquote in %
- Gesamtstatistik aller bisherigen Quiz

---

### 📜 Vokabelliste

#### Funktionen der Vokabelliste

**Anzeige:**
- ID, English, German
- Letztes Ergebnis (✅/❌/➖)
- Datum des letzten Quiz
- Anzahl Correct/Wrong (C/W)

**Aktionen:**

##### 🔄 Refresh List

Aktualisiert die Liste (z.B. nach Hinzufügen neuer Vokabeln)

##### 📊 Show Statistics

Zeigt detaillierte Statistiken:
- Gesamtzahl der Vokabeln
- Abgefragte vs. nie abgefragte Wörter
- Erfolgsquote
- Top 5 schwierigste Wörter

##### 🔍 Find Doublets

Findet und markiert doppelte englische Wörter
- Doppelte Einträge werden rot markiert
- Zeigt IDs der Duplikate an

##### 💾 Export to CSV

Exportiert die komplette Vokabeldatenbank als CSV-Datei
- Trennzeichen: Semikolon (`;`)
- Kodierung: UTF-8
- Öffenbar in Excel, LibreOffice Calc, etc.

**CSV-Spalten:**
- ID, English, German
- Created At, Last Queried
- Last Result, Correct Count, Wrong Count
- Success Rate (%)

##### 🔍 Search (Suchfunktion)

1. Suchbegriff eingeben
2. Klick auf **"🔍 Search"** oder Enter
3. Gefundene Vokabeln werden gelb markiert angezeigt
4. **"✖️ Clear Search"** zum Zurücksetzen

---

### 📖 Reading-Modul

Das Reading-Modul ermöglicht das Hochladen von Texten mit automatischer Vokabel-Markierung.

#### Text hochladen

1. Wechseln zum Tab **"📖 Reading"**
2. Klick auf **"📤 Upload Text File"**
3. Textdatei (.txt) auswählen
4. Titel für den Text eingeben
5. Text wird hochgeladen und analysiert

#### Text anzeigen

1. Text aus der Liste auswählen
2. Klick auf **"👁️ View Selected"**
3. Text wird angezeigt mit:
   - **Grün markierte Wörter** = Vokabeln aus der Datenbank
   - Statistik: Wortanzahl, gefundene Vokabeln

**Info-Anzeige:**
- Titel des Textes
- Gesamtzahl Wörter
- Anzahl einzigartiger Vokabeln
- Gesamtzahl Vorkommen

#### Text löschen

1. Text aus der Liste auswählen
2. Klick auf **"🗑️ Delete Selected"**
3. Löschung bestätigen

#### 📊 Statistics

Zeigt Reading-Statistiken:
- Anzahl hochgeladener Texte
- Gesamtzahl Wörter in allen Texten
- Durchschnittliche Wortanzahl pro Text
- Durchschnittliche Vokabel-Treffer

---

### ⚙️ Einstellungen

#### Email-Benachrichtigungen einrichten

Die App kann nach jedem Quiz automatisch eine Email mit den Ergebnissen versenden.

**Voraussetzungen:**
- Gmail-Account
- Gmail App-Passwort (NICHT das normale Passwort!)

**Gmail App-Passwort erstellen:**

1. Google Account-Einstellungen öffnen
2. **Sicherheit** → **2-Faktor-Authentifizierung**
3. Nach unten scrollen zu **"App-Passwörter"**
4. Neues App-Passwort für "Mail" generieren
5. 16-stelliges Passwort kopieren

**In der App konfigurieren:**

1. Wechseln zum Tab **"⚙️ Settings"**
2. **Gmail Address** eingeben
3. **App Password** einfügen (16 Zeichen)
4. Klick auf **"💾 Save Email Settings"**

**Test-Email senden:**

- Klick auf **"📧 Send Test Email"**
- Prüfen ob Email bei `janpfrang@hotmail.com` ankommt

**Email-Inhalt:**
- Quiz-Name und Datum
- Quiz-Performance (getestet, korrekt, falsch, Erfolgsrate)
- Gesamtstatistik (alle Zeiten)
- Schönes HTML-Design

---

## Datenverwaltung

### Automatisches Backup

Die Daten werden automatisch bei jeder Änderung gespeichert.

### Manuelles Backup

**Menü → File → Backup Data...**

1. Speicherort und Dateiname wählen
2. JSON-Datei wird erstellt
3. Empfohlen: Regelmäßige Backups auf externem Laufwerk

### Daten wiederherstellen

**Menü → File → Restore Data...**

1. Backup-Datei (.json) auswählen
2. Bestätigung (überschreibt aktuelle Daten!)
3. Alte Daten werden automatisch gesichert
4. Liste wird aktualisiert

### Datenspeicherort anzeigen

**Menü → Help → Data Location**

- Zeigt den Pfad zur Datendatei
- Direkter Zugriff zur Datei möglich

---

## Tipps & Tricks

### 🎯 Effektives Lernen

**Täglich:**
- Morgens: "📅 Quiz: Today's Words" (Wiederholung vom Vortag)
- Abends: "📚 Quiz: Last 10 Words" (neue Wörter)

**Wöchentlich:**
- 1x "🎲 Quiz: Random 30 Words" (zufällige Wiederholung)
- 1x "❌ Quiz: Incorrect Only" (schwierige Wörter gezielt)

**Monatlich:**
- Statistiken prüfen und schwierige Wörter identifizieren
- CSV-Export erstellen und in Excel analysieren
- Doublets suchen und doppelte Einträge löschen

### 📖 Reading-Modul optimal nutzen

**Geeignete Texte:**
- Kurze Zeitungsartikel
- Blog-Posts
- Buchkapitel
- Eigene Texte

**Workflow:**

1. Text hochladen
2. Markierte Vokabeln identifizieren
3. Unbekannte (nicht markierte) Wörter zur Datenbank hinzufügen
4. Text erneut anzeigen → mehr Markierungen!

### 🔍 Suchfunktion nutzen

**Beispiele:**
- Nach Thema suchen: "car" findet alle Auto-Vokabeln
- Nach deutscher Übersetzung: "haus" findet house, building, etc.
- Nach Wortteilen: "ing" findet alle Wörter mit -ing

### 📊 Statistiken interpretieren

**Erfolgsquote unter 70%?**  
→ Mehr üben mit "❌ Quiz: Incorrect Only"

**Viele "Never Queried" Wörter?**  
→ "🆕 Quiz: Never Tested Words" verwenden

**Hohe Wrong Count bei bestimmten Wörtern?**  
→ In der Statistik identifizieren und gezielt üben

### 💡 Best Practices

1. **Regelmäßigkeit:** Täglich 10-15 Minuten besser als 1x wöchentlich 2 Stunden
2. **Kontextlernen:** Vokabeln aus Reading-Texten lernen sich besser
3. **Wiederholung:** Wörter mit <5 korrekten Antworten werden automatisch ins Random-Quiz einbezogen
4. **Backup:** Wöchentliches Backup verhindert Datenverlust
5. **Email-Tracking:** Emails dokumentieren Lernfortschritt über Zeit

---

## Häufige Fragen (FAQ)

**Q: Kann ich die App auf mehreren Computern nutzen?**  
A: Ja, einfach die `vocabulary_data.json` Datei zwischen Computern kopieren oder über Cloud-Dienst synchronisieren.

**Q: Unterstützt die App andere Sprachen außer Englisch-Deutsch?**  
A: Die Felder sind flexibel - man kann jede Sprachkombination nutzen. Die UI ist allerdings auf Englisch-Deutsch ausgelegt.

**Q: Wie viele Vokabeln kann ich speichern?**  
A: Praktisch unbegrenzt. Die App wurde mit mehreren tausend Vokabeln getestet.

**Q: Warum funktioniert der Email-Versand nicht?**  
A: Stelle sicher, dass du ein Gmail **App-Passwort** verwendest, nicht dein normales Gmail-Passwort. 2-Faktor-Authentifizierung muss in Gmail aktiviert sein.

**Q: Kann ich die Empfänger-Email-Adresse ändern?**  
A: Ja, in der Datei unter `Config.EMAIL_RECIPIENT` (Zeile 52) kann die Adresse geändert werden.

**Q: Wie erstelle ich eine .exe-Datei?**  
A: Mit PyInstaller:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "FilipVocabularyApp" vocabulary_app_with_reading.py
```

---

## Support & Kontakt

Bei Fragen oder Problemen:
- Email: janpfrang@hotmail.com

---

**Viel Erfolg beim Vokabellernen! 📚🎓**
