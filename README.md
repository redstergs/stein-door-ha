# Door Stein Bridge 0.2.0 – Home Assistant Testbetrieb

Dieses Repository enthält ausschließlich die Home-Assistant-App. Cloudflare Worker `stein-door` bleibt unverändert (v0.8).

## Aktualisieren
1. Inhalt dieses ZIPs ins **öffentliche** Repository `redstergs/stein-door-ha` hochladen (keine zusätzlichen Oberordner).
2. In Home Assistant → Einstellungen → Apps → App-Store → Repositories neu laden / nach Updates suchen.
3. Door Stein Bridge auf **0.2.0** aktualisieren und starten.
4. Protokoll prüfen: `Door Stein Bridge 0.2.0: TESTBETRIEB`.
5. Test-Helper `input_boolean.door_stein_hauseingang` und `input_boolean.door_stein_wohnungstuer` müssen bereits existieren.
6. In Door Stein die Teststeuerung durch Administrator freigeben und eine Türöffnung auslösen. Der jeweilige Helper sollte kurz auf `on`, dann `off` wechseln.

## Voraussetzungen
- Worker v0.8 mit `/api/ha/poll` und `/api/ha/ack`, Cloudflare-Secrets `HA_API_TOKEN` und `HA_HMAC_SECRET`.
- Home Assistant `/config/secrets.yaml` mit passenden `door_stein_api_token` und `door_stein_hmac_secret`.
- HA-Package mit beiden Test-Helpern.
- Keine echte Türhardware angebunden.

## Sicherheitsgrenzen
- Die Bridge kennt nur zwei `input_boolean`-Entitäten, keine Schloss-Entitäten.
- Aufträge werden vor dem Schalten persistent als verarbeitet markiert. Das verhindert doppelte Ausführung nach einem Neustart, kann aber bei Fehlern Aufträge verlieren.
- Die Bridge führt bei Fehlern keine neuen Schaltvorgänge aus. Nach Kommunikationsverlust kann ein Helper allerdings eingeschaltet bleiben; daher dürfen die Test-Helper niemals unmittelbar echte Hardware betätigen.
- Cloudflare-Not-Aus und Ablaufzeit werden beim Polling berücksichtigt. Ein bereits begonnener 1-Sekunden-Testimpuls kann durch eine spätere Sperre nicht rückwirkend verhindert werden.
- Ein Polling-Timeout nach dem serverseitigen Claim kann einen Auftrag verfallen lassen; kein automatisches Replay.
- Vor Anschluss echter Schlösser sind zusätzliche End-to-End-Sicherheits- und Ausfalltests erforderlich.
