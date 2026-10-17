# Door Stein Bridge 0.3.0 – lokaler Not-Aus und Audit

**Nur Test-Helper, keine echten Schlösser.**

## Neuer lokaler Not-Aus
Unter **Einstellungen → Apps → Door Stein Bridge → Konfiguration** kann `emergency_stop: true` gesetzt werden. Nach **Speichern und Neustart** fragt die Bridge keine neuen Aufträge ab und führt keine Aktionen aus. Dieser Schalter wirkt unabhängig vom Cloudflare-Not-Aus. Zum Fortsetzen `false` setzen und erneut starten. Bereits laufende Impulse werden durch einen Konfigurationswechsel nicht unterbrochen.

Cloudflare verfügt bereits über einen serverseitigen Not-Aus (`/api/admin/test-mode`); dieser verhindert neue Aufträge und liefert der Bridge `emergency_stop: true`. **Eine Admin-Oberfläche für den Not-Aus ist nicht Bestandteil dieses Bridge-Updates.**

## Lokales Audit
Die Datei `/data/processed.sqlite3` enthält zusätzlich `bridge_audit` mit `job_id`, `door_id`, `event`, `detail`, `created_at`. Ereignisse: `claimed_locally`, `duplicate_rejected`, `pulse_finished`, `ack_completed`, `error`. Das Audit speichert keine Tokens oder Passkeys. Es ist noch keine Audit-Anzeige in der PWA implementiert. Cloudflare protokolliert bereits Anfragen und Bestätigungen in `audit_log`.

## Selbsttests
Die fünf isolierten Selbsttests bleiben erhalten (`security_selftest: true`). Sie können nach erfolgreicher Validierung mit `security_selftest: false` deaktiviert werden. Wir sollten sie **nicht endgültig entfernen**, sondern als optionale Regressionstests behalten. Sie schalten keine Helper.

## Grenzen
Das lokale Audit und der Not-Aus müssen auf dem echten Home Assistant noch getestet werden. Ein nach `pulse_finished` fehlgeschlagenes ACK wird als Fehler protokolliert und nicht nachträglich als sicher abgebrochen gemeldet; eine verlässliche Worker-seitige Darstellung unklarer Zustände erfordert ein späteres Protokoll-Update. Der lokale Not-Aus benötigt einen App-Neustart und ist kein Echtzeit-Hardware-Stopp.
