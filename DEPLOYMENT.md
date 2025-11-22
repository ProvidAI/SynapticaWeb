# AWS EC2 Deployment Guide

This guide walks you through deploying the Synaptica backend (FastAPI API, Research Agents, and PostgreSQL) on AWS EC2.

## Architecture

The deployment includes:
- **Backend API** (Port 8000): Main orchestrator API
- **Research Agents** (Port 5001): AI research agents server
- **PostgreSQL** (Port 5432): Database for tasks, payments, and agent data
- **Nginx** (Port 80/443): Reverse proxy and load balancer

## Prerequisites

1. **AWS Account** with EC2 access
2. **API Keys**:
   - OpenAI API key or Anthropic API key
   - Hedera account credentials (for blockchain features)
   - Optional: Tavily, Serper, Pinata API keys

## Step 1: Launch EC2 Instance

### Recommended Instance Type
- **Type**: `t3.medium` or larger (2 vCPU, 4GB RAM minimum)
- **For production**: `t3.large` or `t3.xlarge` recommended

### Launch Instance

1. Go to AWS EC2 Console
2. Click **Launch Instance**
3. Configure:
   - **Name**: `synaptica-backend`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t3.medium` or larger
   - **Key pair**: Create new or use existing (you'll need this to SSH)
   - **Storage**: 30 GB gp3 (minimum)
   - **Network settings**:
     - Create security group with:
       - SSH (port 22) - Your IP only
       - HTTP (port 80) - Anywhere
       - HTTPS (port 443) - Anywhere (for future SSL)

4. Click **Launch Instance**

### Configure Security Group

After launch, edit the security group to allow:

| Type  | Protocol | Port | Source    | Description          |
|-------|----------|------|-----------|----------------------|
| SSH   | TCP      | 22   | Your IP   | SSH access           |
| HTTP  | TCP      | 80   | 0.0.0.0/0 | Web traffic          |
| HTTPS | TCP      | 443  | 0.0.0.0/0 | Secure web (future)  |

## Step 2: Connect to EC2 Instance

```bash
# Get your instance's public IP from AWS console
ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

## Step 3: Clone Repository

```bash
# Install git if needed
sudo apt-get update
sudo apt-get install -y git

# Clone your repository
git clone https://github.com/your-username/synaptica-web.git
cd synaptica-web
```

**Alternative**: If your repo is private, you can use SCP to transfer files:

```bash
# From your local machine
scp -i /path/to/your-key.pem -r /path/to/synaptica-web ubuntu@<EC2_PUBLIC_IP>:~/
```

## Step 4: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your actual values
nano .env
```

### Required Environment Variables

```bash
# AI API Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Hedera Blockchain (required for agent marketplace features)
HEDERA_ACCOUNT_ID=0.0.xxxxx
HEDERA_PRIVATE_KEY=302e...
HEDERA_RPC_URL=https://testnet.hashio.io/api

# Database (auto-configured in docker-compose, but you can override)
POSTGRES_PASSWORD=your_secure_password_here

# Contract Addresses (if you have deployed contracts)
IDENTITY_CONTRACT_ADDRESS=0x...
REPUTATION_CONTRACT_ADDRESS=0x...
VALIDATION_CONTRACT_ADDRESS=0x...

# Optional: Research Enhancement APIs
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...
PINATA_API_KEY=...
PINATA_SECRET_KEY=...
```

Save and exit (Ctrl+X, Y, Enter in nano).

## Step 5: Deploy Application

Run the automated deployment script:

```bash
# Make the script executable (if not already)
chmod +x deploy-ec2.sh

# Run deployment
./deploy-ec2.sh
```

The script will:
1. Update system packages
2. Install Docker and Docker Compose
3. Build application containers
4. Start all services (PostgreSQL, Backend, Research Agents, Nginx)
5. Verify service health

**Note**: If Docker group changes are needed, you may need to log out and back in, then run the script again.

## Step 6: Verify Deployment

### Check Service Status

```bash
# View all running containers
docker-compose ps

