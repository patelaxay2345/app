# JobTalk Admin Dashboard

A comprehensive admin dashboard for managing recruitment partners, monitoring campaigns, and controlling concurrency settings.

## 🚀 Features

- **Partner Management**: Configure and manage recruitment partner connections
- **Real-time Dashboard**: Monitor campaigns, calls, and system utilization
- **SSH/Database Integration**: Secure connections to partner databases
- **Concurrency Control**: Adjust campaign concurrency limits dynamically
- **Alert System**: Automated alerts for critical thresholds
- **User Authentication**: JWT-based secure authentication
- **Email Notifications**: AWS SES integration for alerts

## 🛠️ Tech Stack

- **Frontend**: React 19, Tailwind CSS, Radix UI
- **Backend**: FastAPI (Python), Motor (MongoDB async)
- **Database**: MongoDB Atlas
- **Deployment**: Docker, GitLab CI/CD
- **Infrastructure**: Linode, Nginx, Supervisor

## 📋 Quick Links

- [🚀 Quick Start Guide](./QUICK_START.md) - Get up and running in 5 minutes (Production Deployment)
- [📖 Full Deployment Guide](./DEPLOYMENT.md) - Comprehensive production deployment instructions
- [🔧 Development Setup](#for-local-development) - Quick local development setup
- [📚 Detailed Setup Guide](./PROJECT_SETUP.md) - Complete development environment setup
- [✅ Deployment Checklist](./DEPLOYMENT_CHECKLIST.md) - Pre/post deployment checklist
- [🔄 Workflow Diagrams](./WORKFLOW.md) - Visual deployment workflows

---

## 🏃 Quick Start

### For Deployment (Production/Dev)

See [QUICK_START.md](./QUICK_START.md) for deploying to Linode with GitLab CI/CD.

### For Local Development

#### 🚀 Automated Setup (Recommended)

**One-Command Setup:**
```bash
# Clone repository
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# Run automated setup script
chmod +x setup-dev.sh
./setup-dev.sh
```

The setup script will:
- ✅ Check all required dependencies
- ✅ Create Python virtual environment
- ✅ Install backend dependencies
- ✅ Install frontend dependencies
- ✅ Create .env configuration files
- ✅ Generate helper scripts for starting servers

After setup completes, start the application:
```bash
# Option 1: Separate terminals (recommended for development)
./start-backend.sh  # Terminal 1
./start-frontend.sh # Terminal 2

# Option 2: Both servers in background
./start-all.sh
```

Access at: `http://localhost:3000` (default login: admin / Admin@2024)

**For detailed setup instructions including troubleshooting, IDE configuration, and more, see [PROJECT_SETUP.md](./PROJECT_SETUP.md)**

---

#### 📋 Manual Setup

#### Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Yarn** - Run: `npm install -g yarn`
- **MongoDB** - [Local installation](https://www.mongodb.com/try/download/community) or [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (recommended)
- **Git** - [Download](https://git-scm.com/downloads)

#### Step 1: Clone Repository

```bash
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin
```

#### Step 2: Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create environment file from example
cp .env.example .env

# Edit .env file with your configuration
# Required: MONGO_URL, JWT_SECRET, ENCRYPTION_KEY
nano .env  # or use any text editor
```

**Minimum required environment variables in `backend/.env`:**
```env
MONGO_URL="mongodb://localhost:27017"  # Or your MongoDB Atlas connection string
DB_NAME="recruitment_admin"
JWT_SECRET="your-super-secret-jwt-key-change-in-production-2024"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY="your-32-character-encryption-key"
CORS_ORIGINS="*"
```

**Generate secure secrets:**
```bash
# JWT Secret (64 characters)
openssl rand -hex 32

# Encryption Key (32 characters)
openssl rand -base64 32 | head -c 32
```

**Start backend server:**
```bash
uvicorn server:app --reload --port 8001
```

Backend will be available at: `http://localhost:8001`
API documentation at: `http://localhost:8001/docs`

#### Step 3: Setup Frontend (New Terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
yarn install

# Create environment file from example
cp .env.example .env

# Edit frontend/.env with backend URL (default is fine for local dev)
# REACT_APP_BACKEND_URL=http://localhost:8001
```

**Start frontend development server:**
```bash
yarn start
```

Frontend will automatically open at: `http://localhost:3000`

#### Step 4: Access Application

1. Open browser to `http://localhost:3000`
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `Admin@2024`
3. **⚠️ Important**: Change the default password immediately!

#### Quick Setup Commands

```bash
# One-command setup (requires separate terminals)

# Terminal 1 - Backend
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn server:app --reload --port 8001

# Terminal 2 - Frontend  
cd frontend && yarn install && yarn start
```

---

## 📁 Project Structure

```
jobtalk-admin/
├── backend/                    # FastAPI backend
│   ├── services/              # Business logic services
│   ├── models.py              # Pydantic models
│   ├── server.py              # Main API server
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── contexts/          # Context providers
│   │   ├── pages/            # Page components
│   │   └── utils/            # Utilities
│   └── package.json          # Node dependencies
├── deployment/                # Deployment configurations
│   ├── nginx.conf            # Nginx configuration
│   ├── supervisord.conf      # Supervisor configuration
│   ├── deploy.sh             # Deployment script
│   ├── server-setup.sh       # Server setup script
│   └── check-ci-vars.sh      # CI/CD variables checker
├── .gitlab-ci.yml            # GitLab CI/CD pipeline
├── docker-compose.prod.yml   # Production docker-compose
├── docker-compose.dev.yml    # Development docker-compose
├── Dockerfile                # Multi-stage Docker build
└── DEPLOYMENT.md             # Deployment documentation
```

---

## 🔧 Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB (local or Atlas)
- Git

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn server:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Configure environment
cp .env.example .env
# Edit .env with backend URL

# Run development server
yarn start
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### Default Credentials

- **Username**: `admin`
- **Password**: `Admin@2024`

⚠️ **Change these credentials immediately in production!**

---

## 💻 Development Workflow

### Project Setup for New Developers

#### 1. Install System Dependencies

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node@18 mongodb-community yarn
```

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 18 and Yarn
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y
npm install -g yarn

# Install MongoDB (optional - use Atlas if preferred)
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install mongodb-org -y
```

**Windows:**
- Download Python 3.11: https://www.python.org/downloads/
- Download Node.js 18: https://nodejs.org/
- Install Yarn: `npm install -g yarn`
- MongoDB Atlas recommended (or Docker Desktop with MongoDB)

#### 2. Clone and Setup

```bash
# Clone repository
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# Create virtual environment for backend
cd backend
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Go back to root
cd ..

# Install frontend dependencies
cd frontend
yarn install
cd ..
```

#### 3. Setup MongoDB

**Option A: MongoDB Atlas (Recommended)**
1. Create free account at https://www.mongodb.com/cloud/atlas
2. Create a new cluster (free M0 tier available)
3. Create database user
4. Whitelist your IP address (or use 0.0.0.0/0 for development)
5. Get connection string
6. Add to `backend/.env`:
   ```
   MONGO_URL="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```

**Option B: Local MongoDB**
```bash
# Start MongoDB service
# macOS:
brew services start mongodb-community

# Ubuntu/Linux:
sudo systemctl start mongod
sudo systemctl enable mongod

# Windows:
# MongoDB runs as a service automatically after installation

# Use in backend/.env:
MONGO_URL="mongodb://localhost:27017"
```

#### 4. Configure Environment Files

**Backend (`backend/.env`):**
```env
# Database
MONGO_URL="mongodb://localhost:27017"
DB_NAME="recruitment_admin"

# Security
JWT_SECRET="dev-jwt-secret-change-in-production-minimum-32-chars"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY="dev-32-character-encryption-key"

# AWS SES (optional for local dev, can use dummy values)
AWS_ACCESS_KEY_ID="your-aws-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret"
AWS_REGION="us-east-1"
SMTP_FROM_EMAIL="noreply@localhost.com"
APP_NAME="JobTalk"

# Application
NODE_ENV="development"
PORT=8001
CORS_ORIGINS="*"
```

**Frontend (`frontend/.env`):**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
```

#### 5. Run Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn server:app --reload --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
yarn start
```

The application will open automatically at `http://localhost:3000`

### Common Development Tasks

#### Running Tests

**Backend Tests:**
```bash
cd backend
source venv/bin/activate
pytest
```

**Frontend Tests:**
```bash
cd frontend
yarn test
```

#### Code Linting & Formatting

**Backend (Python):**
```bash
cd backend
# Lint with flake8
flake8 .

# Format with black
black .

# Type checking with mypy
mypy .
```

**Frontend (JavaScript/React):**
```bash
cd frontend
# Lint
yarn lint

# Format
yarn format
```

#### Adding New Dependencies

**Backend:**
```bash
cd backend
source venv/bin/activate
pip install <package-name>
pip freeze > requirements.txt  # Update requirements
```

**Frontend:**
```bash
cd frontend
yarn add <package-name>
```

#### Database Management

**View MongoDB Data:**
```bash
# Connect to local MongoDB
mongosh

# Or connect to Atlas
mongosh "your-connection-string"

# List databases
show dbs

# Use database
use recruitment_admin

# List collections
show collections

# Query data
db.users.find()
db.partner_configs.find()
```

**Reset Development Database:**
```bash
# In mongosh
use recruitment_admin
db.dropDatabase()

# Restart backend - it will recreate default admin user
```

#### Creating New API Endpoints

1. Add Pydantic model to `backend/models.py`
2. Add route handler in `backend/server.py`
3. Test with FastAPI docs at `http://localhost:8001/docs`
4. Add frontend API call in `frontend/src/utils/api.js`
5. Create/update React component

#### Creating New Frontend Pages

1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.js`
3. Add navigation link if needed
4. Style with Tailwind CSS

### Troubleshooting Development Issues

**Backend won't start:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Check if virtual environment is activated
which python  # Should point to venv

# Check MongoDB connection
mongosh "your-mongo-url"

# Check port 8001 is not in use
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows
```

**Frontend won't start:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules yarn.lock
yarn install

# Check Node version
node --version  # Should be 18+

# Check port 3000 is not in use
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows
```

**CORS errors:**
- Ensure `CORS_ORIGINS="*"` in `backend/.env`
- Check `REACT_APP_BACKEND_URL` is set correctly in `frontend/.env`
- Restart backend server after changing CORS settings

**Database connection errors:**
- Verify MongoDB is running: `mongosh`
- Check connection string in `backend/.env`
- For Atlas: ensure IP is whitelisted

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Description of changes"

# Push to remote
git push origin feature/your-feature-name

# Create merge request in GitLab
# After approval, merge to dev, then to main
```

### Hot Reload

Both backend and frontend support hot reload:
- **Backend**: Changes to Python files auto-reload (uvicorn --reload)
- **Frontend**: Changes to React files auto-reload (React Fast Refresh)

### Environment Variables

Development environment variables are in `.env` files:
- `backend/.env` - Backend configuration
- `frontend/.env` - Frontend configuration

**Never commit `.env` files with real secrets!**

---

## 🚢 Deployment

### GitLab CI/CD (Recommended)

The project includes automated CI/CD pipelines for deployment:

1. **Setup Server**: Run setup script on your Linode server
   ```bash
   wget https://gitlab.com/your-username/jobtalk-admin/-/raw/main/deployment/server-setup.sh
   chmod +x server-setup.sh
   sudo ./server-setup.sh
   ```

2. **Configure GitLab Variables**: Add required CI/CD variables
   ```bash
   # Check required variables
   ./deployment/check-ci-vars.sh
   ```

3. **Deploy**:
   - Push to `dev` branch → Automatic deployment to dev environment
   - Push to `main` branch → Manual deployment to production

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete instructions.

### Manual Deployment

```bash
# On server
cd /opt/jobtalk-admin
./deployment/deploy.sh production  # or 'dev'
```

---

## 🔐 Security

### Environment Variables

Never commit `.env` files with actual secrets. Use GitLab CI/CD variables or environment-specific files.

**Required secrets:**
- `JWT_SECRET` - JWT signing key (64+ characters)
- `ENCRYPTION_KEY` - Data encryption key (32 characters)
- `MONGO_URL` - MongoDB connection string
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` - AWS credentials

**Generate secrets:**
```bash
# JWT Secret
openssl rand -hex 32

# Encryption Key
openssl rand -base64 32 | head -c 32
```

### Best Practices

1. Change default admin password immediately
2. Use strong, unique secrets for each environment
3. Enable firewall on server
4. Use HTTPS in production
5. Restrict MongoDB Atlas IP access
6. Regular security updates
7. Monitor logs for suspicious activity

---

## 📊 Monitoring

### Check Application Status

```bash
# On server
docker ps
curl http://localhost/health
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Backend only
docker-compose -f docker-compose.prod.yml logs -f jobtalk_app | grep backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Monitor Resources

```bash
docker stats
htop
```

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
yarn test
```

---

## 🔄 CI/CD Pipeline

The GitLab CI/CD pipeline includes:

### Stages

1. **Build**: Build Docker image and push to GitLab Container Registry
2. **Deploy**: Deploy to production (main) or dev (dev branch)

### Branch Strategy

- `main` → Production (manual approval required)
- `dev` → Development (automatic deployment)

### Pipeline Workflow

```
Push to branch → Build Docker image → Push to registry → Deploy to environment → Health check
```

---

## 📦 Docker

### Build Image

```bash
docker build -t jobtalk-admin .
```

### Run with Docker Compose

```bash
# Production
docker-compose -f docker-compose.prod.yml up -d

# Development
docker-compose -f docker-compose.dev.yml up -d
```

---

## 🛠️ Troubleshooting

### Common Issues

**Can't connect to MongoDB**
- Check MongoDB Atlas IP whitelist
- Verify connection string
- Test: `mongosh "your-connection-string"`

**Application not accessible**
- Check firewall: `ufw status`
- Check containers: `docker ps`
- Check logs: `docker-compose logs`

**Health check fails**
- Wait 30-60 seconds after deployment
- Check backend logs
- Verify MongoDB connection

See [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) for more solutions.

---

## 📞 Support

- **Issues**: Create an issue in GitLab
- **Documentation**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Logs**: Check application and Docker logs

---

## 📄 License

Proprietary - All rights reserved

---

## 🙏 Acknowledgments

Built with FastAPI, React, MongoDB, and modern DevOps practices.

---

**Last Updated**: January 2025
