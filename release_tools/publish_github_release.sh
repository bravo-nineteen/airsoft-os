#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${1:-}"
if [[ -z "$KEY" || ! -f "$KEY" ]]; then
  echo 'Usage: bash release_tools/publish_github_release.sh /path/to/existing-signing-private.pem' >&2
  exit 2
fi
if ! command -v gh >/dev/null; then echo 'Install GitHub CLI: gh' >&2; exit 2; fi
if ! gh auth status >/dev/null 2>&1; then echo 'Run gh auth login first' >&2; exit 2; fi
KEY="$(realpath "$KEY")"
if [[ "$KEY" == "$ROOT/"* ]]; then
  echo 'For safety, store your signing private key OUTSIDE the source directory.' >&2; exit 2
fi
OUT="$ROOT/release-v$(cat "$ROOT/VERSION")"
mkdir -p "$OUT"
python3 "$ROOT/release_tools/build_release.py" "$ROOT" "$OUT" --signing-key "$KEY"
VERSION="$(cat "$ROOT/VERSION")"
gh release create "v${VERSION}"   "$OUT/aos-update.zip" "$OUT/aos-manifest.json" "$OUT/aos-manifest.sig"   --repo bravo-nineteen/airsoft-os --title "AOS ${VERSION} — Resizable Widgets"   --notes-file "$ROOT/RELEASE_NOTES.md" --draft
printf 'Draft created. Review at https://github.com/bravo-nineteen/airsoft-os/releases
'
