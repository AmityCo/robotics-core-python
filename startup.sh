#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
