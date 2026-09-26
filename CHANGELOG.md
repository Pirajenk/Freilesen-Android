# Änderungsprotokoll

## 1.0.0 — 2026-09-26
- Grundgerüst als Android-App mit Kotlin und Jetpack Compose angelegt.
- Minimalistische Startansicht mit Linkfeld, Quellhinweis, Sprachfiltern, Beispielartikeln und Lesemodus umgesetzt.
- Interaktive Browser-Vorschau unter `preview/index.html` erstellt.
- Projektumfang, Entwicklungsstand und Umgang mit Paywalls in README dokumentiert.
- Vermerkt, dass Suche und Artikel derzeit Beispieldaten nutzen und eine Such-/Backend-Integration aussteht.
- Freiwilligen PayPal-Kaffeelink ergänzt; die App bleibt kostenlos.
- PayPal-Empfänger auf die angegebene E-Mail-Adresse umgestellt.
- Statische Beispieltreffer durch Metadatenanalyse und thematisch gefilterte Google News RSS-Suche (DE/EN) im lokalen Suchdienst ersetzt.
- Android-Oberfläche an den Suchdienst angebunden; Quellenlinks öffnen die Originalseite.
- Offensichtliche Plus-/Paywall-Markierungen werden aus den Suchtreffern gefiltert.
- SZ-Testlink geprüft: Seitentitel, Herausgeber, Beschreibung und Veröffentlichungsdatum erkannt; vier thematisch passende Archiv-/Mitgliederkartei-Berichte ausgegeben.
- GitHub-Projekt mit README, Änderungsprotokoll und VS-Code-Konfiguration vorbereitet.

## 1.0.1 — 2026-09-26
- Die Trefferlogik auf beliebige Themen umgestellt; NSDAP-spezifischer Filter entfernt.
- GDELT DOC als zweiten globalen Nachrichtenindex hinzugefügt.
- Bei Eingabe eines neuen Links werden laufende/alte Ergebnisse verworfen, damit keine Resultate zum vorherigen Link stehen bleiben.

## 1.0.2 — 2026-09-26
- Suchtreffer zeigen jetzt einen farbigen Themen-Score von 0 bis 100 (Rot bis Grün), in Browser-Vorschau und Android-Oberfläche.
- Score vergleicht normalisierte Themenbegriffe in Ausgangstitel, URL und öffentlicher Beschreibung mit Treffertitel und verfügbarer Beschreibung; er behauptet keinen Volltextvergleich.
- Die Bewertung berücksichtigt auch schwächere Themenbegriffe aus der Beschreibung im Nenner, damit ein zufälliger Teiltreffer nicht künstlich hoch wirkt.
- 100 Punkte sind nur für identische normalisierte Schlagwörter vorbehalten; reguläre thematische Treffer sind auf 99 begrenzt.
- Score-Limit und Einschränkungen in README dokumentiert.
