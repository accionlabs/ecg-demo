#!/bin/bash
################################################################################
# ECL Demo - AWS EC2 Deployment via AWS CLI
# Launches CloudFormation stack and outputs access details
################################################################################

set -e

# Configuration
STACK_NAME="ecl-demo-$(date +%s)"
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.medium}"
KEY_NAME="${KEY_NAME:-}"
ENVIRONMENT_NAME="ecl-demo"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     🚀 ECL Studio - AWS EC2 CloudFormation Deployment          ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Install it first:"
    echo "  https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
log_success "AWS authenticated as: $AWS_USER"

# Get EC2 key pairs
log_info "Fetching available EC2 key pairs..."
KEY_PAIRS=$(aws ec2 describe-key-pairs --region "$REGION" --query 'KeyPairs[].KeyName' --output text)

if [ -z "$KEY_PAIRS" ]; then
    log_error "No EC2 key pairs found in $REGION"
    echo "Create one:"
    echo "  aws ec2 create-key-pair --key-name ecl-demo --region $REGION"
    exit 1
fi

echo "Available key pairs:"
for i in 1; do
    echo "$KEY_PAIRS" | tr ' ' '\n' | nl
done
echo ""

# Prompt for key pair if not set
if [ -z "$KEY_NAME" ]; then
    read -p "Select key pair name (or create new): " KEY_NAME
fi

# Validate key pair exists
if ! echo "$KEY_PAIRS" | grep -q "$KEY_NAME"; then
    log_warn "Key pair '$KEY_NAME' not found. Creating..."
    aws ec2 create-key-pair --key-name "$KEY_NAME" --region "$REGION" --query 'KeyMaterial' --output text > "${KEY_NAME}.pem"
    chmod 600 "${KEY_NAME}.pem"
    log_success "Key pair created: ${KEY_NAME}.pem"
fi

# Confirm parameters
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Deployment Parameters                       ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║ Stack Name:         $STACK_NAME"
echo "║ Region:             $REGION"
echo "║ Instance Type:      $INSTANCE_TYPE"
echo "║ Key Pair:           $KEY_NAME"
echo "║ Environment:        $ENVIRONMENT_NAME"
echo "║                                                                ║"
echo "║ Estimated Cost:     ~\$40/month ($30 EC2 + \$10 storage)       ║"
echo "║ Deployment Time:    ~25 minutes                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "Deployment cancelled"
    exit 0
fi

echo ""
log_info "Creating CloudFormation stack..."
log_info "Stack name: $STACK_NAME"
echo ""

# Create stack
aws cloudformation create-stack \
    --stack-name "$STACK_NAME" \
    --template-body file://ecl-cloudformation.yaml \
    --region "$REGION" \
    --parameters \
        ParameterKey=KeyName,ParameterValue="$KEY_NAME" \
        ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
        ParameterKey=EnvironmentName,ParameterValue="$ENVIRONMENT_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags Key=Project,Value=ECL Key=Environment,Value=Demo \
    --output json > /dev/null

log_success "CloudFormation stack created"
echo ""

# Wait for stack creation
log_info "Waiting for stack creation to complete..."
log_info "This may take 5-10 minutes. Checking status..."
echo ""

STACK_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackId' --output text)

while true; do
    STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text)
    
    case "$STATUS" in
        CREATE_COMPLETE)
            log_success "Stack creation complete!"
            break
            ;;
        CREATE_IN_PROGRESS)
            echo -n "."
            sleep 10
            ;;
        CREATE_FAILED)
            log_error "Stack creation failed!"
            aws cloudformation describe-stack-events --stack-name "$STACK_NAME" --region "$REGION" --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]' --output table
            exit 1
            ;;
        *)
            log_error "Unexpected status: $STATUS"
            exit 1
            ;;
    esac
done

echo ""

# Get stack outputs
log_info "Retrieving stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs' --output json)

INSTANCE_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="InstanceID") | .OutputValue')
PUBLIC_IP=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="PublicIP") | .OutputValue')
HTTP_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="HTTPURL") | .OutputValue')
SSH_COMMAND=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="SSHCommand") | .OutputValue')

# Wait for instance to be running and services to start
log_info "Waiting for EC2 instance to fully initialize..."
log_info "Services starting (FalkorDB, Ollama, ECL Studio)..."
log_info "Model loading (llama3:8b) - may take 10 minutes..."
echo ""

# Poll instance status
MAX_RETRIES=60
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s "http://${PUBLIC_IP}:8765/api/health" > /dev/null 2>&1; then
        log_success "ECL Studio is responding!"
        break
    fi
    echo -n "."
    sleep 5
    ((RETRY++))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    log_warn "Services not responding yet (might still be loading)"
    log_info "Check instance status:"
    echo "  aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION"
    log_info "Check services:"
    echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
    echo "  docker-compose ps"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║             ✅ Deployment Complete!                            ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo -e "${GREEN}📍 Access ECL Studio:${NC}"
echo "   HTTP:  $HTTP_URL"
echo "   Port:  http://${PUBLIC_IP}:8765"
echo ""

echo -e "${GREEN}🔑 SSH Access:${NC}"
echo "   $SSH_COMMAND"
echo ""

echo -e "${GREEN}📊 Stack Information:${NC}"
echo "   Stack Name:    $STACK_NAME"
echo "   Stack ID:      $STACK_ID"
echo "   Instance ID:   $INSTANCE_ID"
echo "   Public IP:     $PUBLIC_IP"
echo "   Region:        $REGION"
echo ""

echo -e "${GREEN}🔧 AWS CLI Commands:${NC}"
echo "   # View stack status"
echo "   aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION"
echo ""
echo "   # View instance details"
echo "   aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION"
echo ""
echo "   # View logs"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} docker-compose logs -f"
echo ""
echo "   # Monitor resources"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} docker stats"
echo ""
echo "   # Delete stack (cleanup)"
echo "   aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
echo ""

echo -e "${YELLOW}⏳ Next Steps:${NC}"
echo "   1. Wait 5-10 minutes for Ollama model to fully load"
echo "   2. Open http://${PUBLIC_IP}:8765 in your browser"
echo "   3. Click 'Load Sample' to test extraction"
echo "   4. Monitor logs: docker-compose logs -f"
echo ""

echo -e "${BLUE}💡 Tips:${NC}"
echo "   - Keep $KEY_NAME.pem safe (don't commit to git)"
echo "   - To stop costs: aws cloudformation delete-stack --stack-name $STACK_NAME"
echo "   - Monitor costs: aws ce get-cost-and-usage (via AWS Console)"
echo "   - Set budget alert: aws budgets create-budget (via AWS Console)"
echo ""

log_success "Deployment script completed successfully!"
log_info "Check back in 10 minutes - model loading takes time"
