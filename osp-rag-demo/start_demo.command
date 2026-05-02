#!/bin/zsh
set -e
cd "$(dirname "$0")"

if [ -x ".venv/bin/streamlit" ]; then
  PYTHON=".venv/bin/python"
  STREAMLIT=".venv/bin/streamlit"
elif [ -x "../.venv/bin/streamlit" ]; then
  PYTHON="../.venv/bin/python"
  STREAMLIT="../.venv/bin/streamlit"
else
  echo "Streamlit is not installed. Run setup.command first."
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
exec "$STREAMLIT" run app.py --server.port 8501
