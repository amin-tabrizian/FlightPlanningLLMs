#!/usr/bin/env bash
# Per-model loop:
#   1. drop_all + create_all the RAG DB
#   2. Warmup (150 runs, writes to DB)
#   3. Ablation (675 runs, read-only with --no_store, sequential)
#
# Override models:   MODELS="o4-mini claude-haiku-4-5 claude-sonnet-4-6" bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODELS=${MODELS:-"gpt-4.1 o4-mini o3-mini claude-haiku-4-5 claude-sonnet-4-6 deepseek-r1"}
PY=.venv/bin/python

mkdir -p results logs

for m in $MODELS; do
  echo
  echo "=========================================="
  echo "=== Model: $m"
  echo "=========================================="

  echo "--- Resetting RAG DB ---"
  $PY -c "from rag.db import engine; from rag.models import Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine); print('reset ok')"

  echo "--- Warmup ($m) ---"
  $PY drivers/run_warmup.py "$m" 2>&1 | tee "logs/warmup_${m//\//_}.log"

  echo "--- Ablation ($m) ---"
  $PY drivers/run_ablation.py "$m" --workers 1 2>&1 | tee "logs/ablation_${m//\//_}.log"
done

echo
echo "All models done. Aggregates in results/, logs in logs/."
