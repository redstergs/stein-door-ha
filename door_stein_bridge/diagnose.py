"""Safe startup diagnostics: never print secrets or execute door commands."""
import json
import logging
import os
import socket
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('door-stein-diagnostics')


def yes(value):
    return 'ja' if value else 'nein'


def main():
    log.info('Door Stein Bridge 0.1.2 – reiner Diagnosemodus; KEINE Türaktionen, KEIN Polling')
    log.info('SUPERVISOR_TOKEN vorhanden: %s', yes(bool(os.environ.get('SUPERVISOR_TOKEN'))))
    log.info('HASSIO_TOKEN vorhanden: %s', yes(bool(os.environ.get('HASSIO_TOKEN'))))
    log.info('SUPERVISOR_API vorhanden: %s', yes(bool(os.environ.get('SUPERVISOR_API'))))
    log.info('HASSIO_API vorhanden: %s', yes(bool(os.environ.get('HASSIO_API'))))
    log.info('/data/options.json vorhanden: %s', yes(Path('/data/options.json').is_file()))
    try:
        options = json.loads(Path('/data/options.json').read_text(encoding='utf-8'))
        filename = options.get('secrets_file', 'secrets.yaml')
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError('Ungültiger secrets_file-Dateiname')
        path = Path('/homeassistant') / filename
        log.info('Secrets-Datei im HA-Konfigurationsmount vorhanden: %s', yes(path.is_file()))
        log.info('Polling-Konfiguration lesbar: ja')
    except Exception as exc:
        log.warning('Konfiguration nicht vollständig lesbar: %s', type(exc).__name__)
    for hostname in ('supervisor', 'homeassistant'):
        try:
            socket.getaddrinfo(hostname, None)
            log.info('DNS %s erreichbar: ja', hostname)
        except OSError:
            log.info('DNS %s erreichbar: nein', hostname)
    log.info('Diagnose abgeschlossen. App bleibt ohne Türaktionen gestartet.')
    import time
    while True:
        time.sleep(3600)


if __name__ == '__main__':
    main()
