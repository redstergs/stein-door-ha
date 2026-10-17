# Door Stein HA Bridge v0.3.3

**Nur Testbetrieb:** Ausschließlich die zwei bisherigen Home-Assistant-`input_boolean`-Helper; keine echten Türschlösser.

## Änderungen gegenüber v0.3.2
- Lokales Audit in `/data/processed.sqlite3`: Bereinigung beim Start und anschließend einmal täglich; höchstens 1.000 Audit-Ereignisse und höchstens 30 Tage alte Ereignisse. Die Tabelle `processed` (persistenter Duplikat-/Replay-Schutz) wird **niemals** durch die Audit-Bereinigung gelöscht.
- Fehler im Diagnose- und Auftrags-Polling: erste Fehlermeldung sofort, bei fortdauernder Störung höchstens alle fünf Minuten eine Zusammenfassung; nach Wiederherstellung einmalige Entwarnung.
- Versionsmeldung in der Bridge korrigiert auf 0.3.3.
- Bestehende neun Diagnosetests, S6-Tokenweitergabe und Öffnungslogik unverändert.

## Installation
Alle Dateien in das öffentliche Repository `redstergs/stein-door-ha` übernehmen, Home-Assistant-App-Store aktualisieren und Bridge auf 0.3.3 aktualisieren. Der Worker v0.9.0 bleibt unverändert.

## Prüfung
Im Startprotokoll muss `Door Stein Bridge 0.3.3` und `Audit-Pflege` erscheinen. Danach in der Cloudflare-Systemdiagnose den Test `Gültige Signatur` ausführen und prüfen, dass kein Helper geschaltet wird. Anschließend können alle neun Tests erneut ausgeführt werden.

**Hinweis:** Das Home-Assistant-App-Protokoll selbst wird nicht gelöscht; dessen Rotation verwaltet die Container-/Supervisor-Umgebung. Die Begrenzung bezieht sich auf die lokale SQLite-Audittabelle und wiederholte Polling-Fehlermeldungen. Die Diagnosehistorie in Cloudflare D1 ist davon nicht betroffen.
