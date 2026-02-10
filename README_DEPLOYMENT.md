# 🚀 ECL Demo - AWS EC2 Deployment Guide

**Status**: ✅ Ready for Production Deployment  
**Last Updated**: February 10, 2026  
**Repository**: https://github.com/accionlabs/ecg-demo

---

## Quick Start (3 minutes)

```bash
# 1. Install AWS CLI
brew install awscli  # macOS
# OR: see AWS_CLI_SETUP.md for Linux/Windows

# 2. Configure credentials
aws configure

# 3. Create EC2 key pair
aws ec2 create-key-pair --key-name ecl-demo --region us-east-1 --query 'KeyMaterial' --output text > ecl-demo.pem
chmod 600 ecl-demo.pem

# 4. Deploy
cd /path/to/ecg-demo
bash launch-ec2.sh

# 5. Wait ~25 minutes, then open browser
http://your-public-ip:8765
```

---

## What Gets Deployed

Single AWS CloudFormation stack containing:

- **EC2 Instance** (t3.medium, 4GB RAM, 50GB storage)
- **FalkorDB** (Graph database on port 6379)
- **Ollama** (LLM inference engine on port 11434)
- **ECL Studio** (Backend server on port 8765)
- **Nginx** (Reverse proxy on ports 80/443)
- **CloudWatch** (Monitoring & alarms)
- **Security Group** (Ports 22, 80, 443)
- **IAM Role** (EC2 permissions)
- **Elastic IP** (Static public IP)

Total deployment time: ~25 minutes  
Total monthly cost: ~$40 (or ~$20 for 2-week summit)

---

## Documentation Files

### Start Here 👇
1. **DEPLOY_NOW.md** — 3-minute quick reference
2. **launch-ec2.sh** — Run this script to deploy

### Setup & Installation
- **AWS_CLI_SETUP.md** — Install AWS CLI (all platforms)
- **AWS_QUICK_START.md** — 5-minute quick start

### Complete Reference
- **EC2_DEPLOYMENT.md** — 50-page comprehensive guide
- **DEPLOYMENT_SUMMARY.md** — Overview & checklists
- **DEPLOYMENT_READY.txt** — Status file

### Presentation Materials
- **SPEAKER_NOTES.md** — 15-minute presentation script
- **DEMO_PLAYBOOK.md** — Live demo walkthrough
- **MARKET_RESEARCH.md** — Competitive analysis (Lyzr, Corvic, Extend, LandingAI)

### Infrastructure Code
- **docker-compose.yml** — Container orchestration
- **Dockerfile** — ECL Studio image
- **nginx.conf** — Web server configuration
- **ecl-cloudformation.yaml** — Infrastructure as Code
- **deploy-ec2.sh** — Alternative deployment script
- **requirements.txt** — Python dependencies

---

## Prerequisites

- ✅ AWS Account with EC2 access
- ✅ AWS CLI installed (`aws --version`)
- ✅ AWS credentials configured (`aws configure`)
- ✅ EC2 key pair (or create one)
- ✅ Internet connectivity
- ✅ 10-15 minutes of setup time

---

## Deployment Process

### Step 1: Verify AWS Setup (2 min)
```bash
# Check AWS CLI
aws --version

# Check credentials
aws sts get-caller-identity
# Output: Account ID, User ARN, etc.

# List available key pairs
aws ec2 describe-key-pairs --region us-east-1
```

### Step 2: Create EC2 Key Pair (2 min)
```bash
# Create new key pair
aws ec2 create-key-pair --key-name ecl-demo --region us-east-1 --query 'KeyMaterial' --output text > ecl-demo.pem

# Secure the private key
chmod 600 ecl-demo.pem

# Keep this file safe! (Add to .gitignore)
echo "*.pem" >> .gitignore
```

### Step 3: Clone Repository (1 min)
```bash
# If you haven't already
git clone https://github.com/accionlabs/ecg-demo.git
cd ecg-demo

# Or if already cloned
git pull origin main
```

### Step 4: Run Deployment Script (20 min)
```bash
# Execute the deployment
bash launch-ec2.sh

# Follow the prompts:
# 1. Select key pair: ecl-demo
# 2. Confirm parameters
# 3. Wait for CloudFormation (CREATE_COMPLETE)
```

