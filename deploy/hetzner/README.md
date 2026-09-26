# Freilesen API auf einem Hetzner VPS

Diese Konfiguration hält den Python-Dienst im privaten Docker-Netz. Öffentlich erreichbar sind nur Caddys Ports 80 und 443. Caddy fordert nach korrekter DNS-Einrichtung automatisch TLS-Zertifikate an und erneuert sie. Der API-Container ist auf 768 MB RAM begrenzt und akzeptiert höchstens zwei gleichzeitige Suchläufe.

## Voraussetzungen

- Hetzner Cloud Server mit Ubuntu 24.04 LTS; CX23 (2 vCPU, 4 GB RAM) ist ein passender Startpunkt für geringe bis mittlere Nutzung.
- Eine Domain oder Subdomain, deren A-Eintrag auf die öffentliche IPv4-Adresse des Servers zeigt. Ein AAAA-Eintrag darf nur angelegt werden, wenn IPv6 auf dem Server korrekt eingerichtet ist.
- Ein SSH-Schlüsselpaar. Für den SSH-Zugang ausschließlich Schlüssel verwenden und Passwortanmeldung deaktivieren.
- Docker Engine mit Docker Compose Plugin.

## Firewall

In der Hetzner Cloud Firewall nur eingehendes TCP 22 (SSH), TCP 80 und TCP 443 sowie UDP 443 erlauben. Den SSH-Zugang möglichst auf die eigene feste IP-Adresse beschränken. Keine Serververwaltungs- oder Docker-Ports freigeben. Ausgehender Internetverkehr wird für Artikel- und Feed-Abfragen benötigt.

## Start

1. Repository auf dem Server unter `/opt/freilesen` auschecken.
2. Im Ordner `deploy/hetzner` `.env.example` nach `.env` kopieren und `FREILESEN_DOMAIN` auf die konfigurierte Domain setzen.
3. Vom Ordner `/opt/freilesen` aus starten:

   ```sh
   docker compose -f deploy/hetzner/compose.yaml up -d --build
   ```

4. Erreichbarkeit prüfen: `https://<deine-domain>/healthz` muss `{"ok": true}` zurückgeben.
5. Für Android-Release-Builds die API-Adresse als `https://<deine-domain>` eintragen.

Für Updates zuerst den gewünschten Commit aus dem öffentlichen GitHub-Repository auschecken und anschließend denselben Compose-Befehl erneut ausführen. Caddy speichert Zertifikate in den Docker-Volumes `caddy_data` und `caddy_config`; diese Volumes nicht löschen.

## Betrieb

Der Dienst verwendet kein persistentes Artikeldaten- oder Nutzerkonto. Such- und Feed-Caches liegen nur im Arbeitsspeicher. Logs enthalten keine vollständigen Artikel-URLs. Updates für Ubuntu, Docker und Container-Images müssen regelmäßig eingespielt werden. Ein einfacher einzelner VPS ist kein hochverfügbares Setup; bei Server- oder Anbieter-Ausfällen ist die Suche vorübergehend nicht erreichbar.
