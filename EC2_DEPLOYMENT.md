# 🚀 ECL Demo - AWS EC2 Deployment Guide

## Overview
Deploy ECL Studio on AWS EC2 with FalkorDB, Ollama, and Nginx in Docker containers.

**Estimated cost**: $20-50/month (t3.medium with EBS storage)
**Setup time**: 30-45 minutes
**Availability**: 99.9% (managed by Docker + systemd)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                      │
│  (Ubuntu 22.04 LTS, t3.medium, 4GB RAM, 50GB SSD)      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Nginx      │  │  ECL Studio  │  │  FalkorDB    │  │
│  │  Port 80/443 │  │  Port 8765   │  │  Port 6379   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                         ▲                      ▲         │
│                    (Upstream)            (Database)      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Ollama (LLM Inference)                │   │
│  │         Port 11434 (internal only)               │   │
│  │        Model: llama3:8b (~4GB RAM)               │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   Docker Network: ecl-network                    │   │
│  │   Volume Mounts: falkordb_data, ollama_data      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         ▲                                       
         │ HTTPS (port 443)
         │ HTTP (port 80)  
         │
    Internet
```

---

## Prerequisites

1. **AWS Account** with EC2 access
2. **Key pair** created (for SSH access)
3. **Security group** with:
   - Inbound: Port 80 (HTTP), 443 (HTTPS), 22 (SSH)
   - Outbound: All traffic

---

## Step 1: Launch EC2 Instance

### AWS Console
1. Go to **EC2 Dashboard** → **Instances** → **Launch Instances**
2. **Name**: `ecl-demo`
3. **AMI**: Ubuntu 22.04 LTS (Free Tier eligible)
4. **Instance Type**: `t3.medium` (or `t3.small` for POC)
5. **Storage**: 50 GB (gp3 recommended)
6. **Key Pair**: Select or create
7. **Security Group**: Create with rules above
8. **Launch**

### Or via AWS CLI

```bash
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --key-name your-key-name \
  --security-groups ecl-demo \
  --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3}" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ecl-demo}]'
```

**Note the instance IP/hostname** (e.g., `ec2-54-123-45-67.compute-1.amazonaws.com`)

---

## Step 2: Connect to EC2 & Install Docker

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group (so we don't need sudo)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

---

## Step 3: Clone Repository & Setup

```bash
# Navigate to home directory
cd ~

# Clone ECL repo (or copy files if private repo)
git clone https://github.com/accionlabs/ecg-demo.git ecl
cd ecl

# Set permissions
chmod +x docker-compose.yml
chmod +x Dockerfile
```

---

## Step 4: Pre-pull Docker Images (Optional but Recommended)

```bash
# Pre-pull images to speed up startup
docker pull python:3.11-slim
docker pull falkordb/falkordb:latest
docker pull ollama/ollama:latest
docker pull nginx:alpine

# Check disk space (should be ~20GB free)
df -h
```

---

## Step 5: Start the Stack

```bash
# Navigate to ECL directory
cd ~/ecl

# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Wait for services to be healthy (~60 seconds)
```

**Expected output:**
```
ecl-falkordb  | Ready to accept connections
ecl-ollama    | API running on 0.0.0.0:11434
ecl-studio    | Server: http://localhost:8765
ecl-nginx     | [notice] master process started
```

---

## Step 6: Pre-load LLM Model

```bash
# Pull llama3:8b model (takes 5-10 minutes on first run)
docker exec ecl-ollama ollama pull llama3:8b

# Verify
curl http://localhost:11434/api/tags
# Should return list with llama3:8b

# Keep running in background - model stays in memory
```

---

## Step 7: Verify Deployment

```bash
# Health check
curl http://localhost:8765/api/health
# Expected: {"status": "ok", "ollama_available": true, ...}

# Nginx reverse proxy
curl http://localhost/api/health

# Check all services
docker-compose ps
# All should show "Up" status
```

---

## Step 8: Access the Demo

### Option A: Direct IP
Open browser to:
```
http://your-instance-ip:8765
```

### Option B: Via Nginx Reverse Proxy
```
http://your-instance-ip
```

### Option C: Domain Name (Recommended)

1. **Get your Elastic IP** (AWS Console → Elastic IPs → Allocate & Associate)
2. **Point domain DNS to Elastic IP**
   ```
   A record: yourdomain.com → 54.123.45.67
   ```
3. **Update Nginx config**
   ```bash
   # Edit nginx.conf - replace server_name
   server_name yourdomain.com www.yourdomain.com;
   ```
4. **Restart Nginx**
   ```bash
   docker-compose restart nginx
   ```

---

## Step 9: Enable HTTPS (Optional but Recommended)

### Using Let's Encrypt + Certbot

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Generate certificate
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  --agree-tos \
  --email your-email@example.com

# Certificates will be at /etc/letsencrypt/live/yourdomain.com/

# Copy to container volume
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/ecl/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/ecl/ssl/key.pem
sudo chown $USER:$USER ~/ecl/ssl/*

# Uncomment HTTPS block in nginx.conf
# Edit ~/ecl/nginx.conf and uncomment the 443 server block

# Restart Nginx
docker-compose restart nginx

# Verify HTTPS
curl https://yourdomain.com/api/health
```

---

## Monitoring & Maintenance

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs ecl-studio
docker-compose logs ecl-ollama
docker-compose logs falkordb

# Follow live
docker-compose logs -f ecl-studio

# Last 100 lines
docker-compose logs --tail=100
```

### Monitor Resource Usage

```bash
# Container stats
docker stats

# Host system
free -h
df -h
top
```

### Health Checks

```bash
# All services status
docker-compose ps

