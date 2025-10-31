# GitLab CI/CD Deployment Workflow

This document illustrates the complete deployment workflow for JobTalk Admin Dashboard.

## 🔄 Deployment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      DEVELOPER WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Code Changes    │
                    │  git commit      │
                    └──────────────────┘
                              │
                              ▼
              ┌───────────────┴────────────────┐
              │                                 │
        git push origin dev           git push origin main
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │  Dev Branch      │              │  Main Branch     │
    │  (Automatic)     │              │  (Manual)        │
    └──────────────────┘              └──────────────────┘
              │                                 │
              └───────────────┬─────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GITLAB CI/CD PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  BUILD STAGE     │
                    └──────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │ Docker Build       │
                    │ - Frontend build   │
                    │ - Backend setup    │
                    │ - Multi-stage      │
                    └────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Push to GitLab  │
                    │  Container       │
                    │  Registry        │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  DEPLOY STAGE    │
                    └──────────────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │  Dev Deploy      │              │  Prod Deploy     │
    │  (Auto)          │              │  (Manual)        │
    │  Port: 8080      │              │  Port: 80        │
    └──────────────────┘              └──────────────────┘
              │                                 │
              └───────────────┬─────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LINODE SERVER DEPLOYMENT                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │ SSH to Server      │
                    │ Pull latest code   │
                    └────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Login to GitLab  │
                    │ Container Reg    │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Pull Docker      │
                    │ Image            │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Create .env      │
                    │ from CI/CD vars  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ docker-compose   │
                    │ down             │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ docker-compose   │
                    │ up -d            │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Health Check     │
                    │ 30 retries       │
                    └──────────────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │  ✅ Success      │              │  ❌ Failure      │
    │  Deployment      │              │  Show logs       │
    │  Complete        │              │  Rollback        │
    └──────────────────┘              └──────────────────┘
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Internet        │
                    │  (HTTP/HTTPS)    │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LINODE SERVER                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Docker Container                        │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │              Supervisor                             │   │  │
│  │  │                                                     │   │  │
│  │  │  ┌───────────────┐      ┌──────────────────────┐  │   │  │
│  │  │  │   Nginx       │      │   FastAPI Backend    │  │   │  │
│  │  │  │   (Port 80)   │◄────►│   (Port 8001)        │  │   │  │
│  │  │  │               │      │   - API Routes       │  │   │  │
│  │  │  │   Routes:     │      │   - Authentication   │  │   │  │
│  │  │  │   /     → UI  │      │   - Business Logic   │  │   │  │
│  │  │  │   /api  → API │      │   - SSH Services     │  │   │  │
│  │  │  │   /health     │      └──────────────────────┘  │   │  │
│  │  │  │               │               │                 │   │  │
│  │  │  │   Static:     │               │                 │   │  │
│  │  │  │   React Build │               │                 │   │  │
│  │  │  └───────────────┘               │                 │   │  │
│  │  │                                  │                 │   │  │
│  │  └──────────────────────────────────┼─────────────────┘   │  │
│  │                                     │                     │  │
│  └─────────────────────────────────────┼─────────────────────┘  │
│                                        │                        │
└────────────────────────────────────────┼────────────────────────┘
                                         │
                                         │ MongoDB Connection
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │   MongoDB Atlas        │
                            │   (Cloud Database)     │
                            │                        │
                            │   Collections:         │
                            │   - users              │
                            │   - partner_configs    │
                            │   - dashboard_snapshots│
                            │   - connection_logs    │
                            │   - alert_logs         │
                            └────────────────────────┘
