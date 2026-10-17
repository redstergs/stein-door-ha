# Door Stein Bridge 0.1.3 – native API-Diagnose

Diese Version untersucht, warum Home Assistant der Bridge trotz `homeassistant_api: true` keinen `SUPERVISOR_TOKEN` bereitstellt.

## Installation

Die Dateien **im Inhalt** dieses ZIPs in das öffentliche GitHub-Repository `stein-door-ha` hochladen. In Home Assistant den App-Store aktualisieren, Bridge auf **0.1.3** aktualisieren und starten. Danach die **neuen** Protokollzeilen ab `Door Stein Bridge 0.1.3` teilen.

## Sicherheit

- Reiner Diagnosemodus: kein Cloudflare-Polling, keine Türaktionen, keine Schalterbetätigung.
- Prüft nur Vorhandensein der Umgebungsvariablen, Konfigurationsmount und HTTP-Statuscodes der lokalen APIs.
- Keine Ausgabe von Secrets, Tokenwerten, HTTP-Antwortinhalten oder vollständigen Umgebungsvariablen.
- Es werden keine neuen Zugangsdaten benötigt.

Die API-Proben testen **nur** die Erreichbarkeit und liefern keinen Nachweis für die Berechtigung, Türaktionen auszuführen. Bei weiterhin fehlendem Token ist der nächste Schritt die Supervisor-App-Detailkonfiguration bzw. die Add-on-Laufzeitumgebung zu prüfen, bevor weitere Rechte vergeben werden.
