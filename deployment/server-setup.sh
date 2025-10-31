#!/bin/bash

# Server setup script for JobTalk Admin Dashboard
# Run this script on your Linode server as root

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}JobTalk Server Setup${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   exit 1
fi

echo -e "${YELLOW}Step 1: Updating system...${NC}"
apt update && apt upgrade -y
echo -e "${GREEN}✓ System updated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker already installed${NC}"
else
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 3: Installing Docker Compose...${NC}"
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}Docker Compose already installed${NC}"
else
    apt install docker-compose -y
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 4: Installing Git...${NC}"
if command -v git &> /dev/null; then
    echo -e "${GREEN}Git already installed${NC}"
else
    apt install git -y
    echo -e "${GREEN}✓ Git installed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 5: Installing additional tools...${NC}"
apt install curl wget htop nano ufw -y
echo -e "${GREEN}✓ Additional tools installed${NC}"
echo ""

echo -e "${YELLOW}Step 6: Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8080/tcp  # Dev environment
echo -e "${GREEN}✓ Firewall configured${NC}"
echo ""

echo -e "${YELLOW}Step 7: Setting up swap (4GB)...${NC}"
if [ -f /swapfile ]; then
    echo -e "${GREEN}Swap already exists${NC}"
else
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✓ Swap configured${NC}"
fi
echo ""

echo -e "${YELLOW}Step 8: Creating application directory...${NC}"
mkdir -p /opt/jobtalk-admin
echo -e "${GREEN}✓ Application directory created${NC}"
echo ""

echo -e "${YELLOW}Step 9: Generating SSH key for GitLab...${NC}"
if [ -f ~/.ssh/id_ed25519 ]; then
    echo -e "${GREEN}SSH key already exists${NC}"
else
    ssh-keygen -t ed25519 -C "deployment@jobtalk" -f ~/.ssh/id_ed25519 -N ""
    echo -e "${GREEN}✓ SSH key generated${NC}"
fi

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}✓ Server setup completed!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add this SSH public key to GitLab as a Deploy Key:"
echo -e "${GREEN}$(cat ~/.ssh/id_ed25519.pub)${NC}"
echo ""
echo "2. Clone your repository:"
echo -e "${YELLOW}cd /opt/jobtalk-admin${NC}"
echo -e "${YELLOW}git clone git@gitlab.com:your-username/jobtalk-admin.git .${NC}"
echo ""
echo "3. Configure GitLab CI/CD variables as described in DEPLOYMENT.md"
echo ""
echo "4. Push to main or dev branch to trigger deployment"
echo ""
