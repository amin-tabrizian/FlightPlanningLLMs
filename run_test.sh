#!/usr/bin/env bash
# Smoke-test pipeline: 1 warmup run + 1 ablation run per model, all models.
# Override models:  MODELS="gpt-4.1 claude-haiku-4-5" bash run_test.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODELS=${MODELS:-"gpt-4.1 o4-mini o3-mini claude-haiku-4-5 deepseek-r1"}
PY=.venv/bin/python

mkdir -p results logs

for m in $MODELS; do
  echo
  echo "=========================================="
  echo "=== Model: $m"
  echo "=========================================="

  echo "--- Resetting RAG DB ---"
  $PY -c "from rag.db import engine; from rag.models import Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine); print('reset ok')"

  echo "--- Warmup test ($m) ---"
  $PY drivers/run_warmup_test.py "$m" 2>&1 | tee "logs/warmup_test_${m//\//_}.log"

  echo "--- Ablation test ($m) ---"
  $PY drivers/run_ablation_test.py "$m" 2>&1 | tee "logs/ablation_test_${m//\//_}.log"
done

echo
echo "All models done. Results in results/, logs in logs/."
