#!/usr/bin/env bash
# Sestaví React frontend do web_dist/ pro produkci.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/web"
npm ci
npm run build
echo "==> Build hotov: $ROOT/web_dist"
