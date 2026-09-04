#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIRECTORY="/home/pramod/Projects/black_box"
LOG_DIRECTORY="${PROJECT_DIRECTORY}/logs"

mkdir -p "${LOG_DIRECTORY}"
cd "${PROJECT_DIRECTORY}"

source .venv/bin/activate
python3 -m data.instruments.download >> "${LOG_DIRECTORY}/instruments_$(date +%Y-%m).log" 2>&1
