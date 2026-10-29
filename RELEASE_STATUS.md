# Door Stein Bridge 1.1.1 – Integrationskandidat

Basis: Bridge 1.1.0 Preview. Neu: Status-Synchronisierung an Worker 1.1.0.

## Status-POST
`POST /api/ha/lock-state` mit Bearer HA API Token, JSON:
`{"state":"locked|unlocked|unknown","boot_id":"UUID","seq":0}`.
Erster Statusbericht je Bridge-Prozess mit seq=0, danach fortlaufend. Ein nicht bestätigter Bericht wird mit gleicher Sequenz erneut gesendet. Status wird aus der HA-Entität gelesen; bei Fehlern `unknown`. Nach Start und Wiederverbindung erfolgt erneute Übermittlung. Ein Statusbericht autorisiert niemals selbst eine Aktion.

## Unverändert
Hauseingangsimpuls; HMAC v1 für Hauseingang; HMAC v2 für Wohnungstür; lokale Freigabe; Replay-Schutz; unmittelbare Schlossprüfung vor `lock.open`; Audit.

## Prüfungen
Python-Syntaxprüfung und isolierte Status-Synchronisierungstests bestanden. **Kein End-to-End-Test** mit Cloudflare D1, Worker und Home Assistant. Keine produktive Freigabe; zuerst Worker-Migrationen und Integrationstests prüfen. Insbesondere Worker-ACK nach Jobablauf, Worker-Neustarts/Sequenzübernahme und die tatsächliche Sicherheitswirkung der Schloss-Falle müssen im Gesamtsystem getestet werden.
