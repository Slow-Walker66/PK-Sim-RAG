#!/bin/zsh
set -e
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif [ -x "../.venv/bin/python" ]; then
  PYTHON="../.venv/bin/python"
else
  echo "Python environment is missing. Run setup.command first."
  exit 1
fi

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
if "$PYTHON" - <<'PY' >/dev/null 2>&1
import torch
raise SystemExit(0 if torch.backends.mps.is_available() else 1)
PY
then
  export EMBEDDING_DEVICE="${EMBEDDING_DEVICE:-mps}"
fi
"$PYTHON" scripts/update_knowledge_base.py

echo ""
echo "Update complete. You can start the app with start_demo.command."
