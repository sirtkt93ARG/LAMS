#!/usr/bin/env bash
# Levanta todo en Mac/Linux. Uso: ./scripts/dev.sh   (o ./scripts/dev.sh prod)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Creá el entorno: python -m venv .venv"; exit 1; }
$PY -m pip install -e ".[api,lti]" -q
[ -f data/bank_demo.jsonl ] || $PY scripts/generate_bank.py
$PY scripts/gen_lti_keys.py
[ -f web/.env.local ] || cp web/.env.example web/.env.local
export PYTHONPATH="$PWD/src" SESSION_SECRET=dev-session-secret-cambiar-0123456789abcdef \
  LTI_HANDOFF_SECRET=dev-handoff-secret-cambiar-0123456789abcdef LTI_SECRET_KEY=dev-flask-secret \
  LTI_CONFIG="$PWD/lti_service/configs/lti.mock.json" WEB_URL=http://localhost:3000 TOOL_BASE=http://localhost:8200 LTI_SERVICE_URL=http://localhost:8200
if [ "${1:-}" = "prod" ]; then unset MATHEVAL_DEV || true; $PY scripts/seed_reviews.py; export NEXT_PUBLIC_DEV=0
else export MATHEVAL_DEV=1 NEXT_PUBLIC_DEV=1; fi
trap 'kill 0' EXIT
$PY -m uvicorn api.app.main:app --port 8000 &
$PY -m flask --app lti_service.app run --port 8200 &
$PY -m flask --app tools.mock_lms.app run --port 8300 &
(cd web && { [ -d node_modules ] || npm install; } && npm run dev) &
echo "Web: http://localhost:3000 · Aula simulada: http://localhost:8300 · Prueba: $PY scripts/smoke_http.py"
wait
