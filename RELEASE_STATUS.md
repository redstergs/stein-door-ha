# Door · Stein v0.99 – Sicherheits-Zwischenstand, NICHT freigegeben

Quellen: Worker v0.11.5 RC4, Bridge v0.5.0, Audit 2026-10-19.

## Umgesetzt
- B1: nach Fehler in einer Jobliste sofort abbrechen; globale Ausgangsprüfung vor jedem Job.
- B2: keine Öffnungsjob-Abholung, wenn Ausgänge nicht sicher AUS.
- B3: Abschalten und Verifikation vor Cloud-Diagnose.
- W1: atomare begrenzte Versuchs-Slots pro Einladung (Migration 0011).
- W2: globales, atomisches Login-Challenge-Budget (120/min) und gelegentliche Bereinigung; zusätzliche WAF-Begrenzung sinnvoll.
- Version 0.99 in Worker-Paket, UI, Health und Bridge-Metadaten.
- Keine Änderung an HA-Helper-Entity-IDs.

## Noch offen – NICHT für Produktivbetrieb
- Externe Browserbibliotheken weiterhin über jsDelivr. Offline kein Bezug und keine verifizierbare lokale Bündelung möglich.
- CSP erlaubt deshalb weiterhin externe Skripte und unsafe-inline.
- Kein Lockfile; tatsächlicher Build aus npm-Paketen nicht geprüft.
- Kein vollständiger Wiederholungslauf des unabhängigen Audits, keine echten D1-/WebAuthn-/HA-Tests.
- Keine Hardwareimpuls-Begrenzung in diesem Paket enthalten.

## Migration
`migrations/0011_security_limits.sql` vor Worker-Deployment ausführen. D1-Backup anlegen.

Die Archive sind Quellcode-Zwischenstände für Review/Staging, **keine produktionsfertige Freigabe**.
