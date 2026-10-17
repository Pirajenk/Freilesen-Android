# Freilesen

Minimalistische Android-App für frei zugängliche journalistische Perspektiven auf ein Thema.

## Lizenz

Freilesen ist unter der GNU Affero General Public License, Version 3.0 only (AGPL-3.0-only), lizenziert. Der vollständige Lizenztext steht in [LICENSE](LICENSE). Änderungen an einer öffentlich über ein Netzwerk angebotenen Version müssen deren Nutzern den entsprechenden Quellcode anbieten.

## Konzept

Freilesen umgeht keine Paywalls, entfernt keine Bezahlschranken und extrahiert keine geschützten Artikeltexte. Ein eingefügter Link wird anhand von Seitentitel, Beschreibung, Herausgeber, Datum, Schlagwörtern und verfügbarer strukturierter Metadaten ausgewertet. Die App zeigt passende Meldungen mit Metadaten und öffnet die Originalquelle. Erkannte Paywalls und nicht erreichbare Seiten werden ausgeblendet; Seiten, die erreichbar sind, deren Zugänglichkeit sich aber nicht eindeutig prüfen lässt, erscheinen klar markiert als „möglicherweise frei“. Die Zugänglichkeit kann sich nach der Prüfung ändern.

## Projekt

- Android-App: Kotlin und Jetpack Compose, Mindestversion Android 8.0 (API 26)
- Vorschau und lokaler Suchdienst: `python3 server.py` starten, danach `http://localhost:8765` öffnen
- Quellenverzeichnis: 616 kuratierte deutsch-/englischsprachige RSS-/Atom-Feeds in `data/source_catalog.json` (Google News RSS und GDELT ergänzen die Suche im Web)
- Android-Emulator: derselbe Server muss laufen; Android Studio/Emulator greift über `http://10.0.2.2:8765` zu
- Oberfläche: Deutsch/Englisch, Quellenfilter, Artikelliste, Lesemodus

## Öffentliche Browser-Demo

