# 🔧 AWS CLI Setup & EC2 Deployment

## Step 1: Install AWS CLI

### macOS
```bash
# Using Homebrew (recommended)
brew install awscli

# Or download directly
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Verify
aws --version
```

### Linux/Ubuntu
```bash
curl "https://awscli.amazonaws.com/awscliv2.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### Windows (PowerShell)
```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

---

## Step 2: Configure AWS Credentials

### Get AWS Access Keys
1. Go to **AWS Console** → **IAM** → **Users** → **Your User** → **Security Credentials**
2. Click "Create access key"
3. Save the Access Key ID and Secret Access Key

### Configure AWS CLI
```bash
aws configure

# You'll be prompted for:
# AWS Access Key ID: [paste from above]
# AWS Secret Access Key: [paste from above]
# Default region: us-east-1 (or your preferred region)
# Default output format: json
```

Or use environment variables:
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### Verify Configuration
```bash
aws sts get-caller-identity
# Should output your AWS account info
```

---

## Step 3: Create EC2 Key Pair (if not exists)

```bash
# Create key pair
aws ec2 create-key-pair --key-name ecl-demo --region us-east-1 --query 'KeyMaterial' --output text > ecl-demo.pem

# Set proper permissions
chmod 600 ecl-demo.pem

# Verify
aws ec2 describe-key-pairs --key-names ecl-demo --region us-east-1
```

Or via AWS Console:
1. **EC2 Dashboard** → **Key Pairs** → **Create key pair**
2. Name: `ecl-demo`
3. Type: RSA
4. Download `.pem` file
5. Save to safe location

---

## Step 4: Deploy to EC2

### Option A: Using Launch Script (Recommended)

```bash
# Make sure you're in the ecl-demo directory
cd /path/to/ecg-demo

# Run deployment script
bash launch-ec2.sh

# Follow prompts:
# - Select EC2 key pair (ecl-demo)
# - Confirm parameters
# - Wait for deployment to complete (~25 minutes)
```

**Output:**
```
✅ Deployment Complete!

📍 Access ECL Studio:
   HTTP: http://54.123.45.67
   Port: http://54.123.45.67:8765

🔑 SSH Access:
   ssh -i ecl-demo.pem ubuntu@54.123.45.67

...
```

### Option B: Using AWS CLI Directly

```bash
# Set variables
STACK_NAME="ecl-demo-$(date +%s)"
KEY_NAME="ecl-demo"
REGION="us-east-1"
INSTANCE_TYPE="t3.medium"

# Create stack
aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://ecl-cloudformation.yaml \
  --region "$REGION" \
  --parameters \
    ParameterKey=KeyName,ParameterValue="$KEY_NAME" \
    ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

# Get outputs
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs'
```

### Option C: Via AWS Console (GUI)

1. Go to **CloudFormation** → **Create Stack**
2. Upload template file: `ecl-cloudformation.yaml`
3. Fill in parameters:
   - Key Name: `ecl-demo`
   - Instance Type: `t3.medium`
   - Environment Name: `ecl-demo`
4. Click "Create Stack"
5. Wait for **CREATE_COMPLETE** status
6. Check **Outputs** tab for access URLs

---

## Useful AWS CLI Commands

### View Deployment Status
```bash
# List all stacks
aws cloudformation list-stacks --region us-east-1

# Get stack details
STACK_NAME="ecl-demo-xxxx"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'

# Get stack events (useful for debugging)
aws cloudformation describe-stack-events \
  --stack-name "$STACK_NAME" \
  --region us-east-1
```

### Manage Instances
```bash
# List instances
aws ec2 describe-instances --region us-east-1 --filters "Name=tag:Project,Values=ECL"

# Get instance status
INSTANCE_ID="i-xxxxx"
aws ec2 describe-instance-status --instance-ids "$INSTANCE_ID" --region us-east-1

# Reboot instance
aws ec2 reboot-instances --instance-ids "$INSTANCE_ID" --region us-east-1

# Stop instance
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region us-east-1

# Start instance
aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region us-east-1

# Terminate instance
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region us-east-1
```

### SSH Access
```bash
# Get public IP
INSTANCE_ID="i-xxxxx"
IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

# SSH into instance
ssh -i ecl-demo.pem ubuntu@$IP

# Copy files from instance
scp -i ecl-demo.pem ubuntu@$IP:/home/ubuntu/ecl/traces/* ./local-backup/

# Copy files to instance
scp -i ecl-demo.pem ./my-config.sh ubuntu@$IP:/home/ubuntu/
```

