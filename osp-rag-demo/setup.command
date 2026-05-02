#!/bin/zsh
set -e
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Setup complete. Next steps:"
echo "1. Put your API keys in .env or in ../.env"
echo "2. Double-click update_knowledge_base.command"
echo "3. Double-click start_demo.command"