Die Browser-Oberfläche wird über GitHub Pages unter [pirajenk.github.io/Freilesen-Android](https://pirajenk.github.io/Freilesen-Android/) veröffentlicht. Die Suche benötigt zusätzlich das kostenlose Render-Backend aus `render.yaml`; dessen Instanz kann bei Inaktivität einschlafen und beim ersten Aufruf verzögert reagieren. Eingefügte Links werden zur Metadatenanalyse an das Backend übermittelt; Suchthemen werden an externe Nachrichtenindizes gesendet. GitHub Pages kann die Oberfläche selbst hosten, aber keinen Python-Suchdienst ausführen.

## Entwicklungsstand

Die Vorschau und die Android-Oberfläche verwenden `server.py`: Der Server liest Artikel-Metadaten und JSON-LD (Überschrift, Schlagwörter, Kurzbeschreibung und — falls veröffentlicht — Artikeltext), sucht parallel in Google News RSS und GDELT, fragt thematisch gefilterte Quellen aus einem 616er-Feedkatalog ab und ergänzt 31 einzeln dokumentierte unabhängige Redaktionen und Autorenblogs. Darunter sind Investigativprojekte, Fachpublikationen und eigenständige Blogs aus Deutschland und dem englischsprachigen Raum. Zusätzlich durchsucht er Substack, Medium, Ghost, WordPress, Buttondown, beehiiv, write.as, Blogspot und Blogger nach passenden Beiträgen, auch wenn Autorinnen und Autoren nicht vorab in einem Verzeichnis stehen. Die App kann Ergebnisse anschließend über „Alle“, „Deutsch“ und „English“ filtern. Die offene Plattform-Suche ist breiter, aber keine redaktionelle Qualitätsbestätigung; Autorenschaft, externe Belege sowie Korrektur-, Methoden- und Transparenzhinweise werden als beobachtbare Signale angezeigt. RSS-Feeds und Plattformen sind Entdeckungshinweise, kein Nachweis, dass ein einzelner Artikel kostenlos oder sachlich richtig ist.

Die Paywall-Prüfung liest maschinenlesbare Signale im HTML: insbesondere Schema.org `isAccessibleForFree`, `hasPart`/Paywall-Selektoren, Premium-/Abo-Metadaten, typische Paywall-Elemente und Hinweise im sichtbaren Seitentext. Diese Signale entsprechen Googles dokumentierter Auszeichnung für abonnementschranke Artikel ([Google Search Central](https://developers.google.com/search/docs/appearance/structured-data/paywalled-content)). Explizite Bezahlschranken und nicht erreichbare Seiten werden ausgeblendet. Eine erreichbare Seite ohne eindeutiges Freizugriffs-Merkmal darf als „möglicherweise frei“ erscheinen; Nutzer sehen den Unsicherheitsstatus und öffnen die Originalseite selbst. Die Prüfung lädt nur einen begrenzten HTML-Anfang, prüft maximal 48 relevante Kandidaten parallel und cached das Prüfergebnis 15 Minuten. Sorgfaltshinweise werden aus sichtbarer Autorenschaft, externen Quellenlinks und Korrektur-/Transparenzlinks abgeleitet; sie sind kein Wahrheits- oder Qualitätsurteil. Es gibt aktuell keine Community-Bewertungen. Die App übernimmt keine Volltexte.

Jeder Treffer trägt einen Score von 0 bis 100 mit Verlauf von Rot (niedrig) bis Grün (hoch). Der Score vergleicht die stärksten erkannten Themenbegriffe in Metadaten und misst thematische Nähe, nicht den vollständigen Text. Eine kleine Kalibrierung berücksichtigt, dass Überschriften und Beschreibungen oft nur einen Teil des Inhalts wiedergeben; schwache Treffer bleiben trotzdem klar niedriger bewertet. Ein niedriger Score bedeutet eine geringere erkannte Themenüberschneidung, schließt aber nicht aus, dass ein Artikel die gesuchten Informationen enthält. Treffer sind eigenständige Alternativen und keine Kopien oder wortgleichen Fassungen des Ausgangsartikels; Urheberrecht und Originalquelle sind zu beachten. Die Merkliste unterstützt lokal gespeicherte Themenordner und Artikel; gespeicherte Links führen weiterhin zur Verlagsseite, deren Verfügbarkeit sich später ändern kann.

## Bauen

Mit Android Studio öffnen und Gradle Sync ausführen. Erforderlich sind JDK 17 und Android SDK Platform 36. Für eine physische Android-Verbindung sind Serveradresse und erlaubter Host in der Android-Konfiguration anzupassen.

## Freiwillige Unterstützung

Die App ist kostenlos nutzbar. Am Ende der Entdecken-Seite gibt es einen freiwilligen PayPal-Spendenlink mit `dome0903@yahoo.de` als Empfänger. Spenden sind keine Voraussetzung für die Nutzung.

## Datenschutz & Quellen

Der Server protokolliert Suchpfade ohne den eingegebenen Artikel-Link. Für die Suche werden erkannte Themenbegriffe an Google News RSS übermittelt; der vollständige Link wird nur vom lokalen Server zur Metadatenabfrage geöffnet. Quellen-URLs, Nutzungsrechte, robots/Publisher-Vorgaben und ein Impressum sind vor Veröffentlichung zu ergänzen.

## VS Code und Android-Emulator

VS Code-Erweiterungen: Kotlin (`fwcd.kotlin`) sowie Java/Gradle (`vscjava.vscode-java-pack`). Für einen Android-Emulator werden zusätzlich ein JDK 17 und Android Studio mit Android SDK Platform 36, Build Tools und einem Emulator-Image benötigt. Dieses Projekt lässt sich in VS Code bearbeiten; die Emulatorverwaltung erfolgt über Android Studio/Android SDK.


## Rechtlicher Hinweis zu externen Links

Die App zeigt eigenständige Artikelalternativen und verlinkt zur Originalquelle; sie darf Paywalls weder umgehen noch geschützte Volltexte übernehmen. Eine Verlinkung ist nicht automatisch haftungsfrei: Nach der Rechtsprechung des EuGH kann es darauf ankommen, ob der Anbieter wusste oder hätte wissen müssen, dass das verlinkte Werk rechtswidrig veröffentlicht wurde; bei gewinnorientierter Verlinkung kann Kenntnis vermutet werden. Deshalb enthält die App einen Hinweis, dass sie nur technische Zugriffssignale prüft und die Rechteklärung beim jeweiligen Anbieter nicht ersetzt. Dieser Hinweis bietet selbst keinen Haftungsschutz. Vor Veröffentlichung sollten ein Impressum mit erreichbarer Kontaktmöglichkeit und ein Verfahren zum Prüfen und Entfernen konkreter beanstandeter Links ergänzt werden.

## Play-Store-Status (26.09.2026)

Noch nicht veröffentlichungsfähig: Die Play Console ist jetzt mit dem Google-Konto geöffnet, bei dem 2-Faktor-Authentifizierung aktiv ist. Für dieses Konto ist noch kein Entwicklerkonto registriert; die Registrierung verlangt die Auswahl eines Kontotyps, Entwickler-Kontaktdaten, Identitätsprüfung, Zustimmung zu den Play-Vertragsbedingungen und eine einmalige Registrierungsgebühr von 25 US-Dollar. Die Android-App benötigt außerdem einen dauerhaft erreichbaren HTTPS-Backend-Endpunkt. Es liegt in diesem Projekt weder ein signiertes Android App Bundle noch eine Release-Signatur vor. Der Target SDK wurde auf API 36 angehoben (Mindestanforderung für neue Apps ab 31.08.2026). Eine Veröffentlichung setzt Backend-Hosting, Release-Build und vollständige Store-Angaben (unter anderem Datenschutzrichtlinie und App-Inhalt) voraus.

Für den Release-Build muss die Produktions-API als HTTPS-URL angegeben werden, zum Beispiel `-PfreilesenApiBaseUrl=https://<eigene-api-domain>`. Der Debug-Build bleibt auf den lokalen Android-Emulator-Endpunkt eingestellt. Release-Builds ohne HTTPS-API werden absichtlich abgebrochen. Das Projekt zielt jetzt auf API 36 und verwendet Android Gradle Plugin 8.9.1 gemäß Android-16-SDK-Voraussetzung. Der Kaffeetipp ist als freiwilliger Beitrag ohne Zusatzfunktion oder freigeschaltete Inhalte formuliert; Google Play behandelt solche Zahlungen als direkte Tipp-Zahlung, wenn der volle Beitrag dem Creator zugutekommt.

### Eigenes NAS (UGREEN / Docker)

Im Projekt liegen ein `Dockerfile` und `docker-compose.yml` für den Python-Suchdienst. Der Container läuft ohne Root-Rechte, mit schreibgeschütztem Dateisystem und Ressourcenlimits. Port 8765 wird nur an `127.0.0.1` des NAS gebunden; der Suchdienst ist damit nicht direkt aus dem Internet erreichbar. In UGREEN Container Manager kann ein Projekt aus diesen Dateien gestartet werden. Danach lässt sich die Erreichbarkeit lokal über `/healthz` prüfen.

Für eine öffentliche App-API braucht es zusätzlich eine eigene Domain/Subdomain, einen HTTPS-Reverse-Proxy auf dem NAS und ein Zertifikat, zum Beispiel automatisch über Let’s Encrypt. Die Router-Freigabe darf nur den Reverse-Proxy (HTTPS/443; HTTP/80 nur für Zertifikatsvalidierung/Weiterleitung) erreichen, niemals die NAS-Verwaltung. Adminzugriff bleibt im Heimnetz oder VPN. Bis Domain, Proxy und öffentliche Erreichbarkeit sicher eingerichtet und geprüft sind, darf der Android-Release-Build nicht erstellt werden. Das NAS ist ein einzelner Ausfallpunkt; Strom-, Router-, ISP- oder Geräteausfälle stoppen die Live-Suche.

### Hetzner VPS (optional)

Für einen kostengünstigen, dauerhaft erreichbaren Host liegen Compose- und Caddy-Konfigurationen in [`deploy/hetzner`](deploy/hetzner). Der API-Container wird nicht direkt veröffentlicht; nur Caddy nimmt Verbindungen auf HTTP/HTTPS an und fordert für eine eigene Domain automatisch TLS-Zertifikate an. Vor dem Start werden ein Hetzner-Konto, ein Server, eine Domain mit passendem DNS-Eintrag und eine sichere SSH-Konfiguration benötigt. Die Schritte stehen in [`deploy/hetzner/README.md`](deploy/hetzner/README.md). Diese Konfiguration richtet noch keinen Cloudserver ein.

Für einen möglichst kostenlosen geschlossenen Test ist Render in Frankfurt mit dem Gratis-Tarif vorbereitet (`render.yaml`). Der Dienst schläft nach 15 Minuten ohne Anfragen ein und kann beim nächsten Aufruf etwa eine Minute zum Aufwachen brauchen; Render weist darauf hin, dass Gratis-Dienste für Tests und nicht für Produktions-Apps gedacht sind. Das kann den ersten Suchlauf spürbar verzögern. Für einen zuverlässigen öffentlichen Start wäre später ein dauerhaft laufender Dienst nötig; Render nennt dafür derzeit 7 US-Dollar pro Monat zuzüglich möglicher Mehrkosten für Bandbreite. Es wurde noch kein Hosting-Dienst angelegt.
