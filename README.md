# Door · Stein – Home Assistant Add-on-Repository (v1.0)

Dieses Repository enthält das Add-on **Door Stein Bridge** unter [`door_stein_bridge/`](door_stein_bridge/).

## Aufbau

- `repository.yaml`: Metadaten des Home-Assistant-Add-on-Repositories
- `door_stein_bridge/`: Add-on mit `config.yaml`, `Dockerfile`, `run`, `bridge.py` und Diagnoseskripten
- `door_stein_bridge/README.md`: technische Hinweise zur Bridge
- `RELEASE_STATUS.md`: Freigabestatus und offene Integrationstests

## Installation

Dieses Repository als benutzerdefiniertes Add-on-Repository in Home Assistant hinzufügen und **Door Stein Bridge** installieren. Die notwendigen Zugangsdaten ausschließlich in der lokalen Konfiguration bereitstellen, nicht in Git committen.

Die Bridge schaltet ausschließlich die HA-Helper; physische Türöffner benötigen getrennte HA-Automationen und hardwareseitige Impulsbegrenzung.

**Freigabestatus:** Release Candidate, siehe `RELEASE_STATUS.md`.
