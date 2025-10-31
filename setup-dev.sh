#!/bin/bash

# Development Environment Setup Script for JobTalk Admin Dashboard
# This script automates the local development setup process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Header
clear
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║       JobTalk Admin Dashboard - Dev Setup             ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running from project root
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    log_error "Please run this script from the project root directory"
    exit 1
fi

log_info "Starting development environment setup..."
echo ""

# Step 1: Check Python
log_info "Step 1/7: Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION found"
else
    log_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Step 2: Check Node.js
log_info "Step 2/7: Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_success "Node.js $NODE_VERSION found"
else
    log_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Step 3: Check Yarn
log_info "Step 3/7: Checking Yarn installation..."
if command -v yarn &> /dev/null; then
    YARN_VERSION=$(yarn --version)
    log_success "Yarn $YARN_VERSION found"
else
    log_warning "Yarn not found. Installing yarn..."
    npm install -g yarn
    log_success "Yarn installed"
fi

# Step 4: Setup Backend
log_info "Step 4/7: Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || . venv/bin/activate 2>/dev/null || {
    log_error "Failed to activate virtual environment"
    exit 1
}

# Install backend dependencies
log_info "Installing backend dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
log_success "Backend dependencies installed"

# Create backend .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log_info "Creating backend .env file..."
    cat > .env << 'EOF'
# Database Configuration
MONGO_URL="mongodb://localhost:27017"
DB_NAME="recruitment_admin"

# JWT Configuration
JWT_SECRET="dev-jwt-secret-change-in-production-minimum-32-chars"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8

# Encryption Key (32 bytes for AES-256)
ENCRYPTION_KEY="dev-32-character-encryption-key"

# AWS SES Configuration (optional for local dev)
APP_NAME="JobTalk-Dev"
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
AWS_REGION="us-east-1"
SMTP_FROM_EMAIL="noreply@localhost.com"

# Application Settings
NODE_ENV="development"
PORT=8001
CORS_ORIGINS="*"
EOF
    log_success "Backend .env file created"
    log_warning "Please update backend/.env with your MongoDB connection string"
else
    log_success "Backend .env file already exists"
fi

cd ..

# Step 5: Setup Frontend
log_info "Step 5/7: Setting up frontend..."
cd frontend

# Install frontend dependencies
log_info "Installing frontend dependencies..."
yarn install --silent
log_success "Frontend dependencies installed"

# Create frontend .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log_info "Creating frontend .env file..."
    cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
EOF
    log_success "Frontend .env file created"
else
    log_success "Frontend .env file already exists"
fi

cd ..

# Step 6: Check MongoDB
log_info "Step 6/7: Checking MongoDB..."
if command -v mongosh &> /dev/null; then
    log_success "MongoDB Shell found"
    if mongosh --eval "db.version()" --quiet &> /dev/null; then
        log_success "MongoDB is running locally"
    else
        log_warning "MongoDB is not running locally"
        log_info "You can use MongoDB Atlas instead"
        log_info "Update backend/.env with your MongoDB Atlas connection string"
    fi
elif command -v mongo &> /dev/null; then
    log_success "MongoDB (legacy) found"
    if mongo --eval "db.version()" --quiet &> /dev/null; then
        log_success "MongoDB is running locally"
    else
        log_warning "MongoDB is not running locally"
    fi
else
    log_warning "MongoDB not found on local system"
    log_info "Options:"
    log_info "  1. Use MongoDB Atlas (recommended): https://www.mongodb.com/cloud/atlas"
    log_info "  2. Install MongoDB locally"
    log_info "Update backend/.env with your connection string"
fi

# Step 7: Create helpful scripts
log_info "Step 7/7: Creating helper scripts..."

# Create start-backend.sh
cat > start-backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate 2>/dev/null || . venv/bin/activate
echo "Starting backend server on http://localhost:8001"
echo "API docs available at http://localhost:8001/docs"
echo "Press Ctrl+C to stop"
uvicorn server:app --reload --port 8001
EOF
chmod +x start-backend.sh
log_success "Created start-backend.sh"

# Create start-frontend.sh
cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd frontend
echo "Starting frontend server on http://localhost:3000"
echo "Press Ctrl+C to stop"
yarn start
EOF
chmod +x start-frontend.sh
log_success "Created start-frontend.sh"

# Create start-all.sh
cat > start-all.sh << 'EOF'
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
EOF
chmod +x start-all.sh
log_success "Created start-all.sh"

# Setup complete
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║              Setup Complete! 🎉                        ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Next Steps:"
echo ""
echo -e "  1. ${YELLOW}Update MongoDB connection string${NC}"
echo -e "     Edit: ${BLUE}backend/.env${NC}"
echo -e "     Set MONGO_URL to your MongoDB connection string"
echo ""
echo -e "  2. ${YELLOW}Start the application${NC}"
echo -e "     ${GREEN}Option A - Separate terminals:${NC}"
echo -e "       Terminal 1: ${BLUE}./start-backend.sh${NC}"
echo -e "       Terminal 2: ${BLUE}./start-frontend.sh${NC}"
echo ""
echo -e "     ${GREEN}Option B - Single command (background):${NC}"
echo -e "       ${BLUE}./start-all.sh${NC}"
echo ""
echo -e "  3. ${YELLOW}Access the application${NC}"
echo -e "     Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "     Backend API: ${BLUE}http://localhost:8001${NC}"
echo -e "     API Docs: ${BLUE}http://localhost:8001/docs${NC}"
echo ""
echo -e "  4. ${YELLOW}Login with default credentials${NC}"
echo -e "     Username: ${BLUE}admin${NC}"
echo -e "     Password: ${BLUE}Admin@2024${NC}"
echo ""

log_warning "Important: Change the default password after first login!"
echo ""

log_info "For more information, see README.md"
echo ""
