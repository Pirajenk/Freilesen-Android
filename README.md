# Freilesen

Minimalistische Android-App für frei zugängliche journalistische Perspektiven auf ein Thema.

## Konzept

Freilesen umgeht keine Paywalls, entfernt keine Bezahlschranken und extrahiert keine geschützten Artikeltexte. Ein eingefügter Link wird anhand von Seitentitel, Beschreibung, Herausgeber, Datum und URL-Begriffen ausgewertet. Die App zeigt passende Meldungen mit Metadaten und öffnet die Originalquelle. Die Zugänglichkeit kann sich ändern; deshalb prüft man sie auf der Verlagsseite. Offensichtlich als Plus-/Paywall markierte Treffer werden herausgefiltert.

## Projekt

- Android-App: Kotlin und Jetpack Compose, Mindestversion Android 8.0 (API 26)
- Vorschau und lokaler Suchdienst: `python3 server.py` starten, danach `http://localhost:8765` öffnen
- Android-Emulator: derselbe Server muss laufen; Android Studio/Emulator greift über `http://10.0.2.2:8765` zu
- Oberfläche: Deutsch/Englisch, Quellenfilter, Artikelliste, Lesemodus

## Entwicklungsstand

Die Vorschau und die Android-Oberfläche verwenden `server.py`: Der Server liest Metadaten des eingegebenen Artikels und fragt Google News RSS auf Deutsch/Englisch sowie GDELT DOC nach verwandten Meldungen ab. GDELT beschreibt seinen Index als weltweite Suche über 65 Sprachen mit einem rollierenden Fenster von drei Monaten ([GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)). Jeder thematische Kandidat wird danach direkt beim Verlag aufgerufen. Explizite Paywall-Signale, fehlgeschlagene Abrufe und unklare Seiten werden ausgeschlossen; nur Seiten mit positivem Freizugriffs-Metadatum oder umfangreichem lesbarem Artikeltext ohne erkannte Paywall-Hinweise werden angezeigt. Das ist eine konservative Live-Prüfung, aber keine Garantie für zukünftige Erreichbarkeit oder jeden Nutzungszustand. Die App übernimmt keine Volltexte.

Jeder Treffer trägt einen Score von 0 bis 100 mit Verlauf von Rot (niedrig) bis Grün (hoch). Der Score vergleicht Metadaten und misst thematische Nähe, nicht den vollständigen Text. Die Merkliste unterstützt lokal gespeicherte Themenordner und Artikel; gespeicherte Links führen weiterhin zur Verlagsseite, deren Verfügbarkeit sich später ändern kann.

## Bauen

Mit Android Studio öffnen und Gradle Sync ausführen. Erforderlich sind JDK 17, Android SDK Platform 35 und ein Emulator. Für eine physische Android-Verbindung sind Serveradresse und erlaubter Host in der Android-Konfiguration anzupassen.

## Freiwillige Unterstützung

Die App ist kostenlos nutzbar. Am Ende der Entdecken-Seite gibt es einen freiwilligen PayPal-Spendenlink mit `dome0903@yahoo.de` als Empfänger. Spenden sind keine Voraussetzung für die Nutzung.

## Datenschutz & Quellen

Der Server protokolliert Suchpfade ohne den eingegebenen Artikel-Link. Für die Suche werden erkannte Themenbegriffe an Google News RSS übermittelt; der vollständige Link wird nur vom lokalen Server zur Metadatenabfrage geöffnet. Quellen-URLs, Nutzungsrechte, robots/Publisher-Vorgaben und ein Impressum sind vor Veröffentlichung zu ergänzen.

## VS Code und Android-Emulator

VS Code-Erweiterungen: Kotlin (`fwcd.kotlin`) sowie Java/Gradle (`vscjava.vscode-java-pack`). Für einen Android-Emulator werden zusätzlich ein JDK 17 und Android Studio mit Android SDK Platform 35, Build Tools und einem Emulator-Image benötigt. Dieses Projekt lässt sich in VS Code bearbeiten; die Emulatorverwaltung erfolgt über Android Studio/Android SDK. Ein Build und Emulatorstart waren in der aktuellen Umgebung nicht möglich, weil weder JDK noch Android SDK/Emulator installiert sind.
