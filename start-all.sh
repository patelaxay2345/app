#!/bin/bash
echo "Starting both backend and frontend..."
echo "Backend: http://localhost:8001"
echo "Frontend: http://localhost:3000"
echo ""

# Start backend in background
cd backend
source venv/bin/activate 2>/dev/null || . venv/bin/activate
uvicorn server:app --reload --port 8001 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Start frontend
cd frontend
yarn start &
FRONTEND_PID=$!

echo ""
echo "Both servers started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop both servers, run: kill $BACKEND_PID $FRONTEND_PID"

wait
