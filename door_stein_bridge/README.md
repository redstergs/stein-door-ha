# Door Stein Bridge v0.2.0 (Test)

Fragt den privaten Door-Stein-Worker alle `poll_seconds` Sekunden nach Öffnungsaufträgen. Prüft HMAC-SHA-256, Tür-ID, Ablaufzeit und persistente Auftrags-ID. Betätigt ausschließlich `input_boolean.door_stein_hauseingang` und `input_boolean.door_stein_wohnungstuer` und bestätigt das Ergebnis beim Worker.

Die Secrets `door_stein_api_token` und `door_stein_hmac_secret` werden aus `/homeassistant/secrets.yaml` gelesen. Der HA-API-Token wird automatisch über den S6-Dienst `with-contenv` bereitgestellt. Keine Zugangsdaten ins Repository hochladen.

**Achtung:** Dies ist ein Testsystem und noch keine Freigabe für echte Türhardware.
