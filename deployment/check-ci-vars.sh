#!/bin/bash

# GitLab CI/CD Variables Checker
# This script helps verify that all required CI/CD variables are set

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}GitLab CI/CD Variables Checker${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

echo "This script will guide you through setting up GitLab CI/CD variables."
echo "Go to: Settings > CI/CD > Variables in your GitLab project"
echo ""

# Required variables
declare -A REQUIRED_VARS=(
    ["LINODE_SSH_HOST"]="Your Linode server IP address"
    ["LINODE_SSH_USER"]="SSH username (usually 'root')"
    ["LINODE_SSH_PRIVATE_KEY"]="SSH private key for deployment (mark as Protected and Masked)"
    ["MONGO_URL_PROD"]="MongoDB Atlas connection string for production"
    ["MONGO_URL_DEV"]="MongoDB Atlas connection string for development"
    ["JWT_SECRET_PROD"]="JWT secret for production (64+ random characters)"
    ["JWT_SECRET_DEV"]="JWT secret for development (64+ random characters)"
    ["ENCRYPTION_KEY_PROD"]="Encryption key for production (exactly 32 characters)"
    ["ENCRYPTION_KEY_DEV"]="Encryption key for development (exactly 32 characters)"
    ["AWS_ACCESS_KEY_ID"]="AWS access key for SES email service"
    ["AWS_SECRET_ACCESS_KEY"]="AWS secret access key for SES"
    ["SMTP_FROM_EMAIL"]="Email address for sending emails (e.g., noreply@yourdomain.com)"
    ["CORS_ORIGINS_PROD"]="Production CORS origins (e.g., https://yourdomain.com)"
    ["CORS_ORIGINS_DEV"]="Development CORS origins (use '*' for dev)"
)

echo -e "${YELLOW}Required GitLab CI/CD Variables:${NC}"
echo ""

counter=1
for var in "${!REQUIRED_VARS[@]}"; do
    description="${REQUIRED_VARS[$var]}"
    echo -e "${counter}. ${GREEN}${var}${NC}"
    echo -e "   Description: ${description}"
    
    # Add special notes for certain variables
    case $var in
        "LINODE_SSH_PRIVATE_KEY")
            echo -e "   ${YELLOW}Note: Mark as Protected and Masked${NC}"
            echo -e "   ${YELLOW}Generate: ssh-keygen -t ed25519 -f ~/.ssh/gitlab_deploy${NC}"
            ;;
        "JWT_SECRET_PROD"|"JWT_SECRET_DEV")
            echo -e "   ${YELLOW}Generate: openssl rand -hex 32${NC}"
            ;;
        "ENCRYPTION_KEY_PROD"|"ENCRYPTION_KEY_DEV")
            echo -e "   ${YELLOW}Generate: openssl rand -base64 32 | head -c 32${NC}"
            ;;
        "MONGO_URL_PROD"|"MONGO_URL_DEV")
            echo -e "   ${YELLOW}Format: mongodb+srv://user:pass@cluster.mongodb.net/${NC}"
            ;;
    esac
    
    echo ""
    ((counter++))
done

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}Quick Generate Commands:${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

echo "# Generate JWT Secret (64 characters):"
echo "openssl rand -hex 32"
echo ""

echo "# Generate Encryption Key (32 characters):"
echo "openssl rand -base64 32 | head -c 32"
echo ""

echo "# Generate SSH Key Pair:"
echo "ssh-keygen -t ed25519 -f ~/.ssh/gitlab_deploy -N ''"
echo "# Add public key to server:"
echo "ssh-copy-id -i ~/.ssh/gitlab_deploy.pub root@your-linode-ip"
echo "# Copy private key to GitLab:"
echo "cat ~/.ssh/gitlab_deploy"
echo ""

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}Protection Settings:${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

echo "Mark as Protected (only for protected branches):"
echo "  - LINODE_SSH_PRIVATE_KEY"
echo "  - MONGO_URL_PROD"
echo "  - JWT_SECRET_PROD"
echo "  - ENCRYPTION_KEY_PROD"
echo "  - AWS_SECRET_ACCESS_KEY"
echo ""

echo "Mark as Masked (hide in logs):"
echo "  - LINODE_SSH_PRIVATE_KEY"
echo "  - MONGO_URL_PROD"
echo "  - MONGO_URL_DEV"
echo "  - JWT_SECRET_PROD"
echo "  - JWT_SECRET_DEV"
echo "  - ENCRYPTION_KEY_PROD"
echo "  - ENCRYPTION_KEY_DEV"
echo "  - AWS_SECRET_ACCESS_KEY"
echo ""

echo -e "${YELLOW}After adding all variables, push to 'main' or 'dev' branch to trigger deployment.${NC}"
