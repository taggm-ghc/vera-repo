#!/usr/bin/env bash
# One-command launch of the VERA demo page (M7). Loads the latest evaluated run from Postgres
# (vera_vjay.runs.eval_metrics); falls back to a clearly-labelled FIXTURE with the reason shown.
#   ./run_demo.sh            # port 8502
#   ./run_demo.sh 8600       # custom port
#   VERA_DEMO_SOURCE=fixture ./run_demo.sh   # force the fixture
#   NO_BROWSER=1 ./run_demo.sh               # do not open a browser
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-${PORT:-8502}}"
if [[ -z "${VIRTUAL_ENV:-}" && -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi
if [[ -f .env ]]; then set -a; . ./.env; set +a; fi   # EXTERNAL_DB_URL for the DB load
URL="http://localhost:${PORT}/vera_demo"
echo "VERA demo: ${URL}"
if [[ -z "${NO_BROWSER:-}" ]]; then
    ( sleep 3; (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v wslview >/dev/null && wslview "$URL") || true ) >/dev/null 2>&1 &
fi
exec streamlit run streamlit_app.py --server.port "$PORT" --server.headless true \
    --browser.gatherUsageStats false
