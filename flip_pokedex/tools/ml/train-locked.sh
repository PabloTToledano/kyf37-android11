#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Run model export through build-locked.sh'; exit 1; }
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
bash "$ROOT/tools/test-host.sh"
"$ROOT/cache/ml-venv/bin/python" "$ROOT/tools/ml/prepare_photo_augment.py"
exec "$ROOT/cache/ml-venv/bin/python" "$ROOT/tools/ml/train_model.py"
