#!/bin/bash

# Deployment script for JobTalk Admin Dashboard
# Usage: ./deploy.sh [production|dev]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
APP_DIR="/opt/jobtalk-admin"

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}JobTalk Admin Dashboard Deployment${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Validate environment
if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "dev" ]]; then
    echo -e "${RED}Error: Invalid environment. Use 'production' or 'dev'${NC}"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# Navigate to application directory
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: Application directory $APP_DIR does not exist${NC}"
    exit 1
fi

cd "$APP_DIR"

# Determine branch and compose file
if [ "$ENVIRONMENT" = "production" ]; then
    BRANCH="main"
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
    PORT="80"
else
    BRANCH="dev"
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_FILE=".env.dev"
    PORT="8080"
fi

echo -e "${YELLOW}Step 1: Pulling latest code from $BRANCH branch...${NC}"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file $ENV_FILE not found${NC}"
    echo -e "${YELLOW}Please create $ENV_FILE with required variables${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 2: Pulling Docker image...${NC}"
# Read image name from env file
IMAGE=$(grep CI_REGISTRY_IMAGE "$ENV_FILE" | cut -d '=' -f2)
TAG=$(grep IMAGE_TAG "$ENV_FILE" | cut -d '=' -f2)

if [ -z "$IMAGE" ] || [ -z "$TAG" ]; then
    echo -e "${RED}Error: IMAGE or TAG not found in $ENV_FILE${NC}"
    exit 1
fi

docker pull "$IMAGE:$TAG" || {
    echo -e "${RED}Error: Failed to pull Docker image${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker image pulled${NC}"
echo ""

echo -e "${YELLOW}Step 3: Stopping existing containers...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
echo -e "${GREEN}✓ Containers stopped${NC}"
echo ""

echo -e "${YELLOW}Step 4: Starting new containers...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
echo -e "${GREEN}✓ Containers started${NC}"
echo ""

echo -e "${YELLOW}Step 5: Waiting for application to be healthy...${NC}"
sleep 10

HEALTH_CHECK_PASSED=false
for i in {1..30}; do
    if curl -f http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is healthy!${NC}"
        HEALTH_CHECK_PASSED=true
        break
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 2
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo -e "${RED}✗ Health check failed!${NC}"
    echo -e "${YELLOW}Showing last 50 log lines:${NC}"
    docker-compose -f "$COMPOSE_FILE" logs --tail=50
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 6: Cleaning up old Docker images...${NC}"
docker image prune -af --filter "until=72h" > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "Access your application at:"
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "  ${GREEN}http://$(curl -s ifconfig.me)${NC}"
else
    echo -e "  ${GREEN}http://$(curl -s ifconfig.me):8080${NC}"
fi
echo ""
echo -e "View logs with:"
echo -e "  ${YELLOW}docker-compose -f $COMPOSE_FILE logs -f${NC}"
echo ""
