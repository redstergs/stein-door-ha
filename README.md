# Door · Stein – Home Assistant Bridge

**Version 1.2.0-rc.1 · 30. Oktober 2026**  
**Kompatibler Worker:** v1.2.0-rc.1

Dieses Repository enthält das Home-Assistant-Add-on `door_stein_bridge/` zur sicheren Ausführung signierter Türbefehle und Synchronisierung des Schlossstatus mit dem Cloudflare Worker.

## Repository-Struktur

- `repository.yaml` – Metadaten des Home-Assistant-Add-on-Repositories
- `door_stein_bridge/config.yaml` und `build.yaml` – Add-on-Metadaten
- `door_stein_bridge/Dockerfile` und `run` – Container und Startskript
- `door_stein_bridge/bridge.py` – Bridge-Implementierung
- `door_stein_bridge/*tests.py`, `diagnose.py` – Selbsttests und Diagnostik
- `door_stein_bridge/ha_package_snippet.yaml` – Home-Assistant-Konfigurationsbeispiel

## Installation und Update

1. Repository als benutzerdefiniertes Add-on-Repository in Home Assistant hinzufügen und **Door Stein Bridge** installieren.
2. Zugangsdaten und Schlüssel ausschließlich lokal in der Add-on-Konfiguration hinterlegen, niemals im Git-Repository.
3. **Bei Update auf v1.2.0-rc.1 zuerst Worker v1.2.0-rc.1 deployen, danach die Bridge aktualisieren.**
4. Die bestehende lokale SQLite-Datei der Bridge beibehalten; sie enthält Replay-Schutzdaten und die persistente Startgeneration.

## Türsteuerung und Sicherheit

- **Hauseingang (`building`):** Signierter HMAC-v1-Impuls über `input_boolean.door_stein_hauseingang`.
- **Wohnungstür (`apartment`):** HMAC-v2-Aktionen `lock`, `unlock`, `open` über `lock.door_stein_wohnungstur_testschloss`.
- **Lokale Freigabe:** `input_boolean.door_stein_freigabe` muss aktiv sein.
- `open` wird nur bei unmittelbar zuvor bestätigtem Zustand `unlocked` ausgeführt; unbekannte oder verriegelte Zustände blockieren die Falle.
- Die absolute Auftragsgültigkeit wird unmittelbar vor der Schlossaktion erneut geprüft.
- Auftrags-IDs werden persistent gegen Wiederholung geschützt; ein fehlgeschlagener Öffnungsversuch wird nicht automatisch wiederholt.
- **`unlock` entriegelt absichtlich dauerhaft.** Es gibt kein automatisches Wieder-Versperren.
- Die Bridge steuert Home-Assistant-Entitäten; elektrische Impulsbegrenzung und reale Schlossmechanik sind gesondert zu prüfen.

## Schlossstatus-Synchronisierung

Die Bridge sendet `POST /api/ha/lock-state` mit HA-API-Bearer-Token. Beispielhafte Felder:

```json
{"state":"locked","boot_id":"UUID","seq":0}
```

Mögliche Zustände sind `locked`, `unlocked`, `unknown`. Beim Start und bei Änderungen wird der Status gemeldet; seit v1.1.2 zusätzlich spätestens alle **300 Sekunden** auch bei unverändertem Zustand. Erst eine erfolgreich bestätigte Übertragung setzt den Heartbeat-Zeitpunkt zurück. Fehlgeschlagene Meldungen werden mit derselben Sequenz erneut versucht.

Eine persistente, monoton steigende Bridge-Startgeneration in der lokalen SQLite-Tabelle `bridge_meta` verhindert zusammen mit Worker 1.1.9, dass verspätete Startmeldungen älterer Prozesse einen neueren Zustand überschreiben. Statusmeldungen autorisieren selbst keine Türaktion.

## Signiertes Auftragsprotokoll

Wohnungstüraktionen verwenden HMAC-v2, beispielsweise:

```json
{
  "id": "eindeutige-job-id",
  "door_id": "apartment",
  "version": 2,
  "action": "unlock",
  "expires_at": "2026-10-29T21:00:20Z",
  "signature": "64-stellige-hex-hmac-sha256"
}
```

Die Signatur ist HMAC-SHA256 über die UTF-8-Nachricht mit den durch Zeilenumbrüche getrennten Feldern `door-stein-v2`, `id`, `door_id`, `action`, `expires_at`. HMAC-v1 bleibt nur für den Hauseingang zulässig; V1-Aufträge für die Wohnungstür sind nicht erlaubt.

## Tests und Freigabestatus

- Gezielte Offline-Regressionen: `python audit_regression_tests.py` im Add-on-Verzeichnis.
- Weitere Diagnosen: `diagnostic_tests.py`, `security_selftest.py`, `status_sync_tests.py`.
- Die bisherigen Tests ersetzen keinen End-to-End-Test mit Cloudflare D1, Worker, Home Assistant und realer Schloss-Hardware.
- Vor dem Betrieb mit realer Hardware insbesondere Schlosszustand, Falle, Strom- und API-Ausfälle sowie mechanische Notöffnung prüfen.

## Versionshistorie

### 1.1.2 – 30.10.2026
- Regelmäßiger Schlossstatus-Heartbeat (300 Sekunden), auch ohne Zustandsänderung.
- Erneute absolute Ablaufprüfung unmittelbar vor HA-Schlossaktionen.
- Persistente Bridge-Startgeneration für geordnete Statusübernahmen.
- Kompatibel mit Worker v1.1.9; bestehende SQLite-Daten erhalten.

### 1.1.1 – Integrationskandidat
- Statusübertragung an `/api/ha/lock-state` mit Sequenz und Boot-ID.
- Wiederholung nicht bestätigter Meldungen und erneute Übertragung nach Wiederverbindung.

### 1.1.0 – Preview
- HMAC-v2-Aktionen `lock`, `unlock`, `open` für die Wohnungstür.
- HMAC-v1 für den Hauseingang beibehalten.


### 1.2.0-rc.1 – 30.10.2026

- Gemeinsame Release-Candidate-Version mit Worker v1.2.0-rc.1.
- Bridge-Funktionslogik gegenüber 1.1.2 unverändert; Heartbeat, Ablaufprüfung und persistente Statussequenzen bleiben bestehen.
- Vor Einsatz an realer Schloss-Hardware sind Integrations- und Hardwaretests erforderlich.
