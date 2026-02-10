# 📋 ECL EC2 Deployment - Complete Summary

**Status**: ✅ Ready to deploy
**Last Updated**: February 2026
**Audience**: DevOps, SREs, Solutions Engineers

---

## What's Included

This deployment package includes everything needed to run ECL Studio on AWS EC2:

### Docker Containers (4)
1. **ecl-studio** — Backend API server (Python)
2. **falkordb** — Graph database (Redis-compatible)
3. **ollama** — Local LLM inference engine
4. **nginx** — Reverse proxy & load balancer

### Configuration Files
- `docker-compose.yml` — Orchestration
- `Dockerfile` — ECL Studio image
- `nginx.conf` — Web server config
- `requirements.txt` — Python dependencies
- `ecl-cloudformation.yaml` — One-click CloudFormation template

### Deployment Scripts
- `deploy-ec2.sh` — Automated deployment (recommended)
- `AWS_QUICK_START.md` — 5-minute quick start
- `EC2_DEPLOYMENT.md` — Complete reference guide

---

## Deployment Options

### Option 1: Automated Script (Recommended)
**Best for**: Quick deployment, minimal manual work

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Run deployment script
bash deploy-ec2.sh

# Wait 15-20 minutes
# Access: http://your-instance-ip:8765
```

**Pros**: One command, handles everything
**Cons**: Requires Ubuntu 22.04, internet connectivity

**Time**: ~20 minutes

---

### Option 2: CloudFormation Template
**Best for**: Enterprise, repeatable deployments

```bash
# Via AWS Console
# 1. Go to CloudFormation → Create Stack
# 2. Upload: ecl-cloudformation.yaml
# 3. Fill in parameters (instance type, key pair)
# 4. Create stack
# 5. Wait for CREATE_COMPLETE
# 6. Access via Outputs tab

# Or via AWS CLI
aws cloudformation create-stack \
  --stack-name ecl-demo \
  --template-body file://ecl-cloudformation.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=your-key-name \
               ParameterKey=InstanceType,ParameterValue=t3.medium
```

**Pros**: Infrastructure as Code, easy rollback, repeatable
**Cons**: More AWS-specific knowledge required

**Time**: ~25 minutes

---

### Option 3: Manual Deployment
**Best for**: Learning, custom configurations

```bash
# See EC2_DEPLOYMENT.md for step-by-step instructions
# Covers Docker installation, configuration, troubleshooting

# Key steps:
# 1. SSH to instance
# 2. Install Docker
# 3. Clone repository
# 4. Configure docker-compose.yml
# 5. Start services
# 6. Monitor logs
```

**Pros**: Full control, understand each step
**Cons**: Time-consuming, requires Docker knowledge

**Time**: ~45 minutes

---

## Quick Comparison

| Aspect | Script | CloudFormation | Manual |
|--------|--------|----------------|--------|
| **Setup Time** | 20 min | 25 min | 45 min |
| **Automation** | ✓ Full | ✓ Full | ✗ None |
| **Learning Curve** | Easy | Medium | Hard |
| **Cost Visibility** | Good | Excellent | None |
| **Rollback** | Manual | ✓ Automatic | ✗ None |
| **Customization** | Good | Excellent | ✓ Full |
| **Recommended** | ✓✓✓ | ✓✓ | ✓ |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Internet / Users                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Nginx (443)   │ ← HTTPS Reverse Proxy
                    │  Load Balancer │
                    └───────┬────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
        ┌───▼──────┐  ┌─────▼──────┐  ┌───▼──────┐
        │ ECL      │  │ FalkorDB   │  │  Ollama  │
        │ Studio   │  │   Graph    │  │   LLM    │
        │ (8765)   │  │   (6379)   │  │ (11434)  │
        └──────────┘  └────────────┘  └──────────┘
        
        All services on single t3.medium EC2 instance
        Total: ~4GB RAM, 2 vCPU, 50GB storage
```

---

## Resource Requirements

### EC2 Instance
| Component | t3.small | t3.medium | t3.large |
|-----------|----------|-----------|----------|
| vCPU | 2 | 2 | 2 |
| RAM | 2GB | 4GB | 8GB |
| Network | 5 Gbps | 5 Gbps | 5 Gbps |
| Baseline CPU | 10% | 20% | 30% |

### Storage
- **Root Volume**: 50GB gp3 (EBS)
  - OS: ~3GB
  - Docker images: ~15GB
  - Ollama models: ~4GB (llama3:8b)
  - Data/logs: ~2GB

