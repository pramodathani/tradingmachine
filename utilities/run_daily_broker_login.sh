#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIRECTORY="/home/pramod/Projects/tradingmachine"
LOG_DIRECTORY="${PROJECT_DIRECTORY}/logs"

mkdir -p "${LOG_DIRECTORY}"
cd "${PROJECT_DIRECTORY}"

source .venv/bin/activate
python3 -m utilities.broker_login >> "${LOG_DIRECTORY}/broker_login_$(date +%Y-%m).log" 2>&1
