# Änderungsprotokoll

## 1.0.5 — 2026-09-26
- Erkennung an Google-/Schema.org-Paywall-Markup ausgerichtet: `isAccessibleForFree`, `hasPart`, Paywall-Selektoren und Premium-/Abo-Metadaten werden als Signale gelesen.
- Fehler in der Groß-/Kleinschreibung der JSON-LD-Erkennung behoben; strukturierte `isAccessibleForFree`-Werte werden jetzt tatsächlich erkannt.
- Unklare, gesperrte und Paywall-markierte Kandidaten werden ausgeblendet; die Oberfläche gibt diese Unsicherheit nicht mehr als Treffer aus.
- HTML-Prüfung auf 320 KB und fünf Sekunden begrenzt, auf zwölf relevante Kandidaten begrenzt und Ergebnisse 15 Minuten zwischengespeichert.
- Android blendet Antworten mit unbekanntem Zugriffsstatus ebenfalls defensiv aus.

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

## 1.0.3 — 2026-09-26
- Suchtreffer werden live auf der Verlagsseite auf Freizugriff geprüft; erkannte Paywalls und nicht verifizierbare Seiten werden ausgeschlossen.
- Vorschau und Android zeigen freie Zugänglichkeit erst nach dieser Prüfung an.
- Merkliste um lokal persistente Themenordner erweitert; Artikel können aus Treffern in Ordner gespeichert, geöffnet und entfernt werden.
- Datenschutzfreundliche Persistenz: Ordner und Artikelmetadaten bleiben lokal auf dem Gerät bzw. im Browser.

## 1.0.4 — 2026-09-26
- Suchanfragen verwenden alternative Themenbegriffe statt alle Hauptbegriffe zwingend zu verlangen; ein relevanter Themenanker reicht für einen Kandidaten.
- Die Live-Zugriffsprüfung unterscheidet bestätigten freien Zugriff von wahrscheinlich freiem Zugriff und schließt klare Paywall-Signale weiterhin aus.
- Unsichere Zugänglichkeit wird in Trefferkarte und Lesemodus ausdrücklich markiert.
- Die Suche prüft mehr Kandidaten parallel, um trotz Verlagssperren/uneindeutiger Seiten passende offene Alternativen zu finden.
- Kandidaten benötigen wieder mindestens zwei gemeinsame Themenbegriffe; klare S+-Treffer und inhaltlich nur zufällig überlappende Headlines werden so herausgefiltert.
- Hinweis zu Urheberrecht, Alternativcharakter, niedrigen Scores und Originalquelle in den Lesemodus aufgenommen.
- Score auf die zehn stärksten Themenbegriffe normalisiert und nur leicht optimistisch kalibriert; einzelne schwache Überschneidungen werden dadurch nicht stark aufgewertet.
- Suche in beiden Sprachen auf bis zu sieben Kernbegriffe erweitert; generische Begriffe allein gelten nicht als Themenanker. Englisches „party members“ wird gezielt als politischer Begriff erkannt, nicht als allgemeines „family members“.
