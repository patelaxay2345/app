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

- [🚀 Quick Start Guide](./QUICK_START.md) - Get up and running in 5 minutes
- [📖 Full Deployment Guide](./DEPLOYMENT.md) - Comprehensive setup instructions
- [🔧 Development Setup](#development-setup) - Local development guide

---

## 🏃 Quick Start

### For Deployment (Production/Dev)

See [QUICK_START.md](./QUICK_START.md) for deploying to Linode with GitLab CI/CD.

### For Local Development

```bash
# Clone repository
git clone https://gitlab.com/your-username/jobtalk-admin.git
cd jobtalk-admin

# Setup backend
cd backend
cp .env.example .env
# Edit .env with your MongoDB connection string
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Setup frontend (in new terminal)
cd frontend
yarn install
yarn start
```

Access at: `http://localhost:3000`

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
