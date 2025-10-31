# Fixing GitHub Secret Scanning Issues

This guide explains how to resolve the GitHub secret scanning error and prevent it in the future.

## 🚨 The Problem

GitHub detected sensitive credentials in your commits:
- Aiven Service Password
- SSH Private Keys
- Database credentials

These were found in:
- `backend/.env`
- `add-aptask-partner.py`
- `test-partner-setup.py`
- `test-ssh-mongo.py`
- `test-ssh-tunnel.py`
- `test-mysql-tunnel.py`

## ✅ What We've Done

1. **Removed files from tracking**
   - Removed sensitive files from git tracking
   - Updated `.gitignore` to prevent future commits

2. **Created safe alternatives**
   - `scripts/add-partner.py` - Uses environment variables
   - `backend/.env.example` - Template without credentials
   - `frontend/.env.example` - Template without credentials

3. **Updated documentation**
   - `ENV_VARIABLES.md` - Environment variable guide
   - `scripts/README.md` - Script usage guide

## 🔧 Quick Fix Options

### Option 1: Allow Secret (Temporary - Not Recommended)

If you need to push immediately:

1. Click the GitHub link provided in the error message
2. Click "Allow secret" 
3. Push your changes

**⚠️ Warning:** This doesn't remove the secret from history!

### Option 2: Remove from Git History (Recommended)

Remove sensitive files from ALL commits:

```bash
# Install git-filter-repo
# macOS:
brew install git-filter-repo

# Linux:
pip3 install git-filter-repo

# Run cleanup script
./scripts/cleanup-git-history.sh

# Force push to remote
git push origin main --force
```

### Option 3: Fresh Repository (Nuclear Option)

If you don't need the git history:

```bash
# 1. Backup your code
cp -r /app /app-backup

# 2. Remove git history
rm -rf .git

# 3. Initialize fresh repository
git init
git add .
git commit -m "Initial commit without sensitive data"

# 4. Push to new repository
git remote add origin <your-repo-url>
git push -u origin main --force
```

## 🛡️ Prevention for Future

### 1. Always Use .env.example Files

**❌ Never commit:**
```bash
git add backend/.env  # WRONG!
```

**✅ Always commit:**
```bash
git add backend/.env.example  # CORRECT!
```

### 2. Verify Before Commit

```bash
# Check what you're about to commit
git status
git diff --cached

# Look for sensitive data
grep -r "password\|secret\|key" backend/.env
```

### 3. Use Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Check for .env files
if git diff --cached --name-only | grep -E '\.env$|\.env\..*$' | grep -v '\.example$'; then
    echo "❌ Error: Attempting to commit .env file!"
    echo "   Remove it from staging: git reset backend/.env"
    exit 1
fi

# Check for common secret patterns
if git diff --cached | grep -iE 'password.*=.*[^example]|secret.*=.*[^example]|key.*=.*[^example]'; then
    echo "⚠️  Warning: Potential secrets detected in commit"
    echo "   Review your changes carefully"
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        exit 1
    fi
fi

exit 0
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### 4. Use Environment Variables for Scripts

**❌ Hardcoded (BAD):**
```python
password = "AVNS_ME4QjhAtv17LviPV32D"  # NEVER DO THIS!
```

**✅ Environment Variable (GOOD):**
```python
password = os.getenv('PARTNER_DB_PASSWORD')  # ALWAYS DO THIS!
```

### 5. Enable GitHub Secret Scanning

1. Go to repository settings
2. Navigate to: Settings > Security > Code security and analysis  
3. Enable "Secret scanning"
4. Enable "Push protection"

This will block pushes with secrets before they reach GitHub.

## 📋 Checklist After Fix

After fixing the secret leak:

- [ ] Secrets removed from git history
- [ ] `.gitignore` updated to exclude sensitive files
- [ ] `.env.example` files created for all environments
- [ ] All test scripts use environment variables
- [ ] Pre-commit hooks installed (optional)
- [ ] GitHub secret scanning enabled
- [ ] **IMPORTANT:** Rotate/change all exposed credentials

## 🔑 Rotate Compromised Credentials

Since the credentials were exposed, you should rotate them:

### Database Credentials
1. Change database password in Aiven/database provider
2. Update in your local `.env` file
3. Update in partner configuration

### SSH Keys
1. Generate new SSH key pair
2. Add new public key to servers
3. Remove old public key
4. Update partner configuration with new key

### MongoDB Connection Strings
1. Create new database user
2. Update connection string
3. Remove old user

## 📞 Need Help?

- [GitHub Secret Scanning Docs](https://docs.github.com/en/code-security/secret-scanning)
- [git-filter-repo Guide](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

## ✨ After Fix

Once fixed:

```bash
# Verify no secrets in history
git log --all --full-history --source -- backend/.env

# Should return empty

# Safe to push
git push origin main
```

---

**Remember:** Prevention is better than cure. Always use `.env.example` files and environment variables!