### Estimated Monthly Costs
```
Instance (t3.medium):    $30.00
Storage (50GB gp3):      $5.00
Data transfer (typical): $0-2.00
Elastic IP (if unused):  $3.65
─────────────────────────────
Total:                   ~$40/month

With Spot Instances:     ~$12/month
With Reserved (1 year):  ~$18/month
```

---

## Pre-Deployment Checklist

- [ ] AWS account with EC2 access
- [ ] EC2 key pair created and saved locally
- [ ] Security group created or configured
- [ ] Instance type selected (t3.medium recommended)
- [ ] Storage size confirmed (50GB minimum)
- [ ] Budget alerts configured (optional but recommended)
- [ ] Internet connectivity verified
- [ ] DNS/domain configured (optional)
- [ ] SSL certificates ready (optional)

---

## Post-Deployment Checklist

- [ ] Services are running: `docker-compose ps`
- [ ] All containers show "Up" status
- [ ] Health check passes: `curl http://localhost:8765/api/health`
- [ ] Ollama model loaded: `curl http://localhost:11434/api/tags`
- [ ] Browser access works: `http://instance-ip:8765`
- [ ] Can load sample document in UI
- [ ] Can run extraction successfully
- [ ] Logs are clean: `docker-compose logs | grep -i error`
- [ ] Backups configured (optional)
- [ ] CloudWatch alarms set up (optional)

---

## Deployment Checklist by Method

### Script Deployment
- [ ] SSH access verified
- [ ] Internet connectivity checked
- [ ] Downloaded deploy-ec2.sh
- [ ] Run: `bash deploy-ec2.sh`
- [ ] Wait for completion
- [ ] Verify access

### CloudFormation Deployment
- [ ] AWS Console access verified
- [ ] EC2 key pair selected
- [ ] Template uploaded
- [ ] Parameters filled in
- [ ] Stack created
- [ ] Wait for CREATE_COMPLETE
- [ ] Check Outputs tab for URLs

### Manual Deployment
- [ ] SSH access verified
- [ ] Ubuntu 22.04 confirmed
- [ ] Followed EC2_DEPLOYMENT.md step-by-step
- [ ] Verified each service startup
- [ ] Tested all endpoints
- [ ] Confirmed extraction works

---

## Key Files Reference

| File | Purpose | Size |
|------|---------|------|
| `docker-compose.yml` | Service orchestration | 4KB |
| `Dockerfile` | ECL Studio image | 1KB |
| `nginx.conf` | Web server config | 3KB |
| `requirements.txt` | Python dependencies | 1KB |
| `deploy-ec2.sh` | Deployment script | 10KB |
| `EC2_DEPLOYMENT.md` | Full reference | 50KB |
| `AWS_QUICK_START.md` | Quick start guide | 15KB |
| `ecl-cloudformation.yaml` | CloudFormation template | 20KB |

---

## Service Ports

| Service | Port | Protocol | Internal | Public |
|---------|------|----------|----------|--------|
| Nginx | 80 | HTTP | ✓ | ✓ |
| Nginx | 443 | HTTPS | ✓ | ✓ |
| ECL Studio | 8765 | HTTP | ✓ | ✗ |
| FalkorDB | 6379 | Redis | ✓ | ✗ |
| Ollama | 11434 | HTTP | ✓ | ✗ |
| SSH | 22 | TCP | ✗ | ✓ |

---

## Monitoring & Alerts

### CloudWatch Integration
```bash
# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

### Docker Resource Monitoring
```bash
# Real-time stats
docker stats

# CPU percentage
docker stats --no-stream --format "{{.Container}} {{.CPUPerc}} {{.MemUsage}}"

# Historical logs
docker-compose logs ecl-studio | tail -100
```

### Health Checks
```bash
# Full health status
curl http://localhost:8765/api/health

# Service connectivity
docker-compose ps

# Network connectivity
docker network inspect ecl-network
```

---

## Backup & Recovery

### Backup Strategy
```bash
# Daily FalkorDB backup (add to crontab)
0 2 * * * cd ~/ecl && docker-compose exec -T falkordb redis-cli BGSAVE

# Download locally
aws s3 sync ~/ecl/falkordb_data s3://your-bucket/backups/$(date +%Y%m%d)

# Retention: Keep 30 days
aws s3 rm s3://your-bucket/backups --recursive --exclude "*/2025-12-*"
```

### Recovery Procedure
```bash
# 1. SSH to instance
# 2. Stop services
docker-compose stop falkordb

# 3. Restore data
aws s3 sync s3://your-bucket/backups/YYYYMMDD ./falkordb_data

# 4. Start services
docker-compose start falkordb

