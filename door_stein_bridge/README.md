# Door Stein Bridge 0.1.4 – S6-Diagnose

**Keine Türaktionen, kein Cloudflare-Polling.**

Diese Version verwendet statt des direkten Docker-CMD einen regulären S6-Service mit `#!/usr/bin/with-contenv sh`. Sie prüft ausschließlich, ob die vier erwarteten Supervisor-Variablennamen im Python-Prozess, im PID-1-Prozess und in S6-Umgebungsverzeichnissen vorhanden sind. Es werden **keine Werte** ausgegeben. Außerdem prüft sie wie zuvor nur API-HTTP-Statuscodes.

`homeassistant_api: true` und `hassio_api: true` bleiben unverändert. Es sind keine neuen Secrets erforderlich.

Wenn auch hier kein Token sichtbar ist, ist die Ursache nicht sicher identifiziert. Dann müssen die tatsächlich installierten App-Metadaten und Supervisor-Protokolle geprüft werden. Keine echte Türhardware anschließen.
