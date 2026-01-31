#!/bin/bash
# Development startup script with auto-reload

exec uvicorn manus_web_agent.app:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 0
