# Airsoft Operating System

Official AOS source repository and signed update distribution.

## Releases
Releases require three assets: `aos-update.zip`, `aos-manifest.json`, and `aos-manifest.sig`.
AOS verifies Ed25519 signatures using a public key pinned on each client.
Never commit private signing keys. Never treat GitHub checksums alone as signatures.

See `docs/UPDATES.md` for setup and publishing instructions.
