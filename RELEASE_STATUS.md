# Door Stein HA Bridge v1.1.0 – Entwicklungsstand

**Nicht für den produktiven Türbetrieb freigegeben.** Lokal syntaktisch geprüft und 9 isolierte Sicherheitsselbsttests bestanden; keine End-to-End-Tests gegen den Cloudflare Worker oder echtes Nuki-Schloss.

- Legacy v1-Aufträge ausschließlich für `building` (Hauseingang); alter `apartment`-Impuls wird abgelehnt.
- V2-Wohnungstüraufträge: `version: 2`, `door_id: apartment`, `action: lock|unlock|open`; HMAC-SHA256 über `door-stein-v2\n{id}\n{door_id}\n{action}\n{expires_at}`.
- Testschloss: `lock.door_stein_wohnungstur_testschloss` (exakte Home-Assistant-Entity-ID).
- Lokale Freigabe vor Befehlen; `open` nur bei unmittelbar erneut geprüftem `unlocked`.
- `lock` und `unlock` erwarten bestätigten HA-Zustand; `open` hat **keine physische Erfolgssensorik** und wird nur als gesendeter Befehl protokolliert.
- Kein automatischer Wiederholungsversuch bei unklarem Ausgang. Vorhandener Audit-/Duplikatschutz bleibt erhalten.

## Noch offen für die gemeinsame Worker-Version

- Worker muss V2-Jobs samt Aktion korrekt autorisieren und signieren; die bisherige Worker-Version sendet diese nicht.
- Bridge→Worker Status-Synchronisierung, inklusive Start, Zustandsänderung und Reconnect, benötigt einen abgestimmten API-Endpunkt und wird **noch nicht** bereitgestellt.
- Ein eigener ACK-Status `command_sent` statt `completed` für Falleziehen muss im Worker-Protokoll ergänzt werden. Aktuell bedeutet `completed` bei `open` lediglich, dass HA den Service-Aufruf angenommen hat, **nicht**, dass die Tür physisch geöffnet wurde.
- End-to-End-, Fehlermodus- und Recovery-Tests vor Deployment.
