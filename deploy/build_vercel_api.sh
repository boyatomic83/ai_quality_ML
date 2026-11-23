#!/usr/bin/env bash
# Assemble a clean folder for deploying the FastAPI backend to Vercel.
#
# Why a separate folder? Vercel uploads the whole project directory and has no
# tree-shaking for Python, so we copy ONLY what the API needs (no raw data,
# notebooks, venv or node_modules).
#
# Usage (from the project root):
#   bash deploy/build_vercel_api.sh
#   cd build/aqi-forecast-api && npx vercel deploy --prod --yes --token "$VERCEL_TOKEN"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/aqi-forecast-api"   # folder name = Vercel project name

rm -rf "$OUT" && mkdir -p "$OUT/backend"
cp -r "$ROOT/src" "$ROOT/models" "$OUT/"
cp -r "$ROOT/backend/app" "$OUT/backend/"
touch "$OUT/backend/__init__.py"
cp "$ROOT/backend/requirements.txt" "$OUT/requirements.txt"
find "$OUT" -name "__pycache__" -type d -prune -exec rm -rf {} +

# Same Python minor version as training, so the saved model unpickles cleanly.
echo "3.13" > "$OUT/.python-version"

# LightGBM needs the OpenMP runtime (libgomp.so.1), which Vercel's Python
# environment lacks (in Docker we apt-install it). scikit-learn's Linux wheel
# ships a portable copy under a renamed file; we copy it and restore its
# library name with patchelf, then app.py loads it before importing LightGBM.
GOMP=$(ls "$ROOT"/.venv/lib/python3.*/site-packages/scikit_learn.libs/libgomp-*.so* | head -1)
mkdir -p "$OUT/lib"
cp "$GOMP" "$OUT/lib/libgomp.so.1"
"$ROOT/.venv/bin/patchelf" --set-soname libgomp.so.1 "$OUT/lib/libgomp.so.1"

# Vercel looks for an ASGI `app` in app.py at the project root.
cat > "$OUT/app.py" <<'PY'
"""Vercel entrypoint: re-export the FastAPI app (code lives in backend/app/main.py)."""
import ctypes
from pathlib import Path

# Load the bundled OpenMP runtime globally so LightGBM's native library finds it.
ctypes.CDLL(str(Path(__file__).parent / "lib" / "libgomp.so.1"), mode=ctypes.RTLD_GLOBAL)

from backend.app.main import app  # noqa: E402,F401
PY

echo "Built $OUT ($(du -sh "$OUT" | cut -f1))"
