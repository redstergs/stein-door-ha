"""Door Stein 0.1.3: safe native API diagnostics, no polling or actions."""
import json
import logging
import os
import socket
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('door-stein-diagnostics')


def probe(label, url, token):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        with urlopen(Request(url, headers=headers), timeout=3) as response:
            log.info('%s: HTTP %s', label, response.status)
    except HTTPError as exc:
        log.info('%s: HTTP %s', label, exc.code)
    except (URLError, TimeoutError, OSError) as exc:
        log.info('%s: Verbindung fehlgeschlagen (%s)', label, type(exc).__name__)


def main():
    log.info('Door Stein Bridge 0.1.3 – API-Diagnose; KEIN Polling, KEINE Türaktionen')
    names = ('SUPERVISOR_TOKEN', 'HASSIO_TOKEN', 'SUPERVISOR_API', 'HASSIO_API')
    for name in names:
        log.info('%s vorhanden: %s', name, 'ja' if os.environ.get(name) else 'nein')
    token = os.environ.get('SUPERVISOR_TOKEN') or os.environ.get('HASSIO_TOKEN')
    log.info('Prozess-ID: %s; effektive UID: %s', os.getpid(), os.geteuid())
    for path in ('/data/options.json', '/homeassistant/secrets.yaml'):
        log.info('%s vorhanden: %s', path, 'ja' if Path(path).is_file() else 'nein')
    try:
        opts = json.loads(Path('/data/options.json').read_text())
        filename = opts.get('secrets_file', 'secrets.yaml')
        if isinstance(filename, str) and Path(filename).name == filename:
            log.info('Konfiguriertes Secret-File vorhanden: %s', 'ja' if (Path('/homeassistant') / filename).is_file() else 'nein')
        else:
            log.info('Ungültiger secrets_file-Eintrag')
    except (OSError, ValueError, TypeError):
        log.info('Optionsdatei nicht lesbar')
    for host in ('supervisor', 'homeassistant'):
        try:
            socket.getaddrinfo(host, None)
            log.info('DNS %s: ja', host)
        except OSError:
            log.info('DNS %s: nein', host)
    # Read-only GET only; never dump headers, response body, token, or environment.
    probe('Supervisor /supervisor/info ohne Token', 'http://supervisor/supervisor/info', None)
    probe('HA API /api/ ohne Token', 'http://homeassistant:8123/api/', None)
    if token:
        probe('HA API /api/ mit Supervisor-Token', 'http://supervisor/core/api/', token)
    else:
        log.info('API-Test mit Token übersprungen: kein Token vorhanden')
    log.info('Diagnose abgeschlossen; App bleibt ohne Türaktionen gestartet')
    while True:
        time.sleep(3600)


if __name__ == '__main__':
    main()
