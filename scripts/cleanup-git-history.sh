#!/bin/bash

# Git History Cleanup Script
# This script helps remove sensitive files from git history

echo "======================================================================"
echo "  Git History Cleanup - Remove Sensitive Files"
echo "======================================================================"
echo ""
echo "⚠️  WARNING: This will rewrite git history!"
echo "   Only proceed if you understand the consequences."
echo ""
echo "Files to be removed from history:"
echo "  - backend/.env"
echo "  - add-aptask-partner.py"
echo "  - test-partner-setup.py"
echo "  - test-ssh-mongo.py"
echo "  - test-ssh-tunnel.py"
echo "  - test-mysql-tunnel.py"
echo ""

read -p "Do you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborting..."
    exit 0
fi

echo ""
echo "Removing sensitive files from git history..."
echo ""

# Use git filter-repo (recommended) or BFG Repo-Cleaner
# First, check if git-filter-repo is installed
if command -v git-filter-repo &> /dev/null; then
    echo "Using git-filter-repo..."
    git filter-repo --invert-paths \
        --path backend/.env \
        --path add-aptask-partner.py \
        --path test-partner-setup.py \
        --path test-ssh-mongo.py \
        --path test-ssh-tunnel.py \
        --path test-mysql-tunnel.py \
        --force
    
    echo ""
    echo "✅ Files removed from git history!"
    echo ""
    echo "Next steps:"
    echo "  1. Force push to remote:"
    echo "     git push origin main --force"
    echo ""
    echo "  2. All team members must re-clone the repository"
    echo ""
    
else
    echo "❌ git-filter-repo not found!"
    echo ""
    echo "Please install git-filter-repo:"
    echo ""
    echo "  # macOS"
    echo "  brew install git-filter-repo"
    echo ""
    echo "  # Linux (Ubuntu/Debian)"
    echo "  pip3 install git-filter-repo"
    echo ""
    echo "  # Or download from:"
    echo "  https://github.com/newren/git-filter-repo"
    echo ""
    echo "Alternatively, you can:"
    echo "  1. Allow the secret in GitHub (temporary)"
    echo "  2. Or create a fresh repository without the history"
    exit 1
fi
