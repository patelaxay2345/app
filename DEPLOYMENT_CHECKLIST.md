# Deployment Checklist

Use this checklist to ensure a smooth deployment of JobTalk Admin Dashboard.

## ☑️ Pre-Deployment Checklist

### Infrastructure Setup

- [ ] Linode server provisioned (Ubuntu 20.04+)
- [ ] Server has minimum 2GB RAM, 2 CPU cores
- [ ] Domain name purchased (optional)
- [ ] DNS configured to point to server IP

### Server Configuration

- [ ] SSH access to server configured
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Git installed
- [ ] Firewall configured (ports 22, 80, 443, 8080)
- [ ] Swap space configured (recommended for smaller servers)
- [ ] Application directory created: `/opt/jobtalk-admin`

**Quick setup:**
```bash
./deployment/server-setup.sh
```

### MongoDB Atlas

- [ ] MongoDB Atlas account created
- [ ] Production cluster created
- [ ] Development cluster created
- [ ] Database user created with admin privileges
- [ ] Server IP added to Network Access whitelist
- [ ] Connection strings obtained for both environments

### GitLab Configuration

- [ ] Repository created in GitLab
- [ ] Container Registry enabled
- [ ] SSH deploy key added to GitLab
- [ ] Repository cloned to server

### GitLab CI/CD Variables

Run `./deployment/check-ci-vars.sh` to see all required variables.

#### Server Access
- [ ] `LINODE_SSH_HOST` - Server IP address
- [ ] `LINODE_SSH_USER` - SSH username
- [ ] `LINODE_SSH_PRIVATE_KEY` - SSH private key (Protected + Masked)

#### Production Environment
- [ ] `MONGO_URL_PROD` - MongoDB connection string (Masked)
- [ ] `JWT_SECRET_PROD` - JWT secret (Protected + Masked)
- [ ] `ENCRYPTION_KEY_PROD` - Encryption key (Protected + Masked)
- [ ] `CORS_ORIGINS_PROD` - Production domains

#### Development Environment
- [ ] `MONGO_URL_DEV` - MongoDB connection string (Masked)
- [ ] `JWT_SECRET_DEV` - JWT secret (Masked)
- [ ] `ENCRYPTION_KEY_DEV` - Encryption key (Masked)
- [ ] `CORS_ORIGINS_DEV` - Dev CORS origins

#### AWS SES (Email)
- [ ] `AWS_ACCESS_KEY_ID` - AWS access key (Masked)
- [ ] `AWS_SECRET_ACCESS_KEY` - AWS secret key (Protected + Masked)
- [ ] `SMTP_FROM_EMAIL` - Sender email address

### Security

- [ ] Strong JWT secrets generated (64+ characters)
- [ ] Unique encryption keys generated (32 characters each)
- [ ] Different secrets for production and development
- [ ] Secrets stored securely in GitLab CI/CD variables
- [ ] No secrets committed to repository

---

## 🚀 Deployment Checklist

### First Deployment

#### Development Environment

- [ ] Create `dev` branch: `git checkout -b dev && git push origin dev`
- [ ] Push code to trigger pipeline
- [ ] Monitor GitLab pipeline: **CI/CD > Pipelines**
- [ ] Verify build stage completes successfully
- [ ] Verify deploy stage completes successfully
- [ ] Wait for health check to pass

#### Verify Development Deployment

- [ ] Access dev environment: `http://SERVER_IP:8080`
- [ ] Login with default credentials
- [ ] Test partner creation
- [ ] Test dashboard loading
- [ ] Verify MongoDB connection
- [ ] Check browser console for errors
- [ ] Review application logs

**Check logs:**
```bash
ssh root@SERVER_IP
cd /opt/jobtalk-admin
docker-compose -f docker-compose.dev.yml logs -f
```

#### Production Environment

