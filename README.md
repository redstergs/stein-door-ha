# Door Stein Bridge 0.1.4 – Diagnose der S6-Umgebung

1. **Inhalt** dieser ZIP in das öffentliche GitHub-Repository `redstergs/stein-door-ha` hochladen. Keine Secrets hochladen.
2. Home Assistant → Einstellungen → Apps → App-Store → nach Updates suchen; Bridge auf **0.1.4** aktualisieren.
3. Bridge starten und die Logzeilen ab `Door Stein Bridge 0.1.4` mitteilen.

## Änderung

Die Diagnose läuft jetzt als regulärer S6-Service über `#!/usr/bin/with-contenv sh`, statt als Docker-`CMD`. Sie untersucht, ob die Supervisor-Variablen bei PID 1, in der S6-Umgebung oder im Python-Prozess vorhanden sind. **Nur Namen und Ja/Nein**, niemals Werte.

**Reiner Diagnosemodus**: keine Cloudflare-Abfrage, keine Schalterbetätigung, keine Türöffnung. Keine neuen Berechtigungen oder Zugangsdaten.
