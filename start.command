#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [ ! -d vendor/laya ]; then
  mkdir -p vendor
  git clone https://github.com/NandhaKishorM/laya.git vendor/laya
  git -C vendor/laya checkout c7527708f9f5220c669d8aa385077cd28d04708a
fi
if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r requirements-lock.txt -e ./vendor/laya
fi
open http://127.0.0.1:8877
exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8877
