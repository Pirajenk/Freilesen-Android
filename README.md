# Freilesen

Minimalistische Android-App für frei zugängliche journalistische Perspektiven auf ein Thema.

## Konzept

Freilesen umgeht keine Paywalls, entfernt keine Bezahlschranken und extrahiert keine geschützten Artikeltexte. Ein eingefügter Link wird anhand von Seitentitel, Beschreibung, Herausgeber, Datum und URL-Begriffen ausgewertet. Die App zeigt passende Meldungen mit Metadaten und öffnet die Originalquelle. Treffer mit Paywall-Signalen oder unklarem Zugriff werden ausgeblendet; die Zugänglichkeit kann sich nach der Prüfung dennoch ändern.

## Projekt

- Android-App: Kotlin und Jetpack Compose, Mindestversion Android 8.0 (API 26)
- Vorschau und lokaler Suchdienst: `python3 server.py` starten, danach `http://localhost:8765` öffnen
- Android-Emulator: derselbe Server muss laufen; Android Studio/Emulator greift über `http://10.0.2.2:8765` zu
- Oberfläche: Deutsch/Englisch, Quellenfilter, Artikelliste, Lesemodus

## Entwicklungsstand

Die Vorschau und die Android-Oberfläche verwenden `server.py`: Der Server liest Metadaten des eingegebenen Artikels und fragt Google News RSS auf Deutsch/Englisch sowie GDELT DOC nach verwandten Meldungen ab. GDELT beschreibt seinen Index als weltweite Suche über 65 Sprachen mit einem rollierenden Fenster von drei Monaten ([GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)). Die Suche nutzt alternative Themenformulierungen und lässt auch partielle inhaltliche Überschneidungen zu. Die Paywall-Prüfung liest maschinenlesbare Signale im HTML: insbesondere Schema.org `isAccessibleForFree`, `hasPart`/Paywall-Selektoren, Premium-/Abo-Metadaten, typische Paywall-Elemente und Hinweise im sichtbaren Seitentext. Diese Signale entsprechen Googles dokumentierter Auszeichnung für abonnementschranke Artikel ([Google Search Central](https://developers.google.com/search/docs/appearance/structured-data/paywalled-content)). Kandidaten mit expliziten Bezahlschranken, gesperrten Antworten oder unklarem Zugriff werden ausgeblendet. Nur bei positiver Freizugriffs-Auszeichnung oder ausreichend umfangreichem lesbarem Artikeltext ohne Paywall-Signal erscheint ein Treffer. Die Prüfung lädt nur einen begrenzten HTML-Anfang, prüft maximal 24 Top-Kandidaten parallel (bis zu 16 gleichzeitig) und cached das Prüfergebnis 15 Minuten, um Suchanfragen schnell zu halten. Das ist eine belastbare Erkennung auf Quelltextsignalen, aber keine Garantie für spätere Änderungen oder personalisierte Zugriffsbedingungen. Die App übernimmt keine Volltexte.

Jeder Treffer trägt einen Score von 0 bis 100 mit Verlauf von Rot (niedrig) bis Grün (hoch). Der Score vergleicht die stärksten erkannten Themenbegriffe in Metadaten und misst thematische Nähe, nicht den vollständigen Text. Eine kleine Kalibrierung berücksichtigt, dass Überschriften und Beschreibungen oft nur einen Teil des Inhalts wiedergeben; schwache Treffer bleiben trotzdem klar niedriger bewertet. Ein niedriger Score bedeutet eine geringere erkannte Themenüberschneidung, schließt aber nicht aus, dass ein Artikel die gesuchten Informationen enthält. Treffer sind eigenständige Alternativen und keine Kopien oder wortgleichen Fassungen des Ausgangsartikels; Urheberrecht und Originalquelle sind zu beachten. Die Merkliste unterstützt lokal gespeicherte Themenordner und Artikel; gespeicherte Links führen weiterhin zur Verlagsseite, deren Verfügbarkeit sich später ändern kann.

## Bauen

Mit Android Studio öffnen und Gradle Sync ausführen. Erforderlich sind JDK 17, Android SDK Platform 35 und ein Emulator. Für eine physische Android-Verbindung sind Serveradresse und erlaubter Host in der Android-Konfiguration anzupassen.

## Freiwillige Unterstützung

Die App ist kostenlos nutzbar. Am Ende der Entdecken-Seite gibt es einen freiwilligen PayPal-Spendenlink mit `dome0903@yahoo.de` als Empfänger. Spenden sind keine Voraussetzung für die Nutzung.

## Datenschutz & Quellen

Der Server protokolliert Suchpfade ohne den eingegebenen Artikel-Link. Für die Suche werden erkannte Themenbegriffe an Google News RSS übermittelt; der vollständige Link wird nur vom lokalen Server zur Metadatenabfrage geöffnet. Quellen-URLs, Nutzungsrechte, robots/Publisher-Vorgaben und ein Impressum sind vor Veröffentlichung zu ergänzen.

## VS Code und Android-Emulator

VS Code-Erweiterungen: Kotlin (`fwcd.kotlin`) sowie Java/Gradle (`vscjava.vscode-java-pack`). Für einen Android-Emulator werden zusätzlich ein JDK 17 und Android Studio mit Android SDK Platform 35, Build Tools und einem Emulator-Image benötigt. Dieses Projekt lässt sich in VS Code bearbeiten; die Emulatorverwaltung erfolgt über Android Studio/Android SDK. Ein Build und Emulatorstart waren in der aktuellen Umgebung nicht möglich, weil weder JDK noch Android SDK/Emulator installiert sind.