### Step 5: Access the Demo (1 min)
```bash
# From script output, you'll get:
# - Public IP: 54.123.45.67
# - HTTP URL: http://54.123.45.67:8765
# - SSH: ssh -i ecl-demo.pem ubuntu@54.123.45.67

# Open browser to:
http://your-public-ip:8765
```

---

## What Happens During Deployment

```
0 min    → CloudFormation stack creation initiated
2 min    → EC2 instance launching
5 min    → Docker and Docker Compose installing
10 min   → Repository cloning
15 min   → Containers starting (FalkorDB, Ollama, ECL, Nginx)
20 min   → ECL Studio health check passing
25 min   → Ollama model (llama3:8b) fully loaded
25+ min  → Ready for use!
```

**Tip**: Model loading (Ollama) is the longest step. Grab coffee ☕

---

## Cost Breakdown

### Per Instance
| Component | Cost | Notes |
|-----------|------|-------|
| EC2 t3.medium | $30/month | On-demand pricing |
| EBS Storage (50GB) | $5/month | gp3 SSD |
| Data Transfer | $0-2/month | Typical usage |
| Elastic IP | $3.65/month | If unused (optional) |
| **Total** | **~$40/month** | **$1.30/day** |

### For Different Durations
- **2-week summit**: ~$20
- **1-month demo**: ~$40
- **3-month POC**: ~$120

### Cost Optimization
- Use **Spot Instances**: 70% savings (~$12/month)
- Use **t3.small**: ~$15/month (marginal performance)
- **Delete when done**: No storage costs if instance terminated

---

## Post-Deployment

### Access the Demo
```bash
# Via browser
http://your-public-ip:8765

# Or with custom domain
# 1. Point DNS A record to Elastic IP
# 2. Update nginx.conf: server_name yourdomain.com;
# 3. Restart Nginx: docker-compose restart nginx
```

### Run the Presentation
1. Follow **SPEAKER_NOTES.md** (15 minutes)
2. Show live extraction demo
3. Discuss competitive positioning
4. Calculate ROI

### Monitor Deployment
```bash
# SSH into instance
ssh -i ecl-demo.pem ubuntu@your-ip

# Check services
docker-compose ps          # Status of all containers
docker-compose logs -f     # Live logs
docker stats               # Resource usage
curl localhost:8765/api/health  # Health check
```

### Enable HTTPS (Optional)
```bash
# See EC2_DEPLOYMENT.md section "Enable HTTPS"
# Uses Let's Encrypt + Certbot
```

### Setup Backups (Optional)
```bash
# Add daily backup to crontab
crontab -e
# Add: 0 2 * * * cd ~/ecl && docker-compose exec -T falkordb redis-cli BGSAVE
```

---

## Troubleshooting

### AWS CLI Issues
- **"aws: command not found"** → Install AWS CLI (see AWS_CLI_SETUP.md)
- **"Unable to locate credentials"** → Run `aws configure`
- **"Key pair not found"** → Create: `aws ec2 create-key-pair --key-name ecl-demo`

### Deployment Issues
- **Stack creation fails** → Check: `aws cloudformation describe-stack-events --stack-name $STACK`
- **Services not responding** → Wait 5 more minutes (model loading)
- **"502 Bad Gateway"** → SSH in and restart: `docker-compose restart nginx`

### Cost Issues
- **Unexpected charges** → Delete stack: `aws cloudformation delete-stack --stack-name $STACK`
- **High usage** → Check: `docker stats` and `aws cloudwatch get-metric-statistics`

See **EC2_DEPLOYMENT.md** for comprehensive troubleshooting.

---

## Cleanup

### Delete Everything
```bash
STACK_NAME="ecl-demo-xxxxx"  # From script output

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region us-east-1

# Wait for deletion (~5 minutes)
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"

# Verify deletion
aws cloudformation describe-stacks --stack-name "$STACK_NAME"
# Should error: "Stack does not exist"
```

### Delete Key Pair (Optional)
```bash
aws ec2 delete-key-pair --key-name ecl-demo --region us-east-1
```

