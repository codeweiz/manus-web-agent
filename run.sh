#!/bin/bash
# Production startup script

exec uvicorn manus_web_agent.app:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 5