### Monitoring & Logs
```bash
# Get CloudWatch logs
aws logs get-log-events \
  --log-group-name /aws/ec2/ecl-demo \
  --log-stream-name instance \
  --region us-east-1

# Get container logs via SSH
ssh -i ecl-demo.pem ubuntu@$IP docker-compose logs -f ecl-studio

# Monitor resources
ssh -i ecl-demo.pem ubuntu@$IP docker stats
```

### Cost Management
```bash
# Get estimated cost of stack
aws cloudformation get-template-summary \
  --template-body file://ecl-cloudformation.yaml

# List EC2 instances by cost
aws ec2 describe-instances \
  --region us-east-1 \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name]' \
  --output table

# Check EC2 pricing (approximate)
echo "t3.small:  \$15/month"
echo "t3.medium: \$30/month"
echo "t3.large:  \$60/month"
echo "Storage (50GB gp3): \$5/month"
```

### Cleanup
```bash
# Delete stack (all resources)
STACK_NAME="ecl-demo-xxxx"
aws cloudformation delete-stack \
  --stack-name "$STACK_NAME" \
  --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name "$STACK_NAME" \
  --region us-east-1

# Verify deletion
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1
# Should error: "Stack with id {STACK_NAME} does not exist"

# Delete key pair (optional)
aws ec2 delete-key-pair --key-name ecl-demo --region us-east-1
```

---

## Troubleshooting

### "AWS CLI not found"
```bash
# Install AWS CLI
brew install awscli  # macOS
# OR
curl "https://awscli.amazonaws.com/awscliv2.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install  # Linux
```

### "Unable to locate credentials"
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

### "The specified key pair does not exist"
```bash
# Create key pair
aws ec2 create-key-pair --key-name ecl-demo --region us-east-1 --query 'KeyMaterial' --output text > ecl-demo.pem
chmod 600 ecl-demo.pem
```

### "Template error" in CloudFormation
```bash
# Validate template
aws cloudformation validate-template --template-body file://ecl-cloudformation.yaml

# Check template syntax
cat ecl-cloudformation.yaml | head -20
```

### Stack creation failed
```bash
# Check events
aws cloudformation describe-stack-events \
  --stack-name "$STACK_NAME" \
  --region us-east-1 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# Delete failed stack and retry
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region us-east-1
```

---

## Security Best Practices

1. **Never commit credentials**
   ```bash
   # Add to .gitignore
   echo "*.pem" >> .gitignore
   echo ".aws/" >> .gitignore
   ```

2. **Use IAM roles instead of access keys** (for EC2 instances)
   ```bash
   # The CloudFormation template already creates an IAM role
   aws iam list-instance-profiles
   ```

3. **Rotate access keys regularly**
   ```bash
   # Delete old key
   aws iam delete-access-key --access-key-id "AKIA..."
   
   # Create new one
   aws iam create-access-key
   ```

4. **Use MFA** for AWS account
   ```bash
   # Enable MFA in AWS Console
   # IAM → Users → Your User → Security Credentials → MFA devices
   ```

5. **Restrict security group**
   ```bash
   # Change 0.0.0.0/0 to your IP
   aws ec2 authorize-security-group-ingress \
     --group-id sg-xxxxx \
     --protocol tcp \
     --port 22 \
     --cidr YOUR.IP.ADDRESS/32
   ```

---

## Next Steps After Deployment

1. **SSH into instance**
   ```bash
   ssh -i ecl-demo.pem ubuntu@your-public-ip
   ```

2. **Check services**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

3. **Access the demo**
   ```
   http://your-public-ip:8765
   ```

4. **Monitor costs**
   ```bash
   # AWS Console → Billing → Cost Explorer
   # Or set budget alert
   ```

5. **Cleanup when done**
   ```bash
   aws cloudformation delete-stack --stack-name ecl-demo-xxxx
   ```

---

## Cost Calculator

| Component | t3.small | t3.medium | t3.large |
|-----------|----------|-----------|----------|
| Compute | $15 | $30 | $60 |
| Storage (50GB) | $5 | $5 | $5 |
| **Total/month** | **$20** | **$35** | **$65** |
| **Total/hour** | **$0.027** | **$0.048** | **$0.089** |

**Estimate for summit demo**: 2-3 weeks = $140-210

---

## Support

- **AWS Documentation**: https://docs.aws.amazon.com/cli/
- **CloudFormation Docs**: https://docs.aws.amazon.com/cloudformation/
- **EC2 Docs**: https://docs.aws.amazon.com/ec2/
- **Pricing**: https://aws.amazon.com/ec2/pricing/

Ready to deploy! 🚀
