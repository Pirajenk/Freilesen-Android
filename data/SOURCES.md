# Quellkatalog

`source_catalog.json` enthält derzeit 616 kuratierte RSS-/Atom-Feeds. Der Katalog kombiniert die CC0-lizenzierte Sammlung [plenaryapp/awesome-rss-feeds](https://github.com/plenaryapp/awesome-rss-feeds) mit einer kleinen, ausdrücklich als unabhängig/fachjournalistisch gekennzeichneten deutschsprachigen Startauswahl. Der aktuelle Import weist 22 Feeds als deutschsprachig und 594 als englischsprachig aus. Die deutsche RSS-Auswahl ist damit weiterhin deutlich kleiner; Google News und GDELT erweitern die Suche unabhängig davon über ihre Webindizes.

Die Liste ist **keine verifizierte Rangliste der meistbesuchten Websites**. Öffentlich sichtbare Traffic-Ranglisten decken meist nur die Spitze ab; eine vollständige Rangliste ist nicht frei und einheitlich verfügbar. Die Quellen sind daher eine kuratierte Entdeckungsliste, keine Aussage über Popularität, journalistische Qualität oder dauerhafte Kostenfreiheit.

Jeder Feed dient nur der Suche nach Beiträgen. Freier Zugriff wird weiterhin am konkreten Artikel geprüft. Ein Quellhinweis wie Byline, externe Belege, Korrektur- oder Transparenzseite ist beobachtbare Information, kein Wahrheitsurteil.

Der Katalog enthält keine Sterne oder vorgetäuschten Community-Urteile. Eine belastbare Community-Bewertung bräuchte nachvollziehbare Beiträge, Missbrauchsschutz, Moderation und eine gemeinsame Backend-Datenbank; die aktuelle Vorschau speichert nur lokal.

Neu erzeugen: `python3 tools/build_source_catalog.py`. Das Skript übernimmt nur Titel und öffentliche Feed-/Website-URLs aus dem CC0-Feedprojekt und markiert jeden Artikelzugriff weiterhin als prüfpflichtig.
