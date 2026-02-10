# 🚀 DEPLOY ECL NOW - Quick Reference

## All Files Ready to Deploy ✅

**Repo**: https://github.com/accionlabs/ecg-demo
**Branch**: main
**Status**: Ready for production

---

## In 3 Minutes

### 1. Ensure AWS CLI is installed
```bash
aws --version
# If not: see AWS_CLI_SETUP.md
```

### 2. Run deployment
```bash
cd /path/to/ecg-demo
bash launch-ec2.sh
```

### 3. Follow prompts
- Select EC2 key pair
- Confirm parameters
- Wait ~25 minutes

### 4. Access demo
- Browser: `http://your-public-ip:8765`
- SSH: `ssh -i ecl-demo.pem ubuntu@your-ip`

---

## What Gets Deployed

✅ **FalkorDB** — Graph database (port 6379)
✅ **Ollama** — LLM inference (port 11434)
✅ **ECL Studio** — Backend server (port 8765)
✅ **Nginx** — Reverse proxy (port 80/443)
✅ **CloudWatch** — Monitoring & alarms
✅ **Security Group** — Ports 22, 80, 443
✅ **IAM Role** — EC2 permissions
✅ **Elastic IP** — Static public IP

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `launch-ec2.sh` | 🎯 Main deployment script |
| `ecl-cloudformation.yaml` | Infrastructure template |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | ECL Studio image |
| `nginx.conf` | Web server config |
| `requirements.txt` | Python dependencies |
| `deploy-ec2.sh` | Alternative EC2 setup script |
| `AWS_CLI_SETUP.md` | AWS CLI installation guide |
| `AWS_QUICK_START.md` | 5-minute quick start |
| `EC2_DEPLOYMENT.md` | Complete reference (50 pages) |
| `DEPLOYMENT_SUMMARY.md` | Overview & checklists |
| `MARKET_RESEARCH.md` | Competitive analysis |
| `SPEAKER_NOTES.md` | Presentation script |
| `DEMO_PLAYBOOK.md` | Demo walkthrough |

---

## Step-by-Step

### Step 1: Setup AWS CLI
```bash
# macOS
brew install awscli

# Or see AWS_CLI_SETUP.md for Linux/Windows
```

### Step 2: Configure Credentials
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format
```

### Step 3: Create EC2 Key Pair
```bash
aws ec2 create-key-pair --key-name ecl-demo --region us-east-1 --query 'KeyMaterial' --output text > ecl-demo.pem
chmod 600 ecl-demo.pem
```

### Step 4: Clone & Deploy
```bash
# If you haven't already
git clone https://github.com/accionlabs/ecg-demo.git
cd ecg-demo

# Deploy
bash launch-ec2.sh
```

### Step 5: Wait & Access
```
⏳ Wait 25 minutes for:
   - EC2 instance to launch
   - Docker services to start
   - Ollama model to load (llama3:8b)
   - ECL Studio to be ready

✅ Then open: http://your-public-ip:8765
```

---

## What Happens During Deployment

```
[0 min]   CloudFormation stack creation starts
[2 min]   EC2 instance launching
[5 min]   Docker and Docker Compose installing
[10 min]  Repository cloning
[15 min]  Containers starting (FalkorDB, Ollama, ECL, Nginx)
[20 min]  ECL Studio health check passing
[25 min]  Ollama model fully loaded
[25+ min] Ready for use!
```

---

## Access Details After Deployment

```
🌐 Web Interface
   HTTP:  http://your-public-ip
   Port:  http://your-public-ip:8765
   
🔑 SSH Access
   ssh -i ecl-demo.pem ubuntu@your-public-ip
   
💾 Data
   - Traces: /home/ubuntu/ecl/traces/
   - Samples: /home/ubuntu/ecl/sample_documents/
   - Database: FalkorDB (port 6379)
   
📊 Monitoring
   - Health: curl http://your-ip:8765/api/health
   - Stats: ssh... docker stats
   - Logs: ssh... docker-compose logs -f
