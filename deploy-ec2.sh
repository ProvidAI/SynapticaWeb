#!/bin/bash
# AWS EC2 Deployment Script for Synaptica Backend
# This script sets up Docker and deploys the application on a fresh EC2 instance

set -e

echo "================================================"
echo "Synaptica Backend - AWS EC2 Deployment"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Update system packages
echo -e "${GREEN}[1/7] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${GREEN}[2/7] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${YELLOW}Docker installed. You may need to log out and back in for group changes to take effect.${NC}"
else
    echo "Docker already installed"
fi

# Install Docker Compose
echo -e "${GREEN}[3/7] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose already installed"
fi

# Verify installations
docker --version
docker-compose --version

# Create application directory
echo -e "${GREEN}[4/7] Setting up application directory...${NC}"
APP_DIR="/opt/synaptica"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Check if .env file exists
echo -e "${GREEN}[5/7] Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Please edit .env file with your actual configuration values!${NC}"
    echo -e "${YELLOW}Required variables:${NC}"
    echo "  - OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo "  - HEDERA_ACCOUNT_ID, HEDERA_PRIVATE_KEY"
    echo "  - POSTGRES_PASSWORD (recommended to change)"
    echo "  - Other API keys as needed"
    echo ""
    read -p "Press enter to continue after updating .env file..."
fi

# Create data directory
mkdir -p ./data

# Build and start containers
echo -e "${GREEN}[6/7] Building and starting Docker containers...${NC}"
docker-compose down || true
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be healthy
echo -e "${GREEN}[7/7] Waiting for services to be healthy...${NC}"
sleep 10

# Check service status
echo ""
echo -e "${GREEN}Checking service health...${NC}"
echo "================================================"

# Check PostgreSQL
if docker-compose ps postgres | grep -q "healthy"; then
    echo -e "${GREEN}✓ PostgreSQL: Running${NC}"
else
    echo -e "${RED}✗ PostgreSQL: Not healthy${NC}"
fi

# Check Research Agents
if docker-compose ps research-agents | grep -q "healthy"; then
    echo -e "${GREEN}✓ Research Agents: Running${NC}"
else
    echo -e "${RED}✗ Research Agents: Not healthy${NC}"
fi

# Check Backend
if docker-compose ps backend | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend API: Running${NC}"
else
    echo -e "${RED}✗ Backend API: Not healthy${NC}"
fi

# Check Nginx
if docker-compose ps nginx | grep -q "Up"; then
    echo -e "${GREEN}✓ Nginx: Running${NC}"
else
    echo -e "${RED}✗ Nginx: Not running${NC}"
fi

echo "================================================"
echo ""

# Get EC2 public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "localhost")

echo -e "${GREEN}Deployment Complete!${NC}"
echo ""
echo "Your services are available at:"
echo "  - Main API: http://$PUBLIC_IP/health"
echo "  - Research Agents: http://$PUBLIC_IP/agents"
echo "  - Execute Task: POST http://$PUBLIC_IP/execute"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f backend"
echo "  docker-compose logs -f research-agents"
echo "  docker-compose logs -f postgres"
echo ""
echo "To restart services:"
echo "  docker-compose restart"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo -e "${YELLOW}Note: Configure your EC2 Security Group to allow inbound traffic on ports 80, 443${NC}"
