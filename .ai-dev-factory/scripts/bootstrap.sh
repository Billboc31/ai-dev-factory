```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> bootstrap: checking required tools"
for tool in git docker gh claude; do
  if ! command -v "$tool" &>/dev/null; then
    echo "ERROR: required tool not found: $tool" >&2
    exit 1
  fi
  echo "  ok: $tool"
done

echo "==> bootstrap: deploy/.env"
if [ ! -f deploy/.env ]; then
  cp deploy/.env.example deploy/.env
  echo "  created deploy/.env from example — edit it before starting services"
else
  echo "  deploy/.env already exists"
fi

echo "==> bootstrap: Python venv"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "  created .venv"
else
  echo "  .venv already exists"
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r services/control_api/requirements.txt
echo "  Python deps installed"

echo "==> bootstrap: runtime directory tree"
bash deploy/bootstrap.sh

echo "==> bootstrap: pid directory"
mkdir -p .ai-dev-factory/run

echo "==> bootstrap: complete"
```