```

---

## Important Commands

### Monitor Deployment
```bash
STACK_NAME="ecl-demo-xxxx"  # From script output
aws cloudformation describe-stacks --stack-name $STACK_NAME | jq '.Stacks[0].StackStatus'
```

### Get Instance Details
```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=ecl-demo-instance" --query 'Reservations[0].Instances[0]'
```

### SSH and Check Services
```bash
ssh -i ecl-demo.pem ubuntu@your-ip
docker-compose ps          # All services
docker-compose logs -f     # Live logs
docker stats               # Resource usage
curl localhost:8765/api/health  # Health check
```

### Cleanup (Delete Everything)
```bash
STACK_NAME="ecl-demo-xxxx"
aws cloudformation delete-stack --stack-name $STACK_NAME
# Wait ~5 minutes for deletion
```

---

## Cost Estimate

```
EC2 t3.medium:     $30/month
Storage 50GB:      $5/month
Data transfer:     $0-2/month
Elastic IP:        $3.65/month (if unused)
──────────────────────────
TOTAL:             ~$40/month

For 2-week summit: ~$20
For 1 month demo:  ~$40
```

**To avoid costs**: Delete stack when done (`aws cloudformation delete-stack...`)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| AWS CLI not found | See AWS_CLI_SETUP.md |
| "Unable to locate credentials" | Run `aws configure` |
| "Key pair not found" | Create: `aws ec2 create-key-pair --key-name ecl-demo` |
| Services not responding | Wait 25 minutes, check: `aws cloudformation describe-stack-events --stack-name $STACK` |
| "502 Bad Gateway" | SSH in and restart: `docker-compose restart nginx` |
| High costs | Delete stack: `aws cloudformation delete-stack --stack-name $STACK` |

---

## Next Steps

### 1. Run the Demo (5 min)
```
Open http://your-ip:8765
Load sample → Extract → View results
```

### 2. Show to Audience (15 min)
```
Follow SPEAKER_NOTES.md and DEMO_PLAYBOOK.md
Shows extraction, graphs, MCP tools, competitive positioning
```

### 3. Keep Running (2 weeks)
```
Monitor: aws cloudwatch get-metric-statistics...
Backup: ssh... docker-compose exec falkordb redis-cli BGSAVE
```

### 4. Cleanup (5 min)
```
Delete stack to avoid ongoing costs
aws cloudformation delete-stack --stack-name $STACK_NAME
```

---

## All Docs (In Order)

1. **This file** — You are here
2. **AWS_CLI_SETUP.md** — Install AWS CLI
3. **launch-ec2.sh** — Run this to deploy
4. **EC2_DEPLOYMENT.md** — Full reference guide
5. **AWS_QUICK_START.md** — 5-minute guide
6. **DEPLOYMENT_SUMMARY.md** — Overview & checklists
7. **SPEAKER_NOTES.md** — Presentation script
8. **DEMO_PLAYBOOK.md** — Demo walkthrough
9. **MARKET_RESEARCH.md** — Competitive analysis

---

## Final Checklist

- [ ] AWS CLI installed: `aws --version`
- [ ] Credentials configured: `aws sts get-caller-identity`
- [ ] In correct directory: `ls launch-ec2.sh`
- [ ] Ready to deploy: `bash launch-ec2.sh`
- [ ] Following script prompts
- [ ] Waiting for completion (~25 min)
- [ ] Accessing http://your-ip:8765
- [ ] Testing extraction with sample doc
- [ ] Success! 🎉

---

## Support

- **Docs**: Read EC2_DEPLOYMENT.md (comprehensive)
- **Issues**: Check docker-compose logs
- **AWS**: aws cloudformation describe-stack-events --stack-name $STACK
- **Help**: Review AWS_CLI_SETUP.md troubleshooting section

---

**Ready? Run this:**

```bash
bash launch-ec2.sh
```

**Questions? See:**
- AWS_CLI_SETUP.md (setup)
- EC2_DEPLOYMENT.md (detailed reference)
- AWS_QUICK_START.md (5-minute version)

**Let's go! 🚀**
