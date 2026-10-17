# Door Stein Bridge v0.2.1 – Sicherheits-Selbsttests

Beim Start führt die Bridge standardmäßig fünf **isolierte** Sicherheitstests durch. Dabei werden keine HTTP-Anfragen, keine Home-Assistant-Schaltaktionen und keine Zugriffe auf die produktive Auftragsdatenbank ausgeführt. Die Tests nutzen einen eigenen Test-HMAC-Schlüssel und eine SQLite-In-Memory-Datenbank.

Geprüft werden gültige Signatur, doppelte ID, abgelaufener Auftrag, manipulierte Tür-ID und unbekannte Tür-ID.

Im Protokoll muss `SICHERHEITSTEST: 5/5 bestanden; KEINE Test-Helper geschaltet` stehen, gefolgt von `Door Stein Bridge 0.2.1: TESTBETRIEB`. Bei einem fehlgeschlagenen Test beendet sich der Bridge-Prozess vor dem Polling (Fail-Closed).

## Installation
1. ZIP entpacken und dessen **Inhalt** (nicht einen zusätzlichen Ordner) in das öffentliche Repository `redstergs/stein-door-ha` hochladen.
2. In Home Assistant unter Einstellungen → Apps → App-Store nach Updates suchen und auf 0.2.1 aktualisieren.
3. App starten und Protokoll prüfen.

`security_selftest: true` ist standardmäßig aktiviert. Die Cloudflare-Worker-Version und die vorhandenen Secrets bleiben unverändert.

## Grenzen
Dieser Test überprüft nur die lokalen Prüfpfade, nicht die tatsächliche Zustellung manipulierter Aufträge durch Cloudflare, den Neustart mit persistenter Duplikat-ID oder eine verlorene HA-API-Antwort. Die Bridge betätigt ausschließlich die zwei vorhandenen `input_boolean`-Test-Helper; echte Hardware darf nicht verbunden sein.
