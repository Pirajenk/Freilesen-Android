# Freilesen

Minimalistische Android-App für frei zugängliche journalistische Perspektiven auf ein Thema.

## Konzept

Freilesen umgeht keine Paywalls, entfernt keine Bezahlschranken und extrahiert keine geschützten Artikeltexte. Ein eingefügter Link wird anhand von Seitentitel, Beschreibung, Herausgeber, Datum, Schlagwörtern und verfügbarer strukturierter Metadaten ausgewertet. Die App zeigt passende Meldungen mit Metadaten und öffnet die Originalquelle. Erkannte Paywalls und nicht erreichbare Seiten werden ausgeblendet; Seiten, die erreichbar sind, deren Zugänglichkeit sich aber nicht eindeutig prüfen lässt, erscheinen klar markiert als „möglicherweise frei“. Die Zugänglichkeit kann sich nach der Prüfung ändern.

## Projekt

- Android-App: Kotlin und Jetpack Compose, Mindestversion Android 8.0 (API 26)
- Vorschau und lokaler Suchdienst: `python3 server.py` starten, danach `http://localhost:8765` öffnen
- Quellenverzeichnis: 616 kuratierte deutsch-/englischsprachige RSS-/Atom-Feeds in `data/source_catalog.json` (Google News RSS und GDELT ergänzen die Suche im Web)
- Android-Emulator: derselbe Server muss laufen; Android Studio/Emulator greift über `http://10.0.2.2:8765` zu
- Oberfläche: Deutsch/Englisch, Quellenfilter, Artikelliste, Lesemodus

## Entwicklungsstand

Die Vorschau und die Android-Oberfläche verwenden `server.py`: Der Server liest Artikel-Metadaten und JSON-LD (Überschrift, Schlagwörter, Kurzbeschreibung und — falls veröffentlicht — Artikeltext), sucht parallel mit mehreren Formulierungen in Google News RSS und GDELT und durchsucht zusätzlich bis zu 36 thematisch passende Feeds aus dem 616er-Katalog. Die Suche prüft deutsche und englische Begriffe. Der Katalog enthält 22 deutsche und 594 englisch markierte Feeds; die Zahl bezieht sich auf den RSS-Katalog, nicht auf die Sprachabdeckung der Suchindizes. Auswahl, Herkunft und Grenzen stehen in [`data/SOURCES.md`](data/SOURCES.md). RSS-Feeds erweitern die Entdeckung, gelten aber nicht als Nachweis, dass ein einzelner Artikel kostenlos ist.