# 5. Verify
curl http://localhost:8765/api/health
```

---

## Scaling Options

### Vertical Scaling
```bash
# Upgrade instance size (requires restart)
# 1. Stop instance
# 2. Change instance type (AWS Console)
# 3. Start instance
# Downtime: ~2 minutes
```

### Horizontal Scaling
```bash
# For production multi-region:
# 1. Deploy another instance in different AZ
# 2. Configure Application Load Balancer
# 3. Route traffic between instances
# See AWS documentation for details
```

### Storage Scaling
```bash
# Increase EBS volume size
aws ec2 modify-volume --volume-id vol-xxxxx --size 100

# Extend filesystem
sudo resize2fs /dev/nvme0n1p1

# Verify
df -h
```

---

## Cost Optimization Tips

1. **Use Spot Instances**: 70% savings (~$12/month)
2. **Reserved Instances**: 40% savings (~$18/month for 1-year)
3. **Right-size instance**: Start with t3.small if POC
4. **Monitor usage**: Use CloudWatch to find unused resources
5. **Shut down when not needed**: Stop instance (~$2/month storage only)
6. **Use Free Tier**: If eligible, first year free

---

## Security Best Practices

1. **Restrict SSH**: Only from your IP
2. **Use IAM roles**: Instead of hardcoded credentials
3. **Enable VPC Flow Logs**: Monitor network traffic
4. **Set CloudWatch Alarms**: Unused resources, high costs
5. **Regular updates**: `apt update && apt upgrade`
6. **Strong passwords**: If not using key-based auth
7. **Backup data**: Regular snapshots of FalkorDB
8. **Monitor logs**: Review CloudWatch logs regularly
9. **Use HTTPS**: Enable TLS/SSL
10. **Firewall rules**: Only open needed ports

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Services won't start | See "ECL Studio Won't Start" in EC2_DEPLOYMENT.md |
| Slow performance | Check "Performance Tuning" section |
| High costs | Review cost optimization tips above |
| Can't SSH | Verify security group and key pair |
| 502 Gateway error | Restart nginx: `docker-compose restart nginx` |
| No internet | Check security group egress rules |
| Disk full | Run `docker system prune` |
| Memory issues | Increase instance size or use Spot |

---

## FAQ

**Q: Can I use free tier?**
A: Yes, if you have an eligible AWS account. t3.micro has 1GB RAM (marginal), t3.small recommended.

**Q: Can I deploy to a different region?**
A: Yes. Update CloudFormation parameters or modify instance setup.

**Q: How do I upgrade the instance?**
A: Stop instance → Change instance type → Start. ~2 min downtime.

**Q: Is data persistent?**
A: Yes. FalkorDB data is in EBS volume, persists across restarts.

**Q: Can I use GPU for faster inference?**
A: Yes, but costs more. Use g4dn.xlarge (~$500/month). See EC2_DEPLOYMENT.md.

**Q: How do I delete everything?**
A: CloudFormation: Delete stack. Manual: Terminate instance + delete security group.

**Q: Can I use my own domain?**
A: Yes. Point DNS A record to Elastic IP, update nginx.conf, restart.

**Q: How do I enable HTTPS?**
A: Use Let's Encrypt with Certbot. See EC2_DEPLOYMENT.md section "Enable HTTPS".

---

## Next Steps After Deployment

1. **Test the demo** (5 min)
   - Open http://instance-ip:8765
   - Click "Load Sample"
   - Click "Extract"
   - View results

2. **Configure domain** (optional, 10 min)
   - Get Elastic IP
   - Point DNS A record
   - Update nginx.conf
   - Restart nginx

3. **Enable HTTPS** (optional, 15 min)
   - Install Certbot
   - Generate certificate
   - Update nginx.conf
   - Restart nginx

4. **Set up monitoring** (optional, 10 min)
   - Create CloudWatch alarms
   - Configure SNS notifications
   - Set budget alerts

5. **Schedule backups** (optional, 5 min)
   - Add to crontab
   - Upload to S3
   - Configure retention policy

---

## Support Resources

- **AWS EC2 Documentation**: https://docs.aws.amazon.com/ec2/
- **Docker Documentation**: https://docs.docker.com/
- **FalkorDB Docs**: https://docs.falkordb.com/
- **Ollama Docs**: https://ollama.ai/
- **ECL Internal Docs**: See EC2_DEPLOYMENT.md, DEMO_PLAYBOOK.md
- **GitHub**: https://github.com/accionlabs/ecg-demo

---

**Deployment ready. Happy demoing! 🚀**
