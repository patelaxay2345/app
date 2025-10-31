# Scripts Directory

Utility scripts for JobTalk Admin Dashboard management.

## 📁 Available Scripts

### add-partner.py

Add a new partner configuration to the JobTalk dashboard database.

**Usage:**

```bash
# Set environment variables with partner credentials
export PARTNER_NAME="PartnerName"
export PARTNER_DB_HOST="db.example.com"
export PARTNER_DB_PORT="3306"
export PARTNER_DB_NAME="database_name"
export PARTNER_DB_USER="db_username"
export PARTNER_DB_PASSWORD="db_password"
export PARTNER_SSH_HOST="ssh.example.com"
export PARTNER_SSH_PORT="22"
export PARTNER_SSH_USER="ssh_username"
export PARTNER_SSH_KEY="$(cat ~/.ssh/id_rsa)"  # OR
export PARTNER_SSH_PASSWORD="ssh_password"
export PARTNER_CONCURRENCY_LIMIT="50"

# Run the script
python3 scripts/add-partner.py
```

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `PARTNER_NAME` | Yes | Partner display name |
| `PARTNER_DB_HOST` | Yes | Database host address |
| `PARTNER_DB_PORT` | No | Database port (default: 3306) |
| `PARTNER_DB_NAME` | Yes | Database name |
| `PARTNER_DB_USER` | Yes | Database username |
| `PARTNER_DB_PASSWORD` | Yes | Database password |
| `PARTNER_SSH_HOST` | Yes | SSH server address |
| `PARTNER_SSH_PORT` | No | SSH port (default: 22) |
| `PARTNER_SSH_USER` | Yes | SSH username |
| `PARTNER_SSH_KEY` | Optional* | SSH private key |
| `PARTNER_SSH_PASSWORD` | Optional* | SSH password |
| `PARTNER_CONCURRENCY_LIMIT` | No | Max concurrent calls (default: 50) |

*Either `PARTNER_SSH_KEY` or `PARTNER_SSH_PASSWORD` must be provided.

**Example:**

```bash
# Using SSH private key
export PARTNER_NAME="ApTask"
export PARTNER_DB_HOST="db.aptask.com"
export PARTNER_DB_PORT="3306"
export PARTNER_DB_NAME="aptask_prod"
export PARTNER_DB_USER="aptask_user"
export PARTNER_DB_PASSWORD="secure_password"
export PARTNER_SSH_HOST="ssh.aptask.com"
export PARTNER_SSH_USER="root"
export PARTNER_SSH_KEY="$(cat ~/.ssh/aptask_key)"
export PARTNER_CONCURRENCY_LIMIT="100"

python3 scripts/add-partner.py
```

## 🔐 Security Notes

- **Never commit credentials to git**
- Use environment variables for all sensitive data
- SSH keys and passwords are encrypted before storage
- Database passwords are encrypted using AES-256

## 🆘 Troubleshooting

**"MONGO_URL not found"**
- Make sure `backend/.env` exists with valid MongoDB connection

**"Missing required environment variables"**
- Verify all required variables are exported
- Check spelling of variable names

**"Failed to connect to database"**
- Ensure MongoDB is running
- Check `MONGO_URL` in `backend/.env`

## 📚 Additional Resources

- [Environment Variables Guide](../ENV_VARIABLES.md)
- [Project Setup Guide](../PROJECT_SETUP.md)
- [Deployment Guide](../DEPLOYMENT.md)
