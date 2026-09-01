#!/usr/bin/env bash
# Runs the full BAT test suite via pytest.
#
# Usage:
#   scripts/run_testsuit.sh            # run everything
#   scripts/run_testsuit.sh -k scoring # forward extra args to pytest
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 -m pytest tests/ "$@"
