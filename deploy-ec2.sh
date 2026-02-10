#!/bin/bash
################################################################################
# ECL Demo - AWS EC2 One-Click Deployment
# Usage: chmod +x deploy-ec2.sh && ./deploy-ec2.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║          🚀 ECL Studio - AWS EC2 Deployment Script             ║"
echo "║                                                                ║"
echo "║   This script will:                                           ║"
echo "║   1. Install Docker & Docker Compose                          ║"
echo "║   2. Clone ECL repository                                     ║"
echo "║   3. Start FalkorDB, Ollama, and ECL Studio                  ║"
echo "║   4. Pre-load Llama 3 8B model                                ║"
echo "║                                                                ║"
echo "║   Estimated time: 15-20 minutes (depends on internet)         ║"
echo "║   Required: Ubuntu 22.04+ with sudo access                    ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Ubuntu/Debian
if ! grep -qi "ubuntu\|debian" /etc/os-release; then
    log_error "This script is designed for Ubuntu/Debian systems"
    exit 1
fi

# Check if running with appropriate permissions
if [[ "$EUID" == 0 ]]; then
    log_error "Please run without sudo. The script will prompt when needed."
    exit 1
fi

# Check internet connectivity
log_info "Checking internet connectivity..."
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    log_error "No internet connection detected"
    exit 1
fi
log_success "Internet connectivity OK"

# Update system
log_info "Updating system packages..."
sudo apt update -qq
sudo apt upgrade -y -qq
log_success "System packages updated"

# Install Docker
log_info "Installing Docker..."
if command -v docker &> /dev/null; then
    log_success "Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh > /dev/null 2>&1
    rm get-docker.sh
    log_success "Docker installed: $(docker --version)"
fi

# Add user to docker group
if id -nG "$USER" | grep -qw docker; then
    log_success "User already in docker group"
else
    log_info "Adding user to docker group..."
    sudo usermod -aG docker "$USER"
    log_warn "You may need to re-login for group changes to take effect"
fi

# Install Docker Compose
log_info "Installing Docker Compose..."
if command -v docker-compose &> /dev/null; then
    log_success "Docker Compose already installed: $(docker-compose --version)"
else
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose > /dev/null 2>&1
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose installed: $(docker-compose --version)"
fi

# Clone repository
log_info "Setting up ECL repository..."
if [ -d "$HOME/ecl" ]; then
    log_warn "ECL directory already exists at $HOME/ecl"
    read -p "Do you want to re-clone? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/ecl"
        git clone https://github.com/accionlabs/ecg-demo.git "$HOME/ecl" > /dev/null 2>&1
        log_success "Repository cloned to $HOME/ecl"
    fi
else
    git clone https://github.com/accionlabs/ecg-demo.git "$HOME/ecl" > /dev/null 2>&1
    log_success "Repository cloned to $HOME/ecl"
fi

cd "$HOME/ecl"

# Check disk space
log_info "Checking disk space..."
AVAILABLE=$(df / | awk 'NR==2 {print $4}')
REQUIRED=$((50 * 1024 * 1024))  # 50GB in KB
if [ "$AVAILABLE" -lt "$REQUIRED" ]; then
    log_error "Insufficient disk space. Need 50GB, have $(numfmt --to=iec $((AVAILABLE * 1024)))"
    exit 1
fi
log_success "Disk space OK: $(numfmt --to=iec $((AVAILABLE * 1024)))"

# Check memory
log_info "Checking available memory..."
MEMORY=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEMORY" -lt 2000 ]; then
    log_warn "Low memory available: ${MEMORY}MB. May impact performance."
fi
log_success "Memory: ${MEMORY}MB available"

# Create SSL directory
mkdir -p "$HOME/ecl/ssl"

# Start services
log_info "Starting Docker services..."
log_info "  • FalkorDB (Graph Database)"
log_info "  • Ollama (LLM Inference Engine)"
log_info "  • ECL Studio (Backend Server)"
log_info "  • Nginx (Reverse Proxy)"
echo ""

docker-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
MAX_RETRIES=60
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8765/api/health > /dev/null 2>&1; then
        log_success "ECL Studio is healthy"
        break
    fi
    echo -n "."
    sleep 1
    ((RETRY++))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    log_error "Services did not become healthy within 60 seconds"
    log_info "Check logs with: docker-compose logs"
    exit 1
fi

# Pre-load Ollama model
log_info "Pre-loading Ollama model (llama3:8b)..."
log_info "This may take 5-10 minutes on first run..."
echo ""

docker exec ecl-ollama ollama pull llama3:8b > /dev/null 2>&1 &
OLLAMA_PID=$!

# Monitor model loading in background
while kill -0 $OLLAMA_PID 2>/dev/null; do
    MODEL_SIZE=$(docker exec ecl-ollama du -sh ~/.ollama/models 2>/dev/null | cut -f1 || echo "0")
    echo -e "\r  Model loading... ${MODEL_SIZE:-0}" | tr -d '\n'
    sleep 2
done

log_success "Ollama model loaded"
echo ""

# Get instance IP
INSTANCE_IP=$(hostname -I | awk '{print $1}')
if [ -z "$INSTANCE_IP" ]; then
    INSTANCE_IP="localhost"
fi

# Final status
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║                  ✅ Deployment Complete!                       ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo -e "${GREEN}📍 Access ECL Studio:${NC}"
echo "   • Direct:  http://$INSTANCE_IP:8765"
echo "   • Nginx:   http://$INSTANCE_IP"
echo ""

echo -e "${GREEN}📊 Service Status:${NC}"
docker-compose ps | tail -n +2 | sed 's/^/   /'
echo ""

echo -e "${GREEN}🔧 Useful Commands:${NC}"
echo "   docker-compose ps             # Check service status"
echo "   docker-compose logs -f        # View logs (Ctrl+C to exit)"
echo "   docker-compose logs -f ecl-studio  # View ECL Studio logs only"
echo "   docker stats                  # Monitor resource usage"
echo "   docker-compose down           # Stop all services"
echo ""

echo -e "${GREEN}📚 Documentation:${NC}"
echo "   • Full guide:  EC2_DEPLOYMENT.md"
echo "   • Demo guide:  DEMO_PLAYBOOK.md"
echo "   • Architecture: MARKET_RESEARCH.md"
echo ""

echo -e "${YELLOW}⚠️  Next Steps:${NC}"
echo "   1. Open browser to http://$INSTANCE_IP:8765"
echo "   2. Wait for model to fully load (check Ollama logs)"
echo "   3. Click 'Load Sample' to test extraction"
echo "   4. Review logs if any issues: docker-compose logs"
echo ""

echo -e "${BLUE}💡 Tip:${NC} If this is a remote EC2 instance, make sure:"
echo "   • Security group allows inbound port 80, 443, 22"
echo "   • You have an Elastic IP assigned (optional but recommended)"
echo "   • DNS is pointing to the instance (for domain setup)"
echo ""

log_success "Deployment script completed successfully!"