Die Paywall-Prüfung liest maschinenlesbare Signale im HTML: insbesondere Schema.org `isAccessibleForFree`, `hasPart`/Paywall-Selektoren, Premium-/Abo-Metadaten, typische Paywall-Elemente und Hinweise im sichtbaren Seitentext. Diese Signale entsprechen Googles dokumentierter Auszeichnung für abonnementschranke Artikel ([Google Search Central](https://developers.google.com/search/docs/appearance/structured-data/paywalled-content)). Explizite Bezahlschranken und nicht erreichbare Seiten werden ausgeblendet. Eine erreichbare Seite ohne eindeutiges Freizugriffs-Merkmal darf als „möglicherweise frei“ erscheinen; Nutzer sehen den Unsicherheitsstatus und öffnen die Originalseite selbst. Die Prüfung lädt nur einen begrenzten HTML-Anfang, prüft maximal 48 relevante Kandidaten parallel und cached das Prüfergebnis 15 Minuten. Sorgfaltshinweise werden aus sichtbarer Autorenschaft, externen Quellenlinks und Korrektur-/Transparenzlinks abgeleitet; sie sind kein Wahrheits- oder Qualitätsurteil. Es gibt aktuell keine Community-Bewertungen. Die App übernimmt keine Volltexte.

Jeder Treffer trägt einen Score von 0 bis 100 mit Verlauf von Rot (niedrig) bis Grün (hoch). Der Score vergleicht die stärksten erkannten Themenbegriffe in Metadaten und misst thematische Nähe, nicht den vollständigen Text. Eine kleine Kalibrierung berücksichtigt, dass Überschriften und Beschreibungen oft nur einen Teil des Inhalts wiedergeben; schwache Treffer bleiben trotzdem klar niedriger bewertet. Ein niedriger Score bedeutet eine geringere erkannte Themenüberschneidung, schließt aber nicht aus, dass ein Artikel die gesuchten Informationen enthält. Treffer sind eigenständige Alternativen und keine Kopien oder wortgleichen Fassungen des Ausgangsartikels; Urheberrecht und Originalquelle sind zu beachten. Die Merkliste unterstützt lokal gespeicherte Themenordner und Artikel; gespeicherte Links führen weiterhin zur Verlagsseite, deren Verfügbarkeit sich später ändern kann.

## Bauen

Mit Android Studio öffnen und Gradle Sync ausführen. Erforderlich sind JDK 17, Android SDK Platform 35 und ein Emulator. Für eine physische Android-Verbindung sind Serveradresse und erlaubter Host in der Android-Konfiguration anzupassen.

## Freiwillige Unterstützung

Die App ist kostenlos nutzbar. Am Ende der Entdecken-Seite gibt es einen freiwilligen PayPal-Spendenlink mit `dome0903@yahoo.de` als Empfänger. Spenden sind keine Voraussetzung für die Nutzung.

## Datenschutz & Quellen

Der Server protokolliert Suchpfade ohne den eingegebenen Artikel-Link. Für die Suche werden erkannte Themenbegriffe an Google News RSS übermittelt; der vollständige Link wird nur vom lokalen Server zur Metadatenabfrage geöffnet. Quellen-URLs, Nutzungsrechte, robots/Publisher-Vorgaben und ein Impressum sind vor Veröffentlichung zu ergänzen.

## VS Code und Android-Emulator

VS Code-Erweiterungen: Kotlin (`fwcd.kotlin`) sowie Java/Gradle (`vscjava.vscode-java-pack`). Für einen Android-Emulator werden zusätzlich ein JDK 17 und Android Studio mit Android SDK Platform 35, Build Tools und einem Emulator-Image benötigt. Dieses Projekt lässt sich in VS Code bearbeiten; die Emulatorverwaltung erfolgt über Android Studio/Android SDK. Ein Build und Emulatorstart waren in der aktuellen Umgebung nicht möglich, weil weder JDK noch Android SDK/Emulator installiert sind.


## Rechtlicher Hinweis zu externen Links

Die App zeigt eigenständige Artikelalternativen und verlinkt zur Originalquelle; sie darf Paywalls weder umgehen noch geschützte Volltexte übernehmen. Eine Verlinkung ist nicht automatisch haftungsfrei: Nach der Rechtsprechung des EuGH kann es darauf ankommen, ob der Anbieter wusste oder hätte wissen müssen, dass das verlinkte Werk rechtswidrig veröffentlicht wurde; bei gewinnorientierter Verlinkung kann Kenntnis vermutet werden. Deshalb enthält die App einen Hinweis, dass sie nur technische Zugriffssignale prüft und die Rechteklärung beim jeweiligen Anbieter nicht ersetzt. Dieser Hinweis bietet selbst keinen Haftungsschutz. Vor Veröffentlichung sollten ein Impressum mit erreichbarer Kontaktmöglichkeit und ein Verfahren zum Prüfen und Entfernen konkreter beanstandeter Links ergänzt werden.

## Play-Store-Status (26.09.2026)

Noch nicht veröffentlichungsfähig: Die Android-App fragt derzeit ausschließlich `http://10.0.2.2:8765` ab, also den lokalen Entwicklungsserver des Emulators. Für Play Store braucht sie einen dauerhaft erreichbaren HTTPS-Backend-Endpunkt. Außerdem ist das aktuell angemeldete Google-Konto in Play Console noch beim Schritt zur Entwicklerkonto-Erstellung und verlangt zunächst die Aktivierung der 2-Faktor-Authentifizierung. Es liegt in diesem Projekt weder ein signiertes Android App Bundle noch eine Release-Signatur vor. Der aktuelle Target SDK ist 35; seit 31.08.2026 verlangt Google für neue Apps/API-Einreichungen mindestens API 36. Eine Veröffentlichung ist daher erst nach Backend-Hosting, API- und Release-Build-Anpassung, vollständigen Store-Angaben (unter anderem Datenschutzrichtlinie und App-Inhalt) und Einrichtung des Entwicklerkontos möglich.
