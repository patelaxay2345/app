#!/bin/bash

# Quick Start: Add Partner with SSH Password Authentication
# This script makes it easy to add a partner using SSH password

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║  Quick Add Partner - SSH Password Authentication          ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will help you add a partner using SSH password."
echo "All credentials will be encrypted before storage."
echo ""

# Prompt for partner details
read -p "Partner Name: " PARTNER_NAME
echo ""

echo "Database Configuration:"
read -p "  Database Host: " PARTNER_DB_HOST
read -p "  Database Port [3306]: " PARTNER_DB_PORT
PARTNER_DB_PORT=${PARTNER_DB_PORT:-3306}
read -p "  Database Name: " PARTNER_DB_NAME
read -p "  Database User: " PARTNER_DB_USER
read -sp "  Database Password: " PARTNER_DB_PASSWORD
echo ""
echo ""

echo "SSH Configuration:"
read -p "  SSH Host: " PARTNER_SSH_HOST
read -p "  SSH Port [22]: " PARTNER_SSH_PORT
PARTNER_SSH_PORT=${PARTNER_SSH_PORT:-22}
read -p "  SSH Username: " PARTNER_SSH_USER
read -sp "  SSH Password: " PARTNER_SSH_PASSWORD
echo ""
echo ""

read -p "Concurrency Limit [50]: " PARTNER_CONCURRENCY_LIMIT
PARTNER_CONCURRENCY_LIMIT=${PARTNER_CONCURRENCY_LIMIT:-50}

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Partner Configuration Summary:"
echo "═══════════════════════════════════════════════════════════"
echo "  Partner Name: $PARTNER_NAME"
echo "  Database: $PARTNER_DB_HOST:$PARTNER_DB_PORT/$PARTNER_DB_NAME"
echo "  SSH Tunnel: $PARTNER_SSH_HOST:$PARTNER_SSH_PORT"
echo "  SSH User: $PARTNER_SSH_USER"
echo "  SSH Auth: Password"
echo "  Concurrency Limit: $PARTNER_CONCURRENCY_LIMIT"
echo "═══════════════════════════════════════════════════════════"
echo ""

read -p "Proceed with adding this partner? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Export variables
export PARTNER_NAME
export PARTNER_DB_HOST
export PARTNER_DB_PORT
export PARTNER_DB_NAME
export PARTNER_DB_USER
export PARTNER_DB_PASSWORD
export PARTNER_SSH_HOST
export PARTNER_SSH_PORT
export PARTNER_SSH_USER
export PARTNER_SSH_PASSWORD
export PARTNER_CONCURRENCY_LIMIT

# Run the add partner script
echo ""
echo "Adding partner..."
python3 scripts/add-partner.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Partner added successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Start backend: cd backend && uvicorn server:app --reload"
    echo "  2. Open dashboard: http://localhost:3000"
    echo "  3. Navigate to Partners page"
    echo "  4. Click 'Force Sync' to fetch real data"
else
    echo ""
    echo "❌ Failed to add partner. Check errors above."
fi

# Unset sensitive variables
unset PARTNER_DB_PASSWORD
unset PARTNER_SSH_PASSWORD
