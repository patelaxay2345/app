#!/bin/bash
cd backend
source venv/bin/activate 2>/dev/null || . venv/bin/activate
echo "Starting backend server on http://localhost:8001"
echo "API docs available at http://localhost:8001/docs"
echo "Press Ctrl+C to stop"
uvicorn server:app --reload --port 8001