```

---

## 📁 File Structure & Purpose

```
jobtalk-admin/
│
├── .gitlab-ci.yml                    # CI/CD pipeline definition
│   ├── Build Stage: Docker image
│   └── Deploy Stage: To Linode server
│
├── Dockerfile                        # Multi-stage Docker build
│   ├── Stage 1: Build React frontend
│   └── Stage 2: Setup Python backend + Nginx
│
├── docker-compose.prod.yml           # Production environment
│   ├── Single service: jobtalk_app
│   ├── Port 80 exposed
│   └── Uses MongoDB Atlas
│
├── docker-compose.dev.yml            # Dev environment
│   ├── Single service: jobtalk_app
│   ├── Port 8080 exposed
│   └── Uses MongoDB Atlas (dev cluster)
│
├── deployment/
│   ├── nginx.conf                    # Nginx configuration
│   │   ├── /api → backend:8001
│   │   ├── / → React static files
│   │   └── /health → health check
│   │
│   ├── supervisord.conf              # Process manager
│   │   ├── nginx process
│   │   └── uvicorn backend process
│   │
│   ├── deploy.sh                     # Manual deployment script
│   ├── server-setup.sh               # Initial server setup
│   └── check-ci-vars.sh              # Verify CI/CD variables
│
├── backend/
│   ├── server.py                     # FastAPI application
│   ├── models.py                     # Pydantic models
│   ├── services/                     # Business logic
│   └── requirements.txt              # Python dependencies
│
├── frontend/
│   ├── src/                          # React source code
│   ├── public/                       # Static assets
│   ├── package.json                  # Node dependencies
│   └── build/                        # Production build (generated)
│
├── DEPLOYMENT.md                     # Comprehensive deployment guide
├── QUICK_START.md                    # Quick setup instructions
├── DEPLOYMENT_CHECKLIST.md           # Deployment checklist
├── README.md                         # Project overview
└── .env.*.example                    # Environment templates
```

---

## 🔐 Security & Environment Variables Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  GitLab CI/CD Variables                          │
│                  (Settings > CI/CD > Variables)                  │
│                                                                   │
│  Protected Variables (main branch only):                         │
│  ├── LINODE_SSH_PRIVATE_KEY                                     │
│  ├── MONGO_URL_PROD                                             │
│  ├── JWT_SECRET_PROD                                            │
│  └── ENCRYPTION_KEY_PROD                                        │
│                                                                   │
│  Unprotected Variables (all branches):                          │
│  ├── MONGO_URL_DEV                                              │
│  ├── JWT_SECRET_DEV                                             │
│  └── ENCRYPTION_KEY_DEV                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Pipeline reads variables
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitLab CI/CD Pipeline                         │
│                    (.gitlab-ci.yml)                              │
│                                                                   │
│  SSH to server and create .env file:                            │
│  cat > .env.production << EOF                                   │
│    MONGO_URL=${MONGO_URL_PROD}                                  │
│    JWT_SECRET=${JWT_SECRET_PROD}                                │
│    ENCRYPTION_KEY=${ENCRYPTION_KEY_PROD}                        │
│    ...                                                           │
│  EOF                                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Variables written to server
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Linode Server                                 │
│                    /opt/jobtalk-admin/                           │
│                                                                   │
│  .env.production file created with actual values                │
│  (Not committed to Git)                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Docker reads .env file
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container                              │
│                                                                   │
│  Environment variables available to:                            │
│  ├── FastAPI Backend (os.environ.get())                        │
│  └── Application processes                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚦 Deployment Decision Tree

```
                    Start
                      │
                      ▼
              ┌───────────────┐
              │ Which branch? │
              └───────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
    ┌─────────┐             ┌──────────┐
    │   dev   │             │   main   │
    └─────────┘             └──────────┘
         │                         │
         ▼                         ▼
  ┌─────────────┐         ┌──────────────┐
  │ Auto deploy │         │ Manual deploy│
  │ to dev:8080 │         │ approval req │
  └─────────────┘         └──────────────┘
         │                         │
         ▼                         ▼
  ┌─────────────┐         ┌──────────────┐
  │ Test in dev │         │ Deploy to    │
  │ environment │         │ production   │
  └─────────────┘         │ port 80      │
         │                └──────────────┘
         │                         │
         ▼                         ▼
    ┌─────────┐             ┌──────────┐
    │  Ready  │             │  Live!   │
    │  for    ├────────────►│  Monitor │
    │  prod?  │   Merge     │  & Scale │
    └─────────┘             └──────────┘
```

---

## 📊 Health Check Flow

```
Deployment completes
       │
       ▼
Sleep 10 seconds
       │
       ▼
┌──────────────┐
│ Retry Loop   │
│ (30 attempts)│
└──────────────┘
       │
       ▼
curl http://localhost/health
       │
    ┌──┴──┐
    │     │
    ▼     ▼
  200    Error
  OK     
    │     │
    │     └──► Sleep 2s ──► Retry
    │
    ▼
┌─────────────┐
│ ✅ Success  │
│ Deployment  │
│ Complete    │
└─────────────┘


If all 30 attempts fail:
       │
       ▼
┌─────────────┐
│ ❌ Failure  │
│ Show logs   │
│ Exit 1      │
└─────────────┘
```

---

## 🔄 Rollback Procedure

```
                    Issue Detected
                          │
                          ▼
              ┌─────────────────────┐
              │  Go to GitLab       │
              │  Deployments >      │
              │  Environments       │
              └─────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Find last good     │
              │  deployment         │
              └─────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Click Rollback     │
              │  button             │
              └─────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
    ┌──────────────┐          ┌──────────────┐
    │  Automatic   │    OR    │   Manual     │
    │  via GitLab  │          │   via SSH    │
    └──────────────┘          └──────────────┘
            │                           │
            │                           ▼
            │                  docker pull old-version
            │                           │
            │                           ▼
            │                  docker-compose down
            │                           │
            │                           ▼
            │                  docker-compose up -d
            │                           │
            └───────────┬───────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │  Verify rollback    │
              │  successful         │
              └─────────────────────┘
```

---

## 📈 Monitoring & Logging

```
Application Running
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Backend   Frontend
Logs      Logs
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│  Supervisor     │
│  stdout/stderr  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Docker logs    │
│  JSON format    │
│  Max 3x10MB     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  View with:     │
│  docker-compose │
│  logs -f        │
└─────────────────┘
```

---

This workflow diagram provides a visual overview of the entire deployment process. For detailed instructions, refer to:

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete setup guide
- [QUICK_START.md](./QUICK_START.md) - Quick start instructions
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Step-by-step checklist
