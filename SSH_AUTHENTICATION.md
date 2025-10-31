# SSH Authentication Options

JobTalk Admin Dashboard supports **two methods** for SSH tunnel authentication to partner databases.

## 🔐 Authentication Methods

### Method 1: SSH Password (Recommended ⭐)

**Advantages:**
- ✅ Simpler setup - just username and password
- ✅ No key file management
- ✅ Works immediately
- ✅ Easy to rotate credentials

**When to use:**
- Quick setup for testing
- When you have SSH password access
- Temporary connections
- Simple deployments

**Example:**
```bash
export PARTNER_SSH_USER="root"
export PARTNER_SSH_PASSWORD="your_secure_password"
```

---

### Method 2: SSH Private Key (Optional)

**Advantages:**
- ✅ More secure (no password in memory)
- ✅ Better for production
- ✅ Supports key rotation
- ✅ Can use passphrase-protected keys

**When to use:**
- Production environments
- When password authentication is disabled
- High-security requirements
- Automated deployments

**Example:**
```bash
# Option A: Direct key content
export PARTNER_SSH_KEY="$(cat ~/.ssh/partner_key)"

# Option B: Key file path (script will read it)
export PARTNER_SSH_KEY_PATH="/home/user/.ssh/partner_key"
```

---

## 📝 Complete Examples

### Example 1: Using SSH Password

```bash
# Partner: ApTask
# Authentication: SSH Password

export PARTNER_NAME="ApTask"
export PARTNER_DB_HOST="db.aptask.com"
export PARTNER_DB_PORT="3306"
export PARTNER_DB_NAME="aptask_prod"
export PARTNER_DB_USER="aptask_admin"
export PARTNER_DB_PASSWORD="db_secure_pass_2024"
export PARTNER_SSH_HOST="ssh.aptask.com"
export PARTNER_SSH_PORT="22"
export PARTNER_SSH_USER="root"
export PARTNER_SSH_PASSWORD="ssh_secure_pass_2024"
export PARTNER_CONCURRENCY_LIMIT="100"

# Add partner
python3 scripts/add-partner.py
```

### Example 2: Using SSH Private Key

```bash
# Partner: VendorX
# Authentication: SSH Private Key

export PARTNER_NAME="VendorX"
export PARTNER_DB_HOST="mysql.vendorx.com"
export PARTNER_DB_PORT="3306"
export PARTNER_DB_NAME="vendorx_db"
export PARTNER_DB_USER="readonly_user"
export PARTNER_DB_PASSWORD="db_password"
export PARTNER_SSH_HOST="tunnel.vendorx.com"
export PARTNER_SSH_PORT="22"
export PARTNER_SSH_USER="tunnel_user"
export PARTNER_SSH_KEY_PATH="$HOME/.ssh/vendorx_key"
export PARTNER_CONCURRENCY_LIMIT="50"

# Add partner
python3 scripts/add-partner.py
```

### Example 3: Using SSH Key with Passphrase (Future)

```bash
# Note: Passphrase support coming soon
export PARTNER_SSH_KEY_PATH="$HOME/.ssh/protected_key"
export PARTNER_SSH_PASSPHRASE="key_passphrase"
```

---

## 🔄 How It Works

### SSH Password Flow

```
1. Dashboard Backend
   ↓
2. SSH Password Authentication
   ↓
3. SSH Tunnel Created
   ↓
4. MySQL Connection through Tunnel
   ↓
5. Real Data Fetched
```

### SSH Key Flow

```
1. Dashboard Backend
   ↓
2. Load Private Key
   ↓
3. SSH Key Authentication
   ↓
4. SSH Tunnel Created
   ↓
5. MySQL Connection through Tunnel
   ↓
6. Real Data Fetched
```

---

## 🔐 Security Best Practices

### For SSH Passwords:

1. **Use Strong Passwords**
   - Minimum 16 characters
   - Mix of letters, numbers, symbols
   - Use password manager

2. **Rotate Regularly**
   - Change passwords every 90 days
   - Update in JobTalk after changing

3. **Limit Access**
   - Create dedicated SSH user
   - Restrict to specific IP addresses
   - Use sudo for elevated commands

### For SSH Keys:

1. **Generate Strong Keys**
   ```bash
   # RSA 4096-bit
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/partner_key
   
   # ED25519 (modern, secure)
   ssh-keygen -t ed25519 -f ~/.ssh/partner_key
   ```

2. **Protect Private Keys**
   - Set permissions: `chmod 600 ~/.ssh/partner_key`
   - Use passphrase protection
   - Never commit to git
   - Store in secure vault

3. **Key Management**
   - One key per partner
   - Document key locations
   - Have backup/recovery plan

---

## 🛠️ Troubleshooting

### SSH Password Issues

**Problem:** "Authentication failed"
```bash
# Solutions:
# 1. Verify password is correct
# 2. Check if password auth is enabled on server:
grep "PasswordAuthentication" /etc/ssh/sshd_config

# 3. Check account is not locked
sudo passwd -S username
```

**Problem:** "Permission denied"
```bash
# Solutions:
# 1. Verify username exists
# 2. Check SSH service is running
# 3. Verify firewall allows SSH
```

### SSH Key Issues

**Problem:** "Key load failed"
```bash
# Solutions:
# 1. Check key format:
head -1 ~/.ssh/partner_key
# Should start with: "-----BEGIN OPENSSH PRIVATE KEY-----"

# 2. Verify key permissions:
chmod 600 ~/.ssh/partner_key

# 3. Test key manually:
ssh -i ~/.ssh/partner_key user@host
```

**Problem:** "Public key denied"
```bash
# Solutions:
# 1. Verify public key is in authorized_keys:
ssh user@host "cat ~/.ssh/authorized_keys"

# 2. Check authorized_keys permissions:
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

---

## 📊 Comparison

| Feature | SSH Password | SSH Private Key |
|---------|--------------|-----------------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐ Moderate |
| **Security** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Ease of Rotation** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Moderate |
| **Production Ready** | ⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Highly |
| **Quick Testing** | ⭐⭐⭐⭐⭐ Perfect | ⭐⭐⭐ Good |
| **Automation** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |

---

## ✅ Recommendation

**For Development/Testing:**
- Use **SSH Password** - faster setup, easier to get started

**For Production:**
- Use **SSH Private Key** - better security, audit trail

**For Both:**
- Encrypt credentials (done automatically by JobTalk)
- Use dedicated accounts
- Monitor access logs
- Rotate credentials regularly

---

## 🔗 Related Documentation

- [Add Partner Script](./scripts/README.md)
- [Environment Variables](./ENV_VARIABLES.md)
- [Security Best Practices](./FIXING_SECRET_LEAKS.md)

---

**Last Updated:** November 2025
