# Deployment Guide - JobTalk Admin Dashboard

This guide covers deploying the JobTalk Admin Dashboard to Linode using GitLab CI/CD with Docker.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [GitLab Configuration](#gitlab-configuration)
4. [MongoDB Atlas Setup](#mongodb-atlas-setup)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- GitLab account with repository access
- Linode server (Ubuntu 20.04 or later)
- MongoDB Atlas account
- Domain name (optional but recommended)
- GitLab Runner (for custom runners, optional)

---

## Server Setup

### 1. Initial Server Configuration

SSH into your Linode server:
```bash
ssh root@your-linode-ip
```

### 2. Install Docker and Docker Compose

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Enable Docker to start on boot
systemctl enable docker
systemctl start docker

# Verify installation
docker --version
docker-compose --version
```

### 3. Install Git

```bash
apt install git -y
git --version
```

### 4. Create Application Directory

```bash
mkdir -p /opt/jobtalk-admin
cd /opt/jobtalk-admin
```

### 5. Clone Repository

```bash
# Replace with your GitLab repository URL
git clone https://gitlab.com/your-username/jobtalk-admin.git .

# Create dev branch if not exists
git checkout -b dev
git push -u origin dev
```

### 6. Setup SSH Key for GitLab Access (if using private repo)

```bash
ssh-keygen -t ed25519 -C "deployment@jobtalk"
cat ~/.ssh/id_ed25519.pub
# Add this public key to GitLab: Settings > Repository > Deploy Keys
```

### 7. Configure Firewall

```bash
# Allow HTTP, HTTPS, and SSH
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8080/tcp  # For dev environment
ufw enable

# Check status
ufw status
```

### 8. Setup Swap (Optional but recommended for smaller servers)

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## GitLab Configuration

### 1. Enable Container Registry

1. Go to your GitLab project
2. Navigate to **Settings > General > Visibility**
3. Enable **Container Registry**

### 2. Configure CI/CD Variables

Go to **Settings > CI/CD > Variables** and add the following:

#### Server Access Variables

| Variable Name | Value | Protected | Masked |
|--------------|-------|-----------|--------|
| `LINODE_SSH_HOST` | Your Linode server IP | ✓ | ✗ |
| `LINODE_SSH_USER` | `root` (or your user) | ✓ | ✗ |
| `LINODE_SSH_PRIVATE_KEY` | Your SSH private key | ✓ | ✓ |

**To get SSH private key:**
```bash
# Generate on your local machine
ssh-keygen -t ed25519 -f ~/.ssh/gitlab_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/gitlab_deploy.pub root@your-linode-ip

# Copy private key content
cat ~/.ssh/gitlab_deploy
# Paste the entire content (including BEGIN and END lines) into GitLab variable
```

#### Production Environment Variables

| Variable Name | Value | Protected | Masked |
|--------------|-------|-----------|--------|
| `MONGO_URL_PROD` | `mongodb+srv://user:pass@cluster.mongodb.net/` | ✓ | ✓ |
| `JWT_SECRET_PROD` | Random 64-char string | ✓ | ✓ |
| `ENCRYPTION_KEY_PROD` | Random 32-char string | ✓ | ✓ |
| `CORS_ORIGINS_PROD` | `https://yourdomain.com` | ✓ | ✗ |
| `AWS_ACCESS_KEY_ID` | Your AWS key | ✓ | ✓ |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret | ✓ | ✓ |
| `SMTP_FROM_EMAIL` | `noreply@yourdomain.com` | ✓ | ✗ |

#### Development Environment Variables

| Variable Name | Value | Protected | Masked |
|--------------|-------|-----------|--------|
| `MONGO_URL_DEV` | `mongodb+srv://user:pass@cluster-dev.mongodb.net/` | ✗ | ✓ |
| `JWT_SECRET_DEV` | Random 64-char string | ✗ | ✓ |
| `ENCRYPTION_KEY_DEV` | Random 32-char string | ✗ | ✓ |
| `CORS_ORIGINS_DEV` | `*` | ✗ | ✗ |

**Generate secure secrets:**
```bash
# JWT Secret (64 characters)
openssl rand -hex 32

# Encryption Key (32 characters for AES-256)
openssl rand -base64 32 | head -c 32
```

---

## MongoDB Atlas Setup

### 1. Create MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Sign up or log in
3. Create a new project: "JobTalk"

### 2. Create Clusters

#### Production Cluster
1. Click **Build a Database**
2. Choose **Shared (Free tier)** or paid tier
3. Name: `jobtalk-prod`
4. Region: Choose closest to your Linode server
5. Click **Create Cluster**

#### Development Cluster
1. Repeat above steps
2. Name: `jobtalk-dev`

### 3. Configure Database Access

1. Go to **Database Access**
2. Click **Add New Database User**
3. Create user:
   - Username: `jobtalk_admin`
   - Password: Generate secure password
   - Database User Privileges: **Atlas Admin**
4. Click **Add User**

### 4. Configure Network Access

1. Go to **Network Access**
2. Click **Add IP Address**
3. Add your Linode server IP
4. Or allow from anywhere: `0.0.0.0/0` (less secure)
5. Click **Confirm**

### 5. Get Connection String

1. Go to **Databases**
2. Click **Connect** on your cluster
3. Choose **Connect your application**
4. Copy connection string:
   ```
   mongodb+srv://jobtalk_admin:<password>@jobtalk-prod.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<password>` with actual password
6. Add this to GitLab CI/CD variables as `MONGO_URL_PROD`

---

## Deployment

### Initial Deployment

1. **Push code to GitLab:**
   ```bash
   git add .
   git commit -m "Initial deployment setup"
   git push origin main
   ```

2. **Monitor Pipeline:**
   - Go to **CI/CD > Pipelines** in GitLab
   - Watch the build stage complete
   - For production (main branch), deployment requires manual approval

3. **Deploy to Production:**
   - Click on the pipeline
   - Click **Play** button on `deploy_production` job
   - Monitor logs for successful deployment

### Development Deployments

1. **Push to dev branch:**
   ```bash
   git checkout dev
   git merge main
   git push origin dev
   ```

2. **Automatic deployment:**
   - Dev deployments are automatic (no manual approval)
   - Pipeline will build and deploy automatically

### Accessing the Application

#### Production
- URL: `http://your-linode-ip` or `https://yourdomain.com`
- Default admin credentials:
  - Username: `admin`
  - Password: `Admin@2024`

#### Development
- URL: `http://your-linode-ip:8080`
- Same default credentials

---

## Manual Deployment (If CI/CD fails)

### On Linode Server

```bash
# Navigate to app directory
cd /opt/jobtalk-admin

# Pull latest code
git pull origin main

# Login to GitLab Container Registry
echo "YOUR_GITLAB_TOKEN" | docker login -u "YOUR_GITLAB_USERNAME" --password-stdin registry.gitlab.com

# Pull image
docker pull registry.gitlab.com/your-username/jobtalk-admin:latest

# Create environment file
cat > .env.production << EOF
CI_REGISTRY_IMAGE=registry.gitlab.com/your-username/jobtalk-admin
IMAGE_TAG=latest
MONGO_URL=mongodb+srv://...
DB_NAME=recruitment_admin_prod
JWT_SECRET=your-secret
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY=your-encryption-key
APP_NAME=JobTalk
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
SMTP_FROM_EMAIL=noreply@jobtalk.com
NODE_ENV=production
PORT=8001
CORS_ORIGINS=*
EOF

# Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## Domain Configuration (Optional)

### 1. Point Domain to Server

Add A record:
- Name: `@` (or subdomain like `admin`)
- Value: Your Linode IP
- TTL: 300

### 2. Setup SSL with Let's Encrypt

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Stop the application temporarily
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml down

# Obtain certificate
certbot certonly --standalone -d yourdomain.com

# Update nginx configuration to use SSL
# Edit deployment/nginx.conf to add SSL configuration

# Restart application
docker-compose -f docker-compose.prod.yml up -d
```

---

## Monitoring and Maintenance

### View Logs

```bash
# All logs
docker-compose -f docker-compose.prod.yml logs -f

# Backend only
docker-compose -f docker-compose.prod.yml logs -f jobtalk_app | grep backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Check Container Status

```bash
docker ps
docker stats
```

### Restart Application

```bash
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml restart
```

### Database Backup

MongoDB Atlas provides automatic backups. To create manual backup:
1. Go to Atlas dashboard
2. Navigate to your cluster
3. Click **Backup** tab
4. Click **Take Snapshot Now**

---

## Troubleshooting

### Pipeline Fails at Build Stage

**Issue:** Docker build fails

**Solution:**
```bash
# Check Dockerfile syntax
# Verify all files exist
# Check GitLab Runner has enough resources
```

### Cannot Connect to MongoDB

**Issue:** Application can't reach MongoDB Atlas

**Solutions:**
1. Check IP whitelist in MongoDB Atlas
2. Verify connection string is correct
3. Test connection from server:
   ```bash
   docker run --rm -it mongo:6.0 mongosh "your-connection-string"
   ```

### Application Not Accessible

**Issue:** Can't access via browser

**Solutions:**
1. Check firewall:
   ```bash
   ufw status
   ```
2. Check container is running:
   ```bash
   docker ps
   ```
3. Check logs:
   ```bash
   docker-compose logs
   ```
4. Test health endpoint:
   ```bash
   curl http://localhost/health
   ```

### SSH Connection Fails in Pipeline

**Issue:** GitLab CI can't SSH to server

**Solutions:**
1. Verify `LINODE_SSH_PRIVATE_KEY` includes full key with headers
2. Check SSH key is added to server:
   ```bash
   cat ~/.ssh/authorized_keys
   ```
3. Verify SSH service is running:
   ```bash
   systemctl status ssh
   ```

### Out of Disk Space

**Issue:** Server runs out of space

**Solutions:**
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes -f

# Remove old images
docker image prune -af --filter "until=72h"
```

---

## Rollback Procedure

### Using GitLab

1. Go to **Deployments > Environments**
2. Select environment (production/development)
3. Click **Rollback** on previous successful deployment

### Manual Rollback

```bash
cd /opt/jobtalk-admin

# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Pull specific version
docker pull registry.gitlab.com/your-username/jobtalk-admin:COMMIT_SHA

# Update .env file IMAGE_TAG
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=COMMIT_SHA/' .env.production

# Start with old version
docker-compose -f docker-compose.prod.yml up -d
```

---

## Security Best Practices

1. **Change default admin password immediately after first login**
2. **Use strong, unique secrets for JWT and encryption**
3. **Enable firewall and limit exposed ports**
4. **Use HTTPS in production (SSL certificates)**
5. **Regularly update system packages:**
   ```bash
   apt update && apt upgrade -y
   ```
6. **Monitor logs for suspicious activity**
7. **Use separate MongoDB databases for prod/dev**
8. **Restrict MongoDB Atlas network access**
9. **Regular backups (automated via Atlas)**
10. **Keep Docker and Docker Compose updated**

---

## Support

For issues or questions:
- Check application logs
- Review this documentation
- Contact DevOps team

---

## Quick Reference

### Common Commands

```bash
# SSH to server
ssh root@your-linode-ip

# Navigate to app
cd /opt/jobtalk-admin

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart

# Stop
docker-compose -f docker-compose.prod.yml down

# Start
docker-compose -f docker-compose.prod.yml up -d

# Pull latest code
git pull origin main

# Check status
docker ps
curl http://localhost/health
```

### Important URLs

- GitLab: `https://gitlab.com/your-username/jobtalk-admin`
- Production: `http://your-domain.com`
- Development: `http://your-linode-ip:8080`
- MongoDB Atlas: `https://cloud.mongodb.com`

---

**Last Updated:** January 2025