# Check logs
docker-compose logs -f backend
docker-compose logs -f research-agents
docker-compose logs -f postgres
```

### Test API Endpoints

```bash
# Get your EC2 public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Test main API health
curl http://$PUBLIC_IP/health

# Test research agents
curl http://$PUBLIC_IP/agents

# Test main API info
curl http://$PUBLIC_IP/
```

Expected responses should show JSON with status information.

## Step 7: Test Task Execution

```bash
# Execute a simple research task
curl -X POST http://$PUBLIC_IP/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Research the latest developments in quantum computing",
    "budget_limit": 10.0,
    "min_reputation_score": 0.7
  }'

# You'll get a task_id in response. Check status:
curl http://$PUBLIC_IP/api/tasks/<task_id>
```

## Managing the Application

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f research-agents
docker-compose logs -f postgres
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Stop Services

```bash
docker-compose down
```

### Start Services

```bash
docker-compose up -d
```

### Update Application Code

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U synaptica_user -d synaptica

# Backup database
docker-compose exec postgres pg_dump -U synaptica_user synaptica > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U synaptica_user -d synaptica
```

## Production Recommendations

### 1. SSL/HTTPS Setup

Use Let's Encrypt for free SSL certificates:

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Certificates auto-renew, but test renewal:
sudo certbot renew --dry-run
```

Then update [nginx.conf](nginx.conf) to use the SSL configuration block.

### 2. Set Up Monitoring

```bash
# Install monitoring tools
docker run -d \
  --name=cadvisor \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  google/cadvisor:latest
```

### 3. Configure Firewall

```bash
# Enable UFW firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. Set Up Automatic Backups

Create a backup script:

```bash
#!/bin/bash
# Save as /opt/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U synaptica_user synaptica > /opt/backups/db_$DATE.sql
# Keep only last 7 days
find /opt/backups -name "db_*.sql" -mtime +7 -delete
```

Add to crontab:

```bash
# Run daily at 2 AM
0 2 * * * /opt/backup.sh
```

### 5. Resource Limits

Edit [docker-compose.yml](docker-compose.yml) to add resource limits:

```yaml
services:
  backend:
    # ... existing config
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose logs backend
docker-compose logs research-agents

# Verify environment variables
cat .env

# Check if ports are already in use
sudo netstat -tulpn | grep -E ':(80|5001|8000|5432)'
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U synaptica_user -d synaptica -c "SELECT 1;"
```

### Out of Memory

```bash
# Check system resources
free -h
docker stats

# Reduce number of workers or upgrade instance type
```

### API Returns 502 Bad Gateway

```bash
# Check if backend is healthy
docker-compose ps backend
curl http://localhost:8000/health

# Check nginx logs
docker-compose logs nginx

# Restart backend
docker-compose restart backend
```

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/execute` | POST | Execute a task |
| `/api/tasks/{task_id}` | GET | Get task status |
| `/api/tasks/history` | GET | Task history |
| `/agents` | GET | List research agents |
| `/agents/{agent_id}` | GET | Get agent metadata |
| `/agents/{agent_id}` | POST | Execute specific agent |

## Cost Estimation

**AWS EC2 Costs** (approximate, us-east-1):
- `t3.medium`: ~$30/month
- `t3.large`: ~$60/month
- `t3.xlarge`: ~$120/month

**Plus**:
- EBS storage: ~$3/GB/month
- Data transfer: First 100GB free, then $0.09/GB

**API Costs**:
- OpenAI API: Pay per token usage
- Anthropic API: Pay per token usage
- Varies based on usage

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review [README.md](README.md)
- Open an issue on GitHub

## Next Steps

- Set up custom domain name
- Configure SSL/HTTPS
- Implement monitoring and alerting
- Set up CI/CD pipeline
- Configure auto-scaling
