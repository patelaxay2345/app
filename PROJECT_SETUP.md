# Project Setup Guide - JobTalk Admin Dashboard

Complete guide for setting up the JobTalk Admin Dashboard for local development.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Setup (Automated)](#quick-setup-automated)
3. [Manual Setup](#manual-setup)
4. [MongoDB Configuration](#mongodb-configuration)
5. [Running the Application](#running-the-application)
6. [Troubleshooting](#troubleshooting)
7. [IDE Configuration](#ide-configuration)
8. [Development Tools](#development-tools)

---

## System Requirements

### Minimum Requirements

- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+, or Windows 11
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 2GB free space
- **Internet**: Required for installing dependencies

### Required Software

| Software | Minimum Version | Recommended Version | Download Link |
|----------|----------------|-------------------|---------------|
| Python | 3.11.0 | 3.11.x (latest) | https://www.python.org/downloads/ |
| Node.js | 18.0.0 | 18.x LTS | https://nodejs.org/ |
| Yarn | 1.22.0 | Latest | `npm install -g yarn` |
| MongoDB | 6.0 | 6.0 (or Atlas) | https://www.mongodb.com/try/download/community |
| Git | 2.30.0 | Latest | https://git-scm.com/downloads |

---

## Quick Setup (Automated)

### For macOS and Linux

```bash
# 1. Clone the repository
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# 2. Run automated setup
chmod +x setup-dev.sh
./setup-dev.sh

# 3. Configure MongoDB connection
nano backend/.env  # Edit MONGO_URL

# 4. Start the application
./start-backend.sh  # Terminal 1
./start-frontend.sh # Terminal 2
```

### For Windows

```powershell
# 1. Clone the repository
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# 2. Follow manual setup below
# (Windows batch script coming soon)
```

---

## Manual Setup

### Step 1: Install System Dependencies

#### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Install Node.js 18
brew install node@18

# Install Yarn
npm install -g yarn

# Install MongoDB (optional - can use Atlas instead)
brew tap mongodb/brew
brew install mongodb-community@6.0
brew services start mongodb-community@6.0
```

#### Ubuntu/Debian Linux

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Yarn
npm install -g yarn

# Install MongoDB (optional)
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install mongodb-org -y
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### Windows

1. **Install Python 3.11**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"
   - Verify: `python --version`

2. **Install Node.js 18**
   - Download LTS from: https://nodejs.org/
   - Run installer with default options
   - Verify: `node --version`

3. **Install Yarn**
   ```powershell
   npm install -g yarn
   ```

4. **Install MongoDB** (optional - Atlas recommended)
   - Download from: https://www.mongodb.com/try/download/community
   - Or use Docker: `docker run -d -p 27017:27017 mongo:6.0`

5. **Install Git**
   - Download from: https://git-scm.com/downloads
   - Use default installation options

### Step 2: Clone Repository

```bash
# Clone via HTTPS
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# OR clone via SSH (requires SSH key setup)
git clone git@gitlab.com:your-username/jobtalk-admin.git
cd jobtalk-admin
```

### Step 3: Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Configure Backend Environment

```bash
# Still in backend directory
cd backend

# Create .env file
cat > .env << 'EOF'
# Database Configuration
MONGO_URL="mongodb://localhost:27017"
DB_NAME="recruitment_admin"

# JWT Configuration
JWT_SECRET="dev-jwt-secret-change-in-production-minimum-32-chars-long"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8

# Encryption Key (Must be exactly 32 characters)
ENCRYPTION_KEY="dev-32-character-encryption-key"

# AWS SES Configuration (for email notifications)
APP_NAME="JobTalk-Dev"
AWS_ACCESS_KEY_ID="your-aws-access-key-id"
AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
AWS_REGION="us-east-1"
SMTP_FROM_EMAIL="noreply@localhost.com"

# Application Settings
NODE_ENV="development"
PORT=8001
CORS_ORIGINS="*"
EOF

# On Windows, create the file manually or use:
# copy .env.example .env
```

**Important:** Update the `MONGO_URL` with your actual MongoDB connection string.

### Step 5: Setup Frontend

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies (this may take a few minutes)
yarn install

# Create .env file
cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
EOF

# On Windows, create manually or copy
```

---

## MongoDB Configuration

### Option 1: MongoDB Atlas (Recommended for Development)

1. **Create Account**
   - Go to: https://www.mongodb.com/cloud/atlas
   - Sign up for free account

2. **Create Cluster**
   - Click "Build a Database"
   - Choose "Free Shared" (M0 tier)
   - Select region closest to you
   - Click "Create Cluster"

3. **Create Database User**
   - Go to "Database Access"
   - Click "Add New Database User"
   - Set username and password
   - Set privileges to "Atlas admin"
   - Click "Add User"

4. **Whitelist IP Address**
   - Go to "Network Access"
   - Click "Add IP Address"
   - For development, use: `0.0.0.0/0` (allow from anywhere)
   - Or add your specific IP address
   - Click "Confirm"

5. **Get Connection String**
   - Go to "Database" > "Connect"
   - Choose "Connect your application"
   - Copy connection string
   - Replace `<password>` with your actual password

6. **Update Backend Configuration**
   ```bash
   # Edit backend/.env
   MONGO_URL="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
   DB_NAME="recruitment_admin"
   ```

### Option 2: Local MongoDB

**Start MongoDB Service:**

```bash
# macOS
brew services start mongodb-community

# Ubuntu/Linux
sudo systemctl start mongod
sudo systemctl status mongod

# Windows - MongoDB runs as service automatically
# Or use: net start MongoDB

# Verify connection
mongosh
# Should connect to: mongodb://localhost:27017
```

**Use in Configuration:**
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="recruitment_admin"
```

### Option 3: MongoDB with Docker

```bash
# Start MongoDB container
docker run -d \
  --name jobtalk-mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  mongo:6.0

# Use in configuration:
MONGO_URL="mongodb://admin:password123@localhost:27017/"
```

---

## Running the Application

### Method 1: Using Helper Scripts (macOS/Linux)

After running `./setup-dev.sh`, use these scripts:

```bash
# Start backend (Terminal 1)
./start-backend.sh

# Start frontend (Terminal 2)
./start-frontend.sh

# Or start both in background
./start-all.sh
```

### Method 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn server:app --reload --port 8001
```

Backend will be available at:
- **API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

**Terminal 2 - Frontend:**
```bash
cd frontend
yarn start
```

Frontend will automatically open at: http://localhost:3000

### First Login

1. Navigate to http://localhost:3000
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `Admin@2024`
3. **⚠️ Important**: Change password immediately after first login

---

## Troubleshooting

### Backend Issues

#### "Command not found: python3.11"
```bash
# Check Python installation
python --version
python3 --version

# Use whatever version is 3.11+
python3 -m venv venv
```

#### "ModuleNotFoundError"
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### "Can't connect to MongoDB"
```bash
# Test MongoDB connection
mongosh "your-connection-string"

# Check if MongoDB is running
# macOS/Linux:
ps aux | grep mongod

# Windows:
tasklist | findstr mongod
```

#### Port 8001 already in use
```bash
# Find process using port 8001
# macOS/Linux:
lsof -i :8001
kill -9 <PID>

# Windows:
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

### Frontend Issues

#### "Command not found: yarn"
```bash
# Install yarn globally
npm install -g yarn

# Verify installation
yarn --version
```

#### "Cannot find module"
```bash
# Clean install
rm -rf node_modules yarn.lock
yarn install
```

#### Port 3000 already in use
```bash
# Find and kill process
# macOS/Linux:
lsof -i :3000
kill -9 <PID>

# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or use different port
PORT=3001 yarn start
```

#### CORS errors
```bash
# 1. Check backend .env has:
CORS_ORIGINS="*"

# 2. Check frontend .env has:
REACT_APP_BACKEND_URL=http://localhost:8001

# 3. Restart both servers
```

### Database Issues

#### "Authentication failed"
- Verify MongoDB Atlas username/password
- Check connection string format
- Ensure no special characters need URL encoding

#### "IP not whitelisted"
- Add your IP to MongoDB Atlas Network Access
- Or use `0.0.0.0/0` for development

#### "Database connection timeout"
- Check internet connection
- Verify MongoDB service is running
- Test connection with mongosh

---

## IDE Configuration

### Visual Studio Code

**Recommended Extensions:**
```
Python (ms-python.python)
Pylance (ms-python.vscode-pylance)
ESLint (dbaeumer.vscode-eslint)
Prettier (esbenp.prettier-vscode)
GitLens (eamodio.gitlens)
Docker (ms-azuretools.vscode-docker)
MongoDB (mongodb.mongodb-vscode)
```

**Settings (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[javascriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Open project
2. Configure Python interpreter:
   - Settings > Project > Python Interpreter
   - Add > Existing Environment
   - Select `backend/venv/bin/python`
3. Mark `backend` as Sources Root
4. Mark `frontend` as Excluded

---

## Development Tools

### Useful Commands

```bash
# Backend
cd backend
source venv/bin/activate

# Run tests
pytest

# Lint code
flake8 .

# Format code
black .

# Type checking
mypy .

# Database shell
mongosh

# Frontend
cd frontend

# Run tests
yarn test

# Lint code
yarn lint

# Format code
yarn format

# Build production
yarn build

# Check bundle size
yarn build --stats
```

### Database Management

```bash
# Connect to MongoDB
mongosh "your-connection-string"

# List databases
show dbs

# Use database
use recruitment_admin

# List collections
show collections

# Query collections
db.users.find().pretty()
db.partner_configs.find().pretty()
db.dashboard_snapshots.find().pretty()

# Drop database (reset)
db.dropDatabase()
```

---

## Next Steps

After successful setup:

1. ✅ Change default admin password
2. 📚 Read the [README.md](./README.md) for project overview
3. 🔧 Review [Development Workflow](./README.md#development-workflow) section
4. 🚀 Start building features!

---

## Getting Help

- **Documentation**: See [README.md](./README.md) and [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Issues**: Create an issue in GitLab
- **Questions**: Contact the development team

---

**Last Updated**: January 2025
