# Environment Variables Guide

Complete reference for all environment variables used in JobTalk Admin Dashboard.

## 📁 File Structure

```
/app/
├── backend/.env              # Backend configuration (gitignored)
├── backend/.env.example      # Backend template (committed to git)
├── frontend/.env             # Frontend configuration (gitignored)
├── frontend/.env.example     # Frontend template (committed to git)
├── .env.production.example   # Production deployment template
└── .env.dev.example          # Development deployment template
```

---

## 🔧 Backend Environment Variables

File: `backend/.env`

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGO_URL` | ✅ Yes | - | MongoDB connection string for JobTalk dashboard database |
| `DB_NAME` | ✅ Yes | `recruitment_admin` | Database name for storing dashboard data |

**Examples:**
```bash
# Local MongoDB
MONGO_URL="mongodb://localhost:27017"

# MongoDB Atlas
MONGO_URL="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"

# MongoDB with authentication
MONGO_URL="mongodb://user:pass@host:27017/dbname?authSource=admin"
```

### Security Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | ✅ Yes | - | Secret key for JWT token signing (min 32 chars) |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_HOURS` | No | `8` | JWT token expiration time in hours |
| `ENCRYPTION_KEY` | ✅ Yes | - | AES-256 encryption key (exactly 32 characters) |

**Generate secure values:**
```bash
# JWT Secret (64 characters recommended)
openssl rand -hex 32

# Encryption Key (must be exactly 32 characters)
openssl rand -base64 32 | head -c 32
```

**Example:**
```bash
JWT_SECRET="a8f3c9d2e1b4f6a7c8d9e0f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY="ThisIsA32CharacterEncryptionK"
```

### AWS SES Configuration (Email Notifications)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | `JobTalk` | Application name used in emails |
| `AWS_ACCESS_KEY_ID` | Optional* | - | AWS access key for SES |
| `AWS_SECRET_ACCESS_KEY` | Optional* | - | AWS secret key for SES |
| `AWS_REGION` | No | `us-east-1` | AWS region for SES |
| `SMTP_FROM_EMAIL` | Optional* | - | Sender email address |

*Required only if you want email notifications/alerts

**Example:**
```bash
APP_NAME="JobTalk"
AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_REGION="us-east-1"
SMTP_FROM_EMAIL="noreply@yourdomain.com"
```

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NODE_ENV` | No | `development` | Environment mode (`development`, `production`) |
| `PORT` | No | `8001` | Backend server port |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins (comma-separated) |

**Example:**
```bash
NODE_ENV="development"
PORT=8001
CORS_ORIGINS="*"

# Production example:
# CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
```

### Complete Backend .env Example

```bash
# MongoDB Configuration
MONGO_URL="mongodb://localhost:27017"
DB_NAME="recruitment_admin"

# Security
JWT_SECRET="a8f3c9d2e1b4f6a7c8d9e0f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY="ThisIsA32CharacterEncryptionK"

# AWS SES (Optional)
APP_NAME="JobTalk"
AWS_ACCESS_KEY_ID="your-aws-access-key-id"
AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
AWS_REGION="us-east-1"
SMTP_FROM_EMAIL="noreply@yourdomain.com"

# Application
NODE_ENV="development"
PORT=8001
CORS_ORIGINS="*"
```

---

## 🎨 Frontend Environment Variables

File: `frontend/.env`

### API Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REACT_APP_BACKEND_URL` | ✅ Yes | - | Backend API URL |

**Examples:**
```bash
# Local development
REACT_APP_BACKEND_URL=http://localhost:8001

# Production
REACT_APP_BACKEND_URL=https://api.yourdomain.com

# Staging
REACT_APP_BACKEND_URL=https://staging-api.yourdomain.com
```

### Development Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REACT_APP_ENABLE_VISUAL_EDITS` | No | `false` | Enable visual editing mode |
| `ENABLE_HEALTH_CHECK` | No | `false` | Enable health check polling |

**Example:**
```bash
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
```

### Complete Frontend .env Example

```bash
# Backend API URL
REACT_APP_BACKEND_URL=http://localhost:8001

# Development settings
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
```

---

## 🚀 Deployment Environment Variables

### Production (.env.production.example)

For GitLab CI/CD and production deployment:

```bash
# Docker Image
CI_REGISTRY_IMAGE=registry.gitlab.com/your-username/jobtalk-admin
IMAGE_TAG=latest

# MongoDB Atlas
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=recruitment_admin_prod

# Security
JWT_SECRET=production-secret-key-64-characters-minimum
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY=prod-32-character-encryption-key

# AWS
APP_NAME=JobTalk
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
SMTP_FROM_EMAIL=noreply@yourdomain.com

# Application
NODE_ENV=production
PORT=8001
CORS_ORIGINS=https://yourdomain.com
```

