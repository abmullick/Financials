#!/bin/bash
# Render deployment start script

cd /app/retirals
uvicorn src.main:app --host 0.0.0.0 --port 8080
