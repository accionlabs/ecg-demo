# ⚡ ECL on AWS - Quick Start (5 minutes)

## TL;DR - Complete in 5 steps

### 1. Launch EC2 Instance
```bash
# AWS Console → EC2 → Launch Instances
# - AMI: Ubuntu 22.04 LTS
# - Type: t3.medium (or t3.small for POC)
# - Storage: 50GB gp3
# - Security: Allow ports 22, 80, 443
# - Launch
```

### 2. SSH Into Instance
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### 3. Run Deployment Script
```bash
# Download and run in one command
curl -fsSL https://raw.githubusercontent.com/accionlabs/ecg-demo/main/deploy-ec2.sh | bash

# Or if you have the file locally:
bash deploy-ec2.sh
```

### 4. Wait for Setup (15-20 minutes)
```
✓ Docker installed
✓ Repository cloned
✓ Services started (FalkorDB, Ollama, ECL Studio)
✓ Model pre-loaded (llama3:8b)
```

### 5. Access Demo
```
Open browser: http://your-instance-ip:8765
```

---

## Quick Setup Checklist

- [ ] EC2 instance launched (Ubuntu 22.04, t3.medium, 50GB)
- [ ] Key pair saved locally
- [ ] Security group configured (ports 22, 80, 443)
- [ ] Got instance IP: ________________
- [ ] SSH works: `ssh -i your-key.pem ubuntu@<IP>`
- [ ] Deployment script running: `bash deploy-ec2.sh`
- [ ] Services healthy: `docker-compose ps` (all "Up")
- [ ] Model loaded: `curl http://localhost:11434/api/tags`
- [ ] Browser access works: `http://<IP>:8765`

---

## Instance Sizing Guide

| Use Case | Instance | Cost/mo | RAM | vCPU | Notes |
|----------|----------|---------|-----|------|-------|
| **POC/Demo** | t3.small | $15 | 2GB | 2 | Works but slower |
| **Production** | t3.medium | $30 | 4GB | 2 | **Recommended** |
| **High Traffic** | t3.large | $60 | 8GB | 2 | Scale if needed |
| **GPU (optional)** | g4dn.xlarge | $500 | 16GB | 1 + GPU | For faster inference |

---

## Common Issues & Fixes

### "Connection refused" when accessing http://IP:8765

```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs ecl-studio

# Restart services
docker-compose restart
```

### Slow response times

```bash
# Check resource usage
docker stats

# If memory low: https://github.com/docker-library/docker/issues/3696
# Increase swap: sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
```

### Model not loading

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Manually pull model
docker exec ecl-ollama ollama pull llama3:8b

# Check disk space
df -h
```

### "502 Bad Gateway" from Nginx

```bash
# Verify ECL Studio is running
curl http://localhost:8765/api/health

# Restart Nginx
docker-compose restart nginx
```

---

## Performance Tuning

### For Demo (POC)
```bash
# Use regex mode (faster, less memory)
# Disable LLM in UI or use smaller model
docker exec ecl-ollama ollama pull tinyllama
```

### For Production
```bash
# Use Ollama with GPU
docker run --gpus all -d -p 11434:11434 ollama/ollama

# Use larger model if time permits
docker exec ecl-ollama ollama pull llama2-70b
```

---

## Cost Estimate

```
EC2 t3.medium:        $30/month
EBS 50GB gp3:         $5/month
Data transfer:        $0-2/month
Elastic IP (if used): $3.65/month
────────────────────────────
Total:                ~$40/month

Or with Spot Instances: ~$12/month
```

---

## Post-Deployment

### 1. Set Up Domain (Optional)

```bash
# Get Elastic IP
aws ec2 allocate-address --domain vpc

# Point your domain DNS to the IP
# A record: yourdomain.com → 54.x.x.x

# SSH in and configure
ssh -i your-key.pem ubuntu@your-instance-ip

# Update nginx.conf
nano nginx.conf
# Change: server_name yourdomain.com;

# Restart Nginx
docker-compose restart nginx
```

### 2. Enable HTTPS (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com --agree-tos --email you@example.com

# Copy to container
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem

# Uncomment HTTPS in nginx.conf
# Restart
docker-compose restart nginx

# Visit https://yourdomain.com
```

### 3. Set Up Backups

```bash
# Daily backup (add to crontab)
echo "0 2 * * * cd ~/ecl && docker-compose exec -T falkordb redis-cli BGSAVE" | crontab -

# Download to local
aws s3 cp s3://your-bucket/backups/ . --recursive
```

### 4. Monitor & Alert

```bash
# CloudWatch agent (optional)
aws ssm send-command --document-name "AWS-ConfigureAWSPackage" --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}'

# Or use simple monitoring
docker stats --no-stream >> /tmp/ecl-stats.log
```

---

## Tear Down

```bash
# Stop services
docker-compose down

# Terminate instance
aws ec2 terminate-instances --instance-ids i-xxxxx

# Clean up security group
aws ec2 delete-security-group --group-id sg-xxxxx

# Release Elastic IP
aws ec2 release-address --allocation-id eipalloc-xxxxx
```

---

## Useful Commands

```bash
# View all containers
docker-compose ps

# View logs (live)
docker-compose logs -f

# View specific service logs
docker-compose logs ecl-studio

# Enter container shell
docker exec -it ecl-studio bash

# View resource usage
docker stats

# Stop all services
docker-compose stop

# Start all services
docker-compose start

# Restart single service
docker-compose restart ecl-studio

# Check health
curl http://localhost:8765/api/health

# Full logs from start
docker-compose logs --tail=1000

# Build/rebuild containers
docker-compose build

# Pull latest images
docker-compose pull

# Update and restart
docker-compose pull && docker-compose up -d
```

---

## Next Steps

1. **Test extraction**: Load sample document in UI
2. **Run full demo**: Follow DEMO_PLAYBOOK.md
3. **Configure domain**: Point DNS if using custom domain
4. **Enable HTTPS**: Use Let's Encrypt
5. **Set up backups**: Schedule daily FalkorDB snapshots
6. **Monitor**: Watch `docker stats` for resource usage

---

## Support Resources

- **Deployment issues**: Check EC2_DEPLOYMENT.md
- **Demo walkthrough**: See DEMO_PLAYBOOK.md
- **Architecture**: Read MARKET_RESEARCH.md
- **Logs**: `docker-compose logs -f`
- **AWS Docs**: https://docs.aws.amazon.com/ec2/

---

## Cost Alerts

To prevent surprise bills, set up AWS Budget:
1. Go to **Billing** → **Budgets**
2. Set threshold: $50/month
3. Add email notification
4. Create alert

---

✅ **You're ready to deploy!**
