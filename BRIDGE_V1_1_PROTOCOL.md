# V2-Auftragsformat (Entwurf)

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

Die Signatur wird mit dem bestehenden HMAC-Schlüssel über die UTF-8-Bytes von
`door-stein-v2\\n{id}\\n{door_id}\\n{action}\\n{expires_at}` gebildet (hier `\\n` als Zeilentrenner dargestellt).

Bestehende V1-Jobs für `building` bleiben unverändert. V1-Jobs für `apartment` sind aus Sicherheitsgründen nicht mehr erlaubt.

Die Worker-Version muss vor der gemeinsamen Aktivierung angepasst werden.
