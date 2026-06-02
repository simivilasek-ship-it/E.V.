#!/usr/bin/env bash
# Sestaví Next.js frontend do web_dist/ pro produkci (statický export).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/web"
npm ci
npm run build

if [ ! -d "$ROOT/web/out" ]; then
  echo "Chyba: Next build nevytvořil 'web/out/'."
  echo "Tip: zkontroluj 'web/next.config.ts' (output: \"export\")."
  exit 1
fi

rm -rf "$ROOT/web_dist"
mv "$ROOT/web/out" "$ROOT/web_dist"
echo "==> Build hotov: $ROOT/web_dist"