# Test connectivity
curl http://localhost:8765/api/health
curl http://localhost:6379/ping  # FalkorDB
curl http://localhost:11434/api/tags  # Ollama
```

### Backup Database

```bash
# Backup FalkorDB data
docker-compose exec falkordb redis-cli BGSAVE

# Backup to local machine
scp -i your-key.pem -r ubuntu@your-instance-ip:~/ecl/falkordb_data ./backup-`date +%Y%m%d`
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart ecl-studio

# Full restart (stop + start)
docker-compose down
docker-compose up -d
```

---

## Troubleshooting

### ECL Studio Won't Start

```bash
# Check logs
docker-compose logs ecl-studio

# Verify dependencies
docker-compose ps
# All should show "Up"

# Restart
docker-compose restart ecl-studio
```

### Ollama Model Loading Issues

```bash
# Check if model is loaded
curl http://localhost:11434/api/tags

# If empty, pull model
docker exec ecl-ollama ollama pull llama3:8b

# If slow, check memory
docker stats ecl-ollama
# Should not exceed 6GB
```

### FalkorDB Connectivity Issues

```bash
# Check FalkorDB logs
docker-compose logs falkordb

# Test connection from ECL Studio
docker-compose exec ecl-studio python3 -c "import socket; socket.create_connection(('falkordb', 6379))"

# Check network
docker network inspect ecl-network
```

### Nginx 502 Bad Gateway

```bash
# Check upstream (ECL Studio)
curl http://ecl-studio:8765/api/health

# Check Nginx config
docker-compose exec nginx nginx -t

# Restart Nginx
docker-compose restart nginx
```

### Out of Disk Space

```bash
# Check usage
df -h

# Clean up Docker images
docker system prune -a --volumes

# Or increase EBS volume:
# 1. AWS Console → Volumes → Modify Volume Size
# 2. SSH into instance and extend filesystem
#    sudo resize2fs /dev/nvme0n1p1
```

---

## Security Best Practices

### 1. Restrict SSH Access
```bash
# Only allow SSH from your IP
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr YOUR.IP.ADDRESS/32
```

### 2. Use Secrets Management
```bash
# Store sensitive env vars
docker-compose exec ecl-studio \
  python3 -c "import os; print(os.getenv('OLLAMA_HOST'))"

# Or use .env file (add to .gitignore)
echo "OLLAMA_HOST=http://ollama:11434" > ~/ecl/.env
docker-compose --env-file .env up -d
```

### 3. Enable Firewall
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 4. Regular Backups
```bash
# Automated daily backup (add to crontab)
crontab -e
# Add: 0 2 * * * docker-compose exec falkordb redis-cli BGSAVE
```

---

## Cost Optimization

| Component | Instance | Monthly Cost | Notes |
|-----------|----------|--------------|-------|
| **EC2** | t3.medium | $30 | On-demand, use Spot for 70% savings |
| **Storage** | 50GB gp3 EBS | $5 | Adjust as needed |
| **Data Transfer** | 10GB/month | $0-1 | First 1GB free, then $0.12/GB |
| **Elastic IP** | 1 (if unused) | $3.65 | Only if not associated |
| **Total** | — | **~$38-40/month** | Or **~$12/month with Spot** |

### Save Money:
- Use **t3.small** ($15/month) for POC
- Use **Spot instances** ($9/month for t3.medium)
- Delete EBS snapshots after 30 days
- Use **Free Tier** (if eligible): $0 for 1 year

---

## Deployment Script (Automated)

```bash
#!/bin/bash
# deploy-ecl.sh - One-click deployment

set -e

echo "🚀 Deploying ECL to EC2..."

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
sudo usermod -aG docker $USER

# Clone repo
cd ~ && git clone https://github.com/accionlabs/ecg-demo.git ecl && cd ecl

# Start stack
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to be healthy..."
for i in {1..60}; do
  if curl -f http://localhost:8765/api/health > /dev/null 2>&1; then
    echo "✅ ECL Studio is ready!"
    break
  fi
  echo -n "."
  sleep 1
done

# Pre-load model
docker exec ecl-ollama ollama pull llama3:8b &

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Access at: http://$(hostname -I | awk '{print $1}'):8765"
echo ""
echo "Docker commands:"
echo "  docker-compose ps        # Check status"
echo "  docker-compose logs -f   # View logs"
echo "  docker-compose down      # Stop services"
```

Save as `deploy-ecl.sh`, then:
```bash
chmod +x deploy-ecl.sh
./deploy-ecl.sh
```

---

## Next Steps

1. **Test the demo**: `http://your-instance-ip:8765`
2. **Run extraction**: Load sample document, click "Extract"
3. **Monitor**: `docker-compose logs -f`
4. **Backup**: Regular FalkorDB snapshots
5. **Scale**: Add auto-scaling or load balancer for multi-region

---

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify health: `curl http://localhost:8765/api/health`
3. SSH into instance and debug manually

---

## Cost Calculator

Adjust for your needs:
```
EC2 Instance: t3.medium (4GB, 2vCPU) = $30/month
EBS Storage: 50GB gp3 = $5/month
Bandwidth: Estimate 10GB/month = $1/month
Elastic IP (if unused): $3.65/month

Total: ~$40/month
With Spot: ~$12/month
```

---

## Tear Down (When Done)

```bash
# Stop services
docker-compose down

# Terminate instance (AWS Console or CLI)
aws ec2 terminate-instances --instance-ids i-xxxxx

# Delete security group
aws ec2 delete-security-group --group-id sg-xxxxx

# Release Elastic IP
aws ec2 release-address --allocation-id eipalloc-xxxxx
```
