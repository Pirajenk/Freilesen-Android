# Änderungsprotokoll

## Build-/Entwicklungsumgebung — 2026-09-26
- Gradle Wrapper 8.11.1 ergänzt, damit Builds reproduzierbar aus dem Repository starten.
- Release-Konfiguration so angepasst, dass lokale Debug-Builds ohne veröffentlichtes Backend funktionieren.
- Java- und Kotlin-Bytecode-Ziele vereinheitlicht, damit der Build mit JDK 21 nicht an inkompatiblen JVM-Zielen scheitert.
- Fehlerhaften `Modifier.weight`-Aufruf in der Merkliste entfernt, der außerhalb eines Compose-Layout-Scopes den Kotlin-Build verhindert hat.
- Google-Mirror für Maven Central ergänzt, damit Abhängigkeiten auch bei nicht auflösbarem `repo.maven.apache.org` geladen werden können.

## Veröffentlichungsvorbereitung — 2026-09-26
- Aktives Google-Konto mit eingeschalteter 2-Faktor-Authentifizierung für die Play-Console-Registrierung ausgewählt; die Einrichtung ist noch nicht abgeschlossen.
- Android-Target-SDK und Compile-SDK auf API 36 angehoben; Android Gradle Plugin auf 8.9.1 aktualisiert.
- API-Endpunkt konfigurierbar gemacht: Debug nutzt weiterhin den lokalen Emulator; Release erfordert eine HTTPS-Adresse und bricht ohne diese bewusst ab.
- Suchanfragen der Android-App und Vorschau auf POST umgestellt, damit eingefügte Artikel-Links nicht in der Request-URL stehen; Anfragegröße, einfache IP-Ratenbegrenzung und gleichzeitige Suchläufe begrenzt.
- Port- und Health-Check für Render ergänzt; Render-Konfiguration vorbereitet, aber noch kein Dienst erstellt oder veröffentlicht.
- Hosting-Vorgabe auf den kostenlosen Tarif für den geschlossenen Test umgestellt; längere Netzwerk-Zeitlimits berücksichtigen den verzögerten Kaltstart des Gratisdienstes.
- Noch offen: Entwicklerkonto samt Vertragsannahme/Gebühr/Identitätsprüfung, HTTPS-Hosting, signierter App-Bundle-Build und Play-Store-Angaben.

## 1.0.7 — 2026-09-26
- Suchlogik liest Titel, URL, Open Graph, News-Schlagwörter sowie strukturierte Artikel-Tags und — wenn veröffentlicht — `articleBody` aus JSON-LD.
- Sucht parallel mit Titel und zweisprachigen Themenformulierungen in Google News RSS und GDELT; prüft bis zu 36 passende Themenfeeds und bis zu 48 Artikelzugriffe.
- Relevanzfilter lässt passende Artikel mit knappen Feed-Metadaten eher durch, verlangt aber weiter mindestens ein spezifisches gemeinsames Thema.
- Erreichbare Seiten ohne eindeutigen Zugriffsstatus können als „möglicherweise frei“ erscheinen; erkannte Paywalls, gesperrte und nicht erreichbare Seiten bleiben verborgen.
- Quellenkatalog auf 616 Feeds aus der CC0-Empfehlungssammlung erweitert.

## 1.0.6 — 2026-09-26
- 616 Quellen- und Blog-Feeds aus einer CC0-lizenzierten Empfehlungssammlung ergänzt, plus deutschsprachige freie Redaktionen und Blogs.
- Themenbezogene RSS-/Atom-Feeds werden zusätzlich zu Google News und GDELT nach passenden Beiträgen durchsucht; Feed-Ergebnisse werden zeitlich begrenzt gecacht.
- Startseite auf freie journalistische Stimmen ausgerichtet: „Wir unterstützen freien Journalismus und unabhängige Blogs.“
- Sorgfaltshinweise zeigen nur beobachtete Signale: genannte Autorenschaft, mehrere externe Artikelquellen sowie verlinkte Korrektur-/Transparenzseiten. Keine Sterne oder unbelegten Qualitätsurteile.
- Quellkatalog klar als kuratiert und nicht traffic-gerankt dokumentiert; pro Artikel gilt weiterhin eine eigene Paywall-Prüfung.
- Android und Vorschau nennen Blog-/Fachfeeds und zeigen die beobachteten Quellenhinweise.

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
# 2026-09-26

## Vorbereitung für UGREEN NAS und Play-Release

- Docker-Image für den Python-Suchdienst ergänzt; läuft als unprivilegierter Nutzer.
- Compose-Betrieb auf 768 MB RAM/2 CPU begrenzt (NAS-Dashboard zeigte nur 1,8 GB verfügbar), schreibgeschütztes Root-Dateisystem, keine Linux-Capabilities und begrenzte Logs.
- API-Port 8765 standardmäßig nur an die NAS-Loopback-Adresse gebunden; dadurch keine versehentliche direkte Internetfreigabe.
- Release-Build verlangt jetzt eine gültige HTTPS-Backend-URL und verweigert Platzhalter.
- README um NAS-Betrieb, Reverse-Proxy/TLS-Voraussetzungen und Einzelserver-Ausfallrisiko ergänzt.
- Noch nicht am NAS installiert oder öffentlich freigeschaltet: NAS-Anmeldung, Domain/DNS, Reverse-Proxy/Zertifikat und Routerfreigaben sind erforderlich. Keine Zugangsdaten oder Schlüssel ins Repository aufgenommen.
