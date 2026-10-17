# Door Stein Bridge v0.1.2 – Diagnose

Diese Version dient ausschließlich der Diagnose, warum die Supervisor-Token-Umgebungsvariablen fehlen. **Sie fragt keine Öffnungsaufträge ab und betätigt keine Test-Helper oder Türhardware.**

## Update

1. Inhalt dieses ZIPs in das öffentliche Repository `redstergs/stein-door-ha` hochladen (insbesondere `door_stein_bridge/config.yaml`, `Dockerfile`, `diagnose.py`).
2. Home Assistant → Einstellungen → Apps → App-Store → Repository aktualisieren / nach Updates suchen.
3. Bridge auf **0.1.2** aktualisieren und starten.
4. Im Protokoll nach `Door Stein Bridge 0.1.2 – reiner Diagnosemodus` suchen und die Diagnosezeilen teilen.

Die Diagnose gibt nur **ja/nein** für die Verfügbarkeit von Token-Variablen, Konfigurationsdateien und DNS aus. Sie liest keine Secret-Werte aus und gibt keine Tokens aus.

**Hinweis:** Diese Version ersetzt vorübergehend die funktionale Bridge, um die Ursache sicher einzugrenzen. Nach der Diagnose erstellen wir eine korrigierte Betriebsfassung.