- [ ] Merge dev to main: `git checkout main && git merge dev && git push origin main`
- [ ] Monitor GitLab pipeline
- [ ] **Manually approve** deployment job
- [ ] Verify build stage completes
- [ ] Verify deploy stage completes
- [ ] Wait for health check to pass

#### Verify Production Deployment

- [ ] Access production: `http://SERVER_IP` or `https://yourdomain.com`
- [ ] Login with default credentials
- [ ] **Immediately change admin password**
- [ ] Test all major features
- [ ] Verify email functionality
- [ ] Check MongoDB Atlas connection
- [ ] Review application logs
- [ ] Monitor system resources

**Check logs:**
```bash
ssh root@SERVER_IP
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml logs -f
```

---

## ✅ Post-Deployment Checklist

### Security Hardening

- [ ] Changed default admin password
- [ ] Created additional admin users (if needed)
- [ ] Reviewed user access levels
- [ ] Verified firewall rules
- [ ] Confirmed MongoDB Atlas IP restrictions
- [ ] SSL/TLS certificate installed (production)
- [ ] HTTPS redirect configured (production)

### Monitoring Setup

- [ ] Application health check working
- [ ] Log rotation configured
- [ ] Disk space monitoring set up
- [ ] Uptime monitoring configured
- [ ] Alert notifications configured

### Documentation

- [ ] Updated README with actual URLs
- [ ] Documented custom configurations
- [ ] Shared credentials with team (securely)
- [ ] Created runbook for common operations

### Testing

- [ ] Load testing performed
- [ ] Email notifications tested
- [ ] Partner SSH connections tested
- [ ] Dashboard refresh functionality tested
- [ ] Alert system tested
- [ ] Concurrency updates tested

### Backup and Recovery

- [ ] MongoDB Atlas backups enabled
- [ ] Backup schedule configured
- [ ] Restore procedure documented
- [ ] Rollback procedure tested

---

## 🔄 Ongoing Maintenance Checklist

### Weekly

- [ ] Review application logs for errors
- [ ] Check disk space usage
- [ ] Monitor MongoDB Atlas metrics
- [ ] Review alert logs

### Monthly

- [ ] System package updates: `apt update && apt upgrade`
- [ ] Docker image cleanup: `docker system prune -af`
- [ ] Review and rotate logs
- [ ] Check SSL certificate expiry
- [ ] Review user access

### Quarterly

- [ ] Security audit
- [ ] Performance review
- [ ] Backup restoration test
- [ ] Disaster recovery drill

---

## 📋 Quick Command Reference

### Health Checks

```bash
# Application health
curl http://localhost/health

# Container status
docker ps

# System resources
docker stats
htop
```

### Logs

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100

# Backend only
docker-compose -f docker-compose.prod.yml logs -f | grep backend
```

### Restart Application

```bash
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml restart
```

### Update Application

```bash
cd /opt/jobtalk-admin
git pull origin main
./deployment/deploy.sh production
```

### Rollback

```bash
cd /opt/jobtalk-admin
docker-compose -f docker-compose.prod.yml down
# Pull specific version
docker pull registry.gitlab.com/your-username/jobtalk-admin:COMMIT_SHA
# Update IMAGE_TAG in .env.production
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🆘 Emergency Contacts

- **DevOps Team**: [Contact info]
- **MongoDB Support**: https://support.mongodb.com
- **AWS Support**: https://support.aws.amazon.com
- **Linode Support**: https://support.linode.com

---

## ✨ Deployment Complete!

Once all checkboxes are marked:

1. ✅ Application is live and accessible
2. ✅ All services are healthy
3. ✅ Monitoring is active
4. ✅ Security is hardened
5. ✅ Team is notified

**Congratulations!** Your JobTalk Admin Dashboard is successfully deployed! 🎉

---

**Next Steps:**
- Monitor application logs regularly
- Set up automated backups
- Configure uptime monitoring
- Plan for scaling if needed

For any issues, refer to [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) troubleshooting section.
