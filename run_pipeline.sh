#!/usr/bin/env bash
# Reproduce the whole ML pipeline + test suite.
set -euo pipefail
cd "$(dirname "$0")"
python ml/build_dataset.py >/dev/null
python ml/train_embedding.py >/dev/null
python ml/evaluate.py >/dev/null
python ml/train_supervised.py --smoke >/dev/null   # pipeline smoke test on SIMULATED labels
python -m pytest tests -q --ignore=tests/e2e
echo "pipeline + tests OK"
