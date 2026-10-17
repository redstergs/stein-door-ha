# Door Stein Bridge – nur Testbetrieb

Dieses Add-on ist ausschließlich für Home-Assistant-Test-Helper vorgesehen. Es enthält keine Nuki- oder Doorman-Aktionen.

Konfiguration: Worker-URL, Polling-Intervall und Impulsdauer. Die beiden Secrets werden aus `/homeassistant/secrets.yaml` gelesen (`door_stein_api_token`, `door_stein_hmac_secret`). Die HA-Konfiguration ist nur lesbar eingebunden. Keine Secrets in Add-on-Optionen oder Logs.

Ein Auftrag wird vor der Testaktion persistent als verarbeitet markiert. Nach einem Absturz kann er verloren gehen; er wird nicht erneut geschaltet. Das Add-on ist nicht für echte Türhardware freigegeben.
