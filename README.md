# Door · Stein – Home Assistant Bridge v0.5.0

Sicherheitsupdate der Bridge v0.4.0. Die Bridge schaltet **ausschließlich** die zwei fest definierten HA-Test-Helper; keine echte Türhardware.

## Änderungen

- Beim Start und nach einem Fehler: beide Tür-Helper ausschalten und tatsächlichen `off`-Zustand über HA prüfen; bis zur erfolgreichen Prüfung keine Öffnungsimpulse.
- Bei fehlerhaftem finalem Ausschalten: begrenzte OFF-Wiederholungen und Sperre weiterer Öffnungen, bis ein sicherer Zustand wieder bestätigt ist.
- Vor dem Einschaltaufruf: lokale Freigabe und signierte Ablaufzeit erneut prüfen.
- Begonnene Einschaltversuche werden lokal protokolliert; bei unklarem Ausgang niemals ein irreführendes `cancelled`-ACK und niemals eine automatische Wiederholung des Impulses.
- Unverändert: HMAC, Replay-Schutz, Diagnosekanal, HA-Freigabe, HTTPS-Polling und Secrets.

## Update

Den Inhalt des ZIP in das öffentliche Add-on-Repository übernehmen und das Add-on auf v0.5.0 aktualisieren. Bestehende Konfiguration und Secrets beibehalten. **Keine** neuen Token nötig. Die Worker-Version v0.11.0 ist für das gemeinsame Release vorgesehen.

## Tests

Bestehende fünf isolierte Security-Selbsttests und vier zusätzliche lokale Recovery-/SQLite-Tests erfolgreich. Ein tatsächlicher HA-Neustart, Netzwerkunterbrechungen und ein vollständiger Ende-zu-Ende-Test müssen in der Testinstallation noch geprüft werden. Unabhängige elektrische Impulsbegrenzung ist erst mit der späteren Hardware festzulegen.
