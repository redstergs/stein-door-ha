# Door Stein HA Bridge 0.3.2

Installation: Inhalt in öffentliches Repository `stein-door-ha` hochladen, App-Store neu laden, App auf 0.3.2 aktualisieren. Cloudflare Worker 0.9.0 vorher deployen.

Neun isolierte Diagnosefälle werden aus der Administratoroberfläche über separate signierte Diagnoseaufträge gestartet. Die fünf bisherigen Start-Selbsttests bleiben optional (`security_selftest`). Diagnosefälle verwenden keine HA-API-Schaltbefehle und keine produktiven Auftrags-IDs. Die Bridge führt weiterhin nur normale Öffnungsaufträge an die zwei Test-Helper aus.

**Wichtig:** Simulierte verlorene ACKs und HA-API-Fehler sind lokale Modelltests, kein Nachweis für Ende-zu-Ende-Verhalten. Das Audit in Cloudflare enthält Diagnoseerstellungen und Ergebnisse; die Bridge protokolliert ihre lokale Verarbeitung in SQLite.

## Korrektur 0.3.2
Das Python-Modul `diagnostic_tests.py` wird jetzt ausdrücklich ins Containerimage kopiert. In 0.3.1 war es im GitHub-Paket enthalten, fehlte jedoch im Dockerfile-COPY. Die frühere HTTP-405-Meldung ist hiervon unabhängig: bitte Worker v0.9.0 und seine D1-Migration prüfen, falls sie erneut auftritt. Diese Version führt keine neuen HA-Schaltaktionen ein.
