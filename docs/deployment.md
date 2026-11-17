# Deployment der öffentlichen Demo

Die Demo läuft mit denselben Compose-Dateien wie lokal, ergänzt um [`docker-compose.prod.yml`](../docker-compose.prod.yml):

- **Caddy** ist der einzige öffentliche Service (Port 80 und 443) und holt das HTTPS-Zertifikat automatisch bei Let's Encrypt. `db`, `app` und `web` sind nur im internen Netz erreichbar.
- **Antworten mit Claude Haiku 5.5** über einen API-Key, nie über ein Claude-Abo (AK-6.3).
- **Kostendeckel:** 5 USD pro Kalendermonat. Jeden Tag steht der Rest geteilt durch die verbleibenden Tage zur Verfügung, am Monatsanfang also rund 0,17 USD oder etwa 100 Fragen. Ist das Tagesbudget aufgebraucht, antwortet die Demo bis Mitternacht (UTC) mit einem Hinweis.
- **Rate-Limit:** 10 Fragen pro Stunde und Besucherin bzw. Besucher.
- **Datenschutz:** Die Fragen werden nicht geloggt. IP-Adressen bleiben nur für das Rate-Limit im Arbeitsspeicher, Caddy schreibt keine Zugriffslogs.

Die Werte stehen fest in `docker-compose.prod.yml`, damit eine aus `.env.example` kopierte `0` sie nicht ausschalten kann. Ändern heisst: die Datei ändern, committen, auf dem Server neu starten.

## 1. Was es braucht

| Was | Empfehlung | Kosten |
|---|---|---|
| Server | Linux-VM mit 4 vCPU und 8 GB RAM, Ubuntu 24.04, z. B. bei Hetzner Cloud (Standort in der EU) | rund 7 bis 15 € pro Monat |
| API-Key | In der [Claude Console](https://platform.claude.com) einen eigenen Workspace für die Demo anlegen, dort ein **Ausgabenlimit** (z. B. 5 USD pro Monat) setzen und einen API-Key nur für die Demo erstellen | nach Verbrauch, höchstens das Limit |
| Domain | Eigene Domain oder Subdomain mit einem A-Record auf die IP des Servers. Ohne eigene Domain geht auch `<ip-mit-bindestrichen>.sslip.io`, z. B. `203-0-113-7.sslip.io` | eigene Domain rund 10 bis 15 CHF pro Jahr |

Das Ausgabenlimit in der Console ist die zweite Sicherung: Es greift auch dann, wenn in der App etwas schiefgeht.

Der Server braucht rund 15 GB Speicher (Images, Datenbank 1,7 GB, Embedding-Modell rund 4 GB).

## 2. Server vorbereiten

```bash
ssh root@<server-ip>
adduser deploy && usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/ && chown -R deploy:deploy /home/deploy/.ssh
# Anmeldung nur mit SSH-Key: in /etc/ssh/sshd_config PasswordAuthentication no und PermitRootLogin no, dann
systemctl restart ssh

ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp && ufw enable
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

Docker veröffentlicht nur die Ports von Caddy; die anderen Services haben in der Produktion keine Ports auf dem Host.

## 3. Code und Konfiguration

Als `deploy` auf dem Server:

```bash
git clone https://github.com/juandroo1/Parlament-RAG.git
cd Parlament-RAG
cp .env.example .env && chmod 600 .env
```

In `.env` anpassen:

```bash
POSTGRES_PASSWORD=<zufällig, z. B. openssl rand -hex 24>
ANTHROPIC_API_KEY=<Key aus dem Demo-Workspace>
DEMO_DOMAIN=<demo.example.ch>
# Alle docker-compose-Befehle nutzen damit automatisch die Produktion.
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
```

Modell, Budget und Rate-Limit setzt `docker-compose.prod.yml`; sie gehören nicht in die `.env`.

## 4. Daten übertragen

Statt auf dem Server rund 17 Stunden neu zu indexieren, kommt die fertige Datenbank als Dump (rund 600 MB) hinüber.

Lokal (Datenbank im Container läuft):

```bash
scripts/db_transfer.sh dump                      # schreibt data/parlrag.dump (rund 1,5 Minuten)
scp data/parlrag.dump deploy@<server-ip>:Parlament-RAG/data/
```

Auf dem Server:

```bash
mkdir -p data
docker compose up -d --wait db
scripts/db_transfer.sh restore                   # rund 3 Minuten, zeigt am Schluss 42'515 Dokumente
```

`restore` bricht ab, wenn die Datenbank schon Dokumente enthält; mit `FORCE=1` wird sie ersetzt.

## 5. Starten und prüfen

```bash
docker compose up -d --build --wait --wait-timeout 300
docker compose ps                                # db, app, web und caddy "healthy"
docker compose exec app parlrag search "Test" --top 1   # lädt das Embedding-Modell vorab
```

Danach unter `https://<DEMO_DOMAIN>` eine Frage stellen. Beim ersten Start lädt Caddy das Zertifikat; das dauert einige Sekunden.

Kontrolle im Betrieb:

```bash
docker compose logs app | grep ask_request       # pro Frage Status, Tokens, Kosten; ohne Wortlaut
docker compose exec db psql -U parlrag -d parlrag \
  -c "SELECT day, requests, round(cost_usd::numeric, 4) FROM api_usage ORDER BY day DESC LIMIT 7"
```

## 6. Aktualisieren und abschalten

```bash
git pull && docker compose up -d --build --wait  # neue Version; die Migrationen laufen beim Start
docker compose down                              # Demo abschalten, Daten bleiben in den Volumes
```

## Nutzungsbedingungen der Daten

Die [Nutzungsbedingungen der Parlamentsdienste](https://www.parlament.ch/de/%C3%BCber-das-parlament/fakten-und-zahlen/open-data-web-services) verlangen:

- die Quelle «Parlamentsdienste der Bundesversammlung, Bern»;
- keinen Eindruck einer amtlichen Veröffentlichung;
- keine inhaltlichen Änderungen an den Daten;
- das Datum des Downloads.

Die Web-UI nennt Quelle, Stand und Datum des Downloads im Footer und weist darauf hin, dass sie keine amtliche Veröffentlichung ist. Die Ausschnitte der Quellen erscheinen im Wortlaut mit Link auf das Original. Die Antworten sind als Erzeugnis eines KI-Modells gekennzeichnet.
