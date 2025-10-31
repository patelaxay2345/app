# Quick Start - GitLab CI/CD Deployment

This is a quick reference guide for deploying JobTalk Admin Dashboard. For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## 🚀 Quick Setup (5 Minutes)

### 1. Server Setup

SSH into your Linode server and run:

```bash
wget https://gitlab.com/your-username/jobtalk-admin/-/raw/main/deployment/server-setup.sh
chmod +x server-setup.sh
sudo ./server-setup.sh
```

### 2. Clone Repository

```bash
cd /opt/jobtalk-admin
git clone https://gitlab.com/your-username/jobtalk-admin.git .
```

### 3. Configure GitLab CI/CD Variables

Go to **Settings > CI/CD > Variables** in GitLab and add:

**Required Variables:**
- `LINODE_SSH_HOST` - Your server IP
- `LINODE_SSH_USER` - SSH username (usually `root`)
- `LINODE_SSH_PRIVATE_KEY` - SSH private key
- `MONGO_URL_PROD` - MongoDB Atlas connection string
- `MONGO_URL_DEV` - MongoDB Atlas connection string (dev)
- `JWT_SECRET_PROD` - Random secure string (64+ chars)
- `JWT_SECRET_DEV` - Random secure string (64+ chars)
- `ENCRYPTION_KEY_PROD` - 32-character string
- `ENCRYPTION_KEY_DEV` - 32-character string
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `SMTP_FROM_EMAIL` - Email sender address
- `CORS_ORIGINS_PROD` - Production domain
- `CORS_ORIGINS_DEV` - Dev CORS origins (use `*`)

**Generate Secrets:**
```bash
# JWT Secret
openssl rand -hex 32

# Encryption Key
openssl rand -base64 32 | head -c 32
```

### 4. Deploy

**Development:**
```bash
git checkout dev
git push origin dev
```

**Production:**
```bash
git checkout main
git push origin main
# Then manually approve deployment in GitLab pipeline
```

## 📋 Branch Strategy

- **`main`** branch → Production environment (manual deployment)
- **`dev`** branch → Development environment (automatic deployment)

## 🔗 Access URLs

- **Production:** `http://your-linode-ip` (port 80)
- **Development:** `http://your-linode-ip:8080` (port 8080)

## 📊 Monitoring

```bash
# SSH to server
ssh root@your-linode-ip

# View logs
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker ps
curl http://localhost/health
```

## 🔧 Common Commands

```bash
# Restart application
docker-compose -f docker-compose.prod.yml restart

# Stop application
docker-compose -f docker-compose.prod.yml down

# Start application
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Clean Docker
docker system prune -af
```

## 🆘 Troubleshooting

**Pipeline fails?**
- Check GitLab CI/CD variables are set correctly
- Verify SSH key is added to server

**Can't access application?**
- Check firewall: `ufw status`
- Check containers: `docker ps`
- Check logs: `docker-compose logs`

**MongoDB connection error?**
- Verify MongoDB Atlas connection string
- Check IP whitelist in MongoDB Atlas
- Test connection: `docker run --rm -it mongo:6.0 mongosh "your-connection-string"`

## 📚 Full Documentation

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete setup instructions, troubleshooting, and best practices.

## 🔐 Security Checklist

- [ ] Changed default admin password
- [ ] Set strong JWT secret
- [ ] Set unique encryption key
- [ ] Configured firewall rules
- [ ] Limited MongoDB Atlas IP access
- [ ] Using HTTPS in production
- [ ] Regular backups enabled
- [ ] Monitoring set up

## 📞 Support

For issues:
1. Check logs: `docker-compose logs`
2. Review [DEPLOYMENT.md](./DEPLOYMENT.md)
3. Contact DevOps team