### Development (.env.dev.example)

For development/staging deployment:

```bash
# Docker Image
CI_REGISTRY_IMAGE=registry.gitlab.com/your-username/jobtalk-admin
IMAGE_TAG=dev

# MongoDB Atlas
MONGO_URL=mongodb+srv://user:pass@cluster-dev.mongodb.net/
DB_NAME=recruitment_admin_dev

# Security (use different secrets than production!)
JWT_SECRET=dev-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
ENCRYPTION_KEY=dev-32-char-encryption-key123

# AWS
APP_NAME=JobTalk-Dev
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
SMTP_FROM_EMAIL=noreply@dev.yourdomain.com

# Application
NODE_ENV=development
PORT=8001
CORS_ORIGINS=*
```

---

## 🔐 Security Best Practices

### ✅ DO:

1. **Use `.env.example` files for templates**
   - Commit `.env.example` to git
   - Include placeholders, not real values

2. **Keep `.env` files secure**
   - Never commit actual `.env` files
   - Add to `.gitignore`
   - Different values for dev/staging/prod

3. **Use strong secrets**
   ```bash
   # Generate secure JWT secret
   openssl rand -hex 32
   
   # Generate encryption key (exactly 32 chars)
   openssl rand -base64 32 | head -c 32
   ```

4. **Use GitLab CI/CD Variables for deployment**
   - Store secrets in GitLab: Settings > CI/CD > Variables
   - Mark sensitive variables as "Masked" and "Protected"

5. **Rotate secrets regularly**
   - Change JWT secrets periodically
   - Rotate encryption keys
   - Update AWS credentials

### ❌ DON'T:

1. **Never commit `.env` files**
   ```bash
   # Bad - contains real credentials
   git add backend/.env
   ```

2. **Don't use weak secrets**
   ```bash
   # Bad examples
   JWT_SECRET="secret"
   ENCRYPTION_KEY="password123"
   ```

3. **Don't share secrets via chat/email**
   - Use secure password managers
   - Use environment variable injection

4. **Don't use same secrets across environments**
   ```bash
   # Bad - same secret for dev and prod
   # Use different values!
   ```

---

## 📝 Setup Checklist

### Local Development Setup

- [ ] Copy `backend/.env.example` to `backend/.env`
- [ ] Update `MONGO_URL` with your MongoDB connection
- [ ] Generate and set `JWT_SECRET` (64 characters)
- [ ] Generate and set `ENCRYPTION_KEY` (32 characters)
- [ ] Copy `frontend/.env.example` to `frontend/.env`
- [ ] Verify `REACT_APP_BACKEND_URL` is correct
- [ ] Test backend starts: `uvicorn server:app --reload`
- [ ] Test frontend starts: `yarn start`

### Production Deployment Setup

- [ ] Configure GitLab CI/CD variables (14 variables)
- [ ] Use strong, unique secrets for production
- [ ] Set `NODE_ENV=production`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Use MongoDB Atlas for production database
- [ ] Enable SSL/TLS for all connections
- [ ] Set up monitoring and alerts

---

## 🆘 Troubleshooting

### "MONGO_URL not found"

**Problem:** Backend can't find MongoDB connection string

**Solution:**
```bash
# Check if .env file exists
ls -la backend/.env

# If not, create from example
cd backend
cp .env.example .env

# Edit with your MongoDB URL
nano .env
```

### "Invalid encryption key length"

**Problem:** Encryption key is not exactly 32 characters

**Solution:**
```bash
# Generate correct length key
openssl rand -base64 32 | head -c 32

# Update in backend/.env
ENCRYPTION_KEY="your-generated-32-char-key12"
```

### "CORS error in browser"

**Problem:** Frontend can't connect to backend

**Solution:**
```bash
# In backend/.env, allow all origins for dev
CORS_ORIGINS="*"

# Or specific origin
CORS_ORIGINS="http://localhost:3000"
```

### "Backend URL not defined"

**Problem:** Frontend doesn't know where backend is

**Solution:**
```bash
# Check frontend/.env exists
ls -la frontend/.env

# If not, create it
cd frontend
cp .env.example .env

# Verify it contains:
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## 📚 Additional Resources

- [MongoDB Connection Strings](https://www.mongodb.com/docs/manual/reference/connection-string/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [AWS SES Setup](https://docs.aws.amazon.com/ses/latest/dg/setting-up.html)
- [React Environment Variables](https://create-react-app.dev/docs/adding-custom-environment-variables/)

---

**Last Updated:** January 2025