### Verify All Resources Deleted
```bash
# Check EC2 instances
aws ec2 describe-instances --filters "Name=key-name,Values=ecl-demo"

# Check Elastic IPs
aws ec2 describe-addresses --filters "Name=tag:Name,Values=ecl-demo-eip"

# Check volumes
aws ec2 describe-volumes --filters "Name=tag:Name,Values=ecl-demo-*"
```

---

## Key Commands

### Monitoring
```bash
# CloudFormation stack status
aws cloudformation describe-stacks --stack-name $STACK

# Instance details
aws ec2 describe-instances --instance-ids $INSTANCE_ID

# Resource usage (via SSH)
ssh -i ecl-demo.pem ubuntu@$IP docker stats

# Logs (via SSH)
ssh -i ecl-demo.pem ubuntu@$IP docker-compose logs -f ecl-studio
```

### Management
```bash
# Stop instance (keeps data, costs less)
aws ec2 stop-instances --instance-ids $INSTANCE_ID

# Start instance
aws ec2 start-instances --instance-ids $INSTANCE_ID

# Reboot
aws ec2 reboot-instances --instance-ids $INSTANCE_ID

# Terminate (deletes everything)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

### Backup/Restore
```bash
# Create EBS snapshot (via SSH)
ssh -i ecl-demo.pem ubuntu@$IP docker-compose exec -T falkordb redis-cli BGSAVE

# Download data
scp -i ecl-demo.pem -r ubuntu@$IP:/home/ubuntu/ecl/traces ./backup-$(date +%Y%m%d)
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              AWS EC2 Instance                    │
│         (t3.medium, 50GB storage)               │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Nginx   │  │ECL Studio│  │FalkorDB  │     │
│  │ 80/443   │  │   8765   │  │   6379   │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│        ▲              ▲              ▲          │
│        └──────────────┴──────────────┘          │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │      Ollama (LLM Inference)            │    │
│  │      Port 11434 (internal only)        │    │
│  │      Model: llama3:8b (~4GB)           │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │   Docker Network (ecl-network)         │    │
│  │   Volumes: falkordb_data, ollama_data  │    │
│  └────────────────────────────────────────┘    │
│                                                  │
└─────────────────────────────────────────────────┘
         ▲                              
         │ HTTPS (443)                  
         │ HTTP (80)                    
         │ SSH (22)                     
         │
      Internet
```

---

## Support Resources

### Quick Help
- **DEPLOY_NOW.md** — 3-minute guide
- **AWS_CLI_SETUP.md** — CLI installation
- **EC2_DEPLOYMENT.md** — Full reference
- **Troubleshooting** — See EC2_DEPLOYMENT.md section

### AWS Documentation
- [CloudFormation](https://docs.aws.amazon.com/cloudformation/)
- [EC2](https://docs.aws.amazon.com/ec2/)
- [AWS CLI](https://docs.aws.amazon.com/cli/)

### Project Documentation
- [SPEAKER_NOTES.md](SPEAKER_NOTES.md) — Presentation
- [DEMO_PLAYBOOK.md](DEMO_PLAYBOOK.md) — Demo walkthrough
- [MARKET_RESEARCH.md](MARKET_RESEARCH.md) — Competitive analysis

---

## Next Steps

1. **Read DEPLOY_NOW.md** (3 minutes)
2. **Setup AWS CLI** (5 minutes, see AWS_CLI_SETUP.md)
3. **Run launch-ec2.sh** (20 minutes)
4. **Open browser** (1 minute)
5. **Test extraction** (5 minutes)
6. **Run full demo** (15 minutes, see SPEAKER_NOTES.md)

---

## Summary

✅ All infrastructure as code  
✅ One-click deployment via CloudFormation  
✅ Fully automated setup (AWS CLI + shell scripts)  
✅ Production-ready with monitoring & alarms  
✅ Complete documentation (8+ guides)  
✅ Ready to present at summit  

**Total time from start to demo**: ~30 minutes  
**Total cost for 2-week summit**: ~$20  

---

**Questions?** See the appropriate guide above.  
**Ready to deploy?** Run: `bash launch-ec2.sh`

🚀 Let's go!
