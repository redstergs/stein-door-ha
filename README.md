# Door Stein Bridge 0.2.1

Version 0.2.1 ergänzt isolierte Sicherheitsselbsttests beim Start der Home-Assistant-App.

Installation: Inhalt dieses Repositorys in `redstergs/stein-door-ha` hochladen, HA App-Store neu laden, Version 0.2.1 aktualisieren und App-Protokoll prüfen.

Erwartet: fünfmal `SICHERHEITSTEST BESTANDEN` und `SICHERHEITSTEST: 5/5 bestanden; KEINE Test-Helper geschaltet`. Danach startet das normale 5-Sekunden-Polling mit ausschließlich zwei Test-Helpern.

Keine Secrets in das öffentliche Repository hochladen. Cloudflare Worker bleibt unverändert.
