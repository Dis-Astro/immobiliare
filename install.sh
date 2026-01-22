#!/bin/bash
#===============================================================================
# EstateWise AutoInstaller for Proxmox VE 8.x
# One-shot installation script - creates LXC, installs Docker, deploys app
#
# Usage: bash install.sh
# Requirements: Run from Proxmox host with root privileges
#===============================================================================

set -euo pipefail

#===============================================================================
# CONFIGURATION - Modify these variables as needed
#===============================================================================
CT_ID="${CT_ID:-200}"                          # Container ID
CT_HOSTNAME="${CT_HOSTNAME:-estatewise}"       # Container hostname
CT_PASSWORD="${CT_PASSWORD:-EstateWise2024!}"  # Root password for CT
CT_MEMORY="${CT_MEMORY:-4096}"                 # RAM in MB
CT_SWAP="${CT_SWAP:-512}"                      # Swap in MB
CT_CORES="${CT_CORES:-2}"                      # CPU cores
CT_DISK="${CT_DISK:-20}"                       # Disk size in GB
CT_STORAGE="${CT_STORAGE:-local-lvm}"          # Proxmox storage for CT
CT_BRIDGE="${CT_BRIDGE:-vmbr0}"                # Network bridge
CT_IP="${CT_IP:-dhcp}"                         # IP address (dhcp or static like 192.168.1.100/24)
CT_GATEWAY="${CT_GATEWAY:-}"                   # Gateway (required if static IP)

# GitHub repository
GITHUB_REPO="https://github.com/Dis-Astro/immobiliare.git"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"               # Optional: GitHub token for private repos
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"         # Branch to checkout

# Persistent storage paths on Proxmox host
HOST_DATA_PATH="/srv/estatewise"
HOST_MONGO_PATH="${HOST_DATA_PATH}/mongo"
HOST_UPLOADS_PATH="${HOST_DATA_PATH}/uploads"

# Paths inside container
CT_MONGO_PATH="/data/mongo"
CT_UPLOADS_PATH="/data/uploads"
CT_APP_PATH="/opt/estatewise"

# Template
CT_TEMPLATE="${CT_TEMPLATE:-}"                 # Will be auto-detected if empty

#===============================================================================
# COLORS AND LOGGING
#===============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${GREEN}==> $1${NC}"; }

trap 'log_error "Installation failed at line $LINENO. Exit code: $?"' ERR

#===============================================================================
# HELPER FUNCTIONS
#===============================================================================
check_proxmox() {
    if ! command -v pveversion &> /dev/null; then
        log_error "This script must be run on a Proxmox VE host"
        exit 1
    fi
    log_ok "Running on Proxmox VE $(pveversion --verbose | head -1 | awk '{print $2}')"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

ct_exec() {
    pct exec "$CT_ID" -- bash -c "$1"
}

wait_for_ct() {
    local max_wait=60
    local waited=0
    while ! pct status "$CT_ID" 2>/dev/null | grep -q "running"; do
        sleep 1
        ((waited++))
        if [[ $waited -ge $max_wait ]]; then
            log_error "Container failed to start within ${max_wait}s"
            exit 1
        fi
    done
    sleep 5  # Extra time for network
}

get_ct_ip() {
    local ip=""
    local max_wait=30
    local waited=0
    while [[ -z "$ip" || "$ip" == "127.0.0.1" ]]; do
        ip=$(pct exec "$CT_ID" -- hostname -I 2>/dev/null | awk '{print $1}' || echo "")
        sleep 1
        ((waited++))
        if [[ $waited -ge $max_wait ]]; then
            log_warn "Could not determine container IP automatically"
            ip="<container-ip>"
            break
        fi
    done
    echo "$ip"
}

#===============================================================================
# STEP 1: VALIDATE ENVIRONMENT
#===============================================================================
validate_environment() {
    log_step "Validating environment"
    
    check_root
    check_proxmox
    
    # Check if CT already exists
    if pct status "$CT_ID" &>/dev/null; then
        log_warn "Container $CT_ID already exists"
        read -p "Do you want to destroy and recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Stopping and destroying existing container..."
            pct stop "$CT_ID" 2>/dev/null || true
            sleep 3
            pct destroy "$CT_ID" --purge 2>/dev/null || true
            log_ok "Existing container destroyed"
        else
            log_error "Installation aborted"
            exit 1
        fi
    fi
    
    # Find Ubuntu template
    if [[ -z "$CT_TEMPLATE" ]]; then
        CT_TEMPLATE=$(pveam list local 2>/dev/null | grep -i "ubuntu-22.04" | head -1 | awk '{print $1}' || echo "")
        if [[ -z "$CT_TEMPLATE" ]]; then
            log_info "Ubuntu 22.04 template not found, downloading..."
            pveam update
            pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst || \
            pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.gz
            CT_TEMPLATE=$(pveam list local | grep -i "ubuntu-22.04" | head -1 | awk '{print $1}')
        fi
    fi
    
    if [[ -z "$CT_TEMPLATE" ]]; then
        log_error "Could not find or download Ubuntu 22.04 template"
        exit 1
    fi
    
    log_ok "Using template: $CT_TEMPLATE"
}

#===============================================================================
# STEP 2: CREATE PERSISTENT STORAGE
#===============================================================================
create_storage() {
    log_step "Creating persistent storage on host"
    
    mkdir -p "$HOST_MONGO_PATH"
    mkdir -p "$HOST_UPLOADS_PATH"
    chmod -R 777 "$HOST_DATA_PATH"
    
    log_ok "Created storage directories:"
    log_info "  MongoDB: $HOST_MONGO_PATH"
    log_info "  Uploads: $HOST_UPLOADS_PATH"
}

#===============================================================================
# STEP 3: CREATE LXC CONTAINER
#===============================================================================
create_container() {
    log_step "Creating LXC container (ID: $CT_ID)"
    
    # Build network config
    local net_config="name=eth0,bridge=${CT_BRIDGE}"
    if [[ "$CT_IP" != "dhcp" ]]; then
        net_config="${net_config},ip=${CT_IP}"
        if [[ -n "$CT_GATEWAY" ]]; then
            net_config="${net_config},gw=${CT_GATEWAY}"
        fi
    else
        net_config="${net_config},ip=dhcp"
    fi
    
    # Create container
    pct create "$CT_ID" "$CT_TEMPLATE" \
        --hostname "$CT_HOSTNAME" \
        --password "$CT_PASSWORD" \
        --memory "$CT_MEMORY" \
        --swap "$CT_SWAP" \
        --cores "$CT_CORES" \
        --rootfs "${CT_STORAGE}:${CT_DISK}" \
        --net0 "$net_config" \
        --unprivileged 0 \
        --features nesting=1,keyctl=1 \
        --onboot 1
    
    log_ok "Container created"
}

#===============================================================================
# STEP 4: CONFIGURE LXC FOR DOCKER
#===============================================================================
configure_lxc() {
    log_step "Configuring LXC for Docker compatibility"
    
    local conf_file="/etc/pve/lxc/${CT_ID}.conf"
    
    # Add AppArmor and Docker-specific configurations
    cat >> "$conf_file" << 'EOF'

# Docker compatibility settings
lxc.apparmor.profile: unconfined
lxc.apparmor.allow_nesting: 1
lxc.cap.drop:
lxc.cgroup2.devices.allow: a
lxc.mount.auto: proc:rw sys:rw
EOF
    
    # Add bind mounts for persistent storage
    cat >> "$conf_file" << EOF

# Persistent storage bind mounts
mp0: ${HOST_MONGO_PATH},mp=${CT_MONGO_PATH}
mp1: ${HOST_UPLOADS_PATH},mp=${CT_UPLOADS_PATH}
EOF
    
    log_ok "LXC configuration updated"
    log_info "Config file: $conf_file"
}

#===============================================================================
# STEP 5: START CONTAINER AND INSTALL DEPENDENCIES
#===============================================================================
start_and_setup() {
    log_step "Starting container and installing dependencies"
    
    pct start "$CT_ID"
    wait_for_ct
    log_ok "Container started"
    
    # Wait for network
    log_info "Waiting for network..."
    sleep 10
    
    # Update system
    log_info "Updating system packages..."
    ct_exec "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq"
    
    # Install prerequisites
    log_info "Installing prerequisites..."
    ct_exec "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        jq \
        wget \
        software-properties-common \
        uidmap"
    
    log_ok "Prerequisites installed"
}

#===============================================================================
# STEP 6: INSTALL DOCKER
#===============================================================================
install_docker() {
    log_step "Installing Docker Engine"
    
    # Add Docker GPG key
    ct_exec "install -m 0755 -d /etc/apt/keyrings"
    ct_exec "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
    ct_exec "chmod a+r /etc/apt/keyrings/docker.gpg"
    
    # Add Docker repository
    ct_exec 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list'
    
    # Install Docker
    ct_exec "apt-get update -qq"
    ct_exec "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
    
    # Configure Docker daemon for LXC compatibility
    ct_exec "mkdir -p /etc/docker"
    ct_exec 'cat > /etc/docker/daemon.json << EOF
{
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "default-ulimits": {
        "nofile": {
            "Name": "nofile",
            "Hard": 65536,
            "Soft": 65536
        }
    }
}
EOF'
    
    # Restart Docker
    ct_exec "systemctl daemon-reload"
    ct_exec "systemctl enable docker"
    ct_exec "systemctl restart docker"
    
    # Verify Docker
    sleep 5
    ct_exec "docker --version"
    ct_exec "docker compose version"
    
    log_ok "Docker installed and configured"
}

#===============================================================================
# STEP 7: CLONE REPOSITORY
#===============================================================================
clone_repository() {
    log_step "Cloning EstateWise repository"
    
    # Build clone URL with token if provided
    local clone_url="$GITHUB_REPO"
    if [[ -n "$GITHUB_TOKEN" ]]; then
        clone_url="https://${GITHUB_TOKEN}@github.com/Dis-Astro/immobiliare.git"
    fi
    
    # Clone repository
    ct_exec "rm -rf ${CT_APP_PATH}"
    ct_exec "git clone --branch ${GITHUB_BRANCH} ${clone_url} ${CT_APP_PATH}"
    
    log_ok "Repository cloned to ${CT_APP_PATH}"
}

#===============================================================================
# STEP 8: APPLY PATCHES AND CONFIGURE
#===============================================================================
apply_patches() {
    log_step "Applying patches and configuration"
    
    # Create yarn.lock if missing
    ct_exec "touch ${CT_APP_PATH}/frontend/yarn.lock"
    
    # Create production docker-compose.yml with bind mounts
    ct_exec "cat > ${CT_APP_PATH}/docker-compose.prod.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: estatewise-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_DATABASE: estatewise
    volumes:
      - ${CT_MONGO_PATH}:/data/db
    networks:
      - estatewise-network
    healthcheck:
      test: echo 'db.runCommand(\"ping\").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: estatewise-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - estatewise-network
    healthcheck:
      test: [\"CMD\", \"redis-cli\", \"ping\"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: estatewise-api
    restart: unless-stopped
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=estatewise
      - REDIS_URL=redis://redis:6379/0
      - CORS_ORIGINS=*
      - SMTP_HOST=\${SMTP_HOST:-}
      - SMTP_PORT=\${SMTP_PORT:-587}
      - SMTP_USER=\${SMTP_USER:-}
      - SMTP_PASSWORD=\${SMTP_PASSWORD:-}
      - SMTP_FROM=\${SMTP_FROM:-noreply@estatewise.local}
    volumes:
      - ${CT_UPLOADS_PATH}:/data/uploads
    ports:
      - \"8001:8001\"
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - estatewise-network
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8001/api/v1/health\"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: estatewise-celery-worker
    restart: unless-stopped
    command: celery -A celery_app worker --loglevel=info --concurrency=2
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=estatewise
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ${CT_UPLOADS_PATH}:/data/uploads
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - estatewise-network

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: estatewise-celery-beat
    restart: unless-stopped
    command: celery -A celery_app beat --loglevel=info
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=estatewise
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - estatewise-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - REACT_APP_BACKEND_URL=http://\${HOST_IP:-localhost}:8001
    container_name: estatewise-frontend
    restart: unless-stopped
    ports:
      - \"3000:80\"
    depends_on:
      - api
    networks:
      - estatewise-network

volumes:
  redis_data:

networks:
  estatewise-network:
    driver: bridge
COMPOSE_EOF"

    # Create production Dockerfile for frontend
    ct_exec "cat > ${CT_APP_PATH}/frontend/Dockerfile.prod << 'DOCKERFILE_EOF'
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json ./
RUN touch yarn.lock

# Install dependencies
RUN yarn install --network-timeout 300000

# Copy source code
COPY . .

# Build argument for backend URL
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=\${REACT_APP_BACKEND_URL}

# Build the application
RUN yarn build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files \$uri \$uri/ /index.html; \
    } \
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)\$ { \
        expires 1y; \
        add_header Cache-Control \"public, immutable\"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD [\"nginx\", \"-g\", \"daemon off;\"]
DOCKERFILE_EOF"

    # Create/update backend Dockerfile
    ct_exec "cat > ${CT_APP_PATH}/backend/Dockerfile << 'DOCKERFILE_EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /data/uploads

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Run the application
CMD [\"uvicorn\", \"server:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8001\"]
DOCKERFILE_EOF"

    # Ensure proper permissions
    ct_exec "chmod -R 755 ${CT_APP_PATH}"
    ct_exec "chmod 777 ${CT_MONGO_PATH} ${CT_UPLOADS_PATH}"
    
    log_ok "Patches applied"
}

#===============================================================================
# STEP 9: BUILD AND START STACK
#===============================================================================
deploy_stack() {
    log_step "Building and deploying Docker stack"
    
    local ct_ip=$(get_ct_ip)
    
    # Export HOST_IP for frontend build
    ct_exec "cd ${CT_APP_PATH} && HOST_IP=${ct_ip} docker compose -f docker-compose.prod.yml build --no-cache"
    
    log_info "Starting services..."
    ct_exec "cd ${CT_APP_PATH} && HOST_IP=${ct_ip} docker compose -f docker-compose.prod.yml up -d"
    
    log_ok "Docker stack deployed"
}

#===============================================================================
# STEP 10: WAIT FOR SERVICES
#===============================================================================
wait_for_services() {
    log_step "Waiting for services to be ready"
    
    local max_wait=180
    local waited=0
    
    # Wait for API health
    log_info "Waiting for API to be healthy..."
    while ! ct_exec "curl -sf http://localhost:8001/api/v1/health" &>/dev/null; do
        sleep 5
        ((waited+=5))
        if [[ $waited -ge $max_wait ]]; then
            log_error "API failed to become healthy within ${max_wait}s"
            ct_exec "cd ${CT_APP_PATH} && docker compose -f docker-compose.prod.yml logs api"
            exit 1
        fi
        echo -n "."
    done
    echo ""
    log_ok "API is healthy"
    
    # Wait for frontend
    log_info "Waiting for frontend..."
    waited=0
    while ! ct_exec "curl -sf http://localhost:3000" &>/dev/null; do
        sleep 5
        ((waited+=5))
        if [[ $waited -ge 120 ]]; then
            log_warn "Frontend may still be starting..."
            break
        fi
        echo -n "."
    done
    echo ""
    log_ok "Frontend is accessible"
}

#===============================================================================
# STEP 11: SELF-TEST
#===============================================================================
run_self_tests() {
    log_step "Running self-tests"
    
    local tests_passed=0
    local tests_failed=0
    
    # Test 1: Container running
    if pct status "$CT_ID" | grep -q "running"; then
        log_ok "Test 1/6: Container is running"
        ((tests_passed++))
    else
        log_error "Test 1/6: Container is NOT running"
        ((tests_failed++))
    fi
    
    # Test 2: Docker containers
    local containers=$(ct_exec "docker ps --format '{{.Names}}' | wc -l")
    if [[ "$containers" -ge 5 ]]; then
        log_ok "Test 2/6: All Docker containers running ($containers containers)"
        ((tests_passed++))
    else
        log_error "Test 2/6: Expected 5+ containers, found $containers"
        ct_exec "docker ps -a"
        ((tests_failed++))
    fi
    
    # Test 3: MongoDB
    if ct_exec "docker exec estatewise-mongodb mongosh --eval 'db.runCommand({ping:1})'" &>/dev/null; then
        log_ok "Test 3/6: MongoDB is responsive"
        ((tests_passed++))
    else
        log_error "Test 3/6: MongoDB is NOT responsive"
        ((tests_failed++))
    fi
    
    # Test 4: Redis
    if ct_exec "docker exec estatewise-redis redis-cli ping" | grep -q "PONG"; then
        log_ok "Test 4/6: Redis is responsive"
        ((tests_passed++))
    else
        log_error "Test 4/6: Redis is NOT responsive"
        ((tests_failed++))
    fi
    
    # Test 5: API health
    local health=$(ct_exec "curl -sf http://localhost:8001/api/v1/health" 2>/dev/null || echo "{}")
    if echo "$health" | grep -q "healthy"; then
        log_ok "Test 5/6: API health check passed"
        ((tests_passed++))
    else
        log_error "Test 5/6: API health check FAILED"
        ((tests_failed++))
    fi
    
    # Test 6: Frontend
    if ct_exec "curl -sf http://localhost:3000" | grep -q "EstateWise\|html"; then
        log_ok "Test 6/6: Frontend is serving content"
        ((tests_passed++))
    else
        log_error "Test 6/6: Frontend is NOT serving content"
        ((tests_failed++))
    fi
    
    echo ""
    log_info "Self-test results: $tests_passed passed, $tests_failed failed"
    
    if [[ $tests_failed -gt 0 ]]; then
        return 1
    fi
    return 0
}

#===============================================================================
# STEP 12: PRINT SUMMARY
#===============================================================================
print_summary() {
    local ct_ip=$(get_ct_ip)
    local status="$1"
    
    echo ""
    echo "==============================================================================="
    if [[ "$status" == "SUCCESS" ]]; then
        echo -e "${GREEN}  ███████╗███████╗████████╗ █████╗ ████████╗███████╗${NC}"
        echo -e "${GREEN}  ██╔════╝██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔════╝${NC}"
        echo -e "${GREEN}  █████╗  ███████╗   ██║   ███████║   ██║   █████╗  ${NC}"
        echo -e "${GREEN}  ██╔══╝  ╚════██║   ██║   ██╔══██║   ██║   ██╔══╝  ${NC}"
        echo -e "${GREEN}  ███████╗███████║   ██║   ██║  ██║   ██║   ███████╗${NC}"
        echo -e "${GREEN}  ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚══════╝${NC}"
        echo -e "${GREEN}              WISE - Installation Complete${NC}"
    else
        echo -e "${RED}  INSTALLATION FAILED${NC}"
    fi
    echo "==============================================================================="
    echo ""
    echo -e "  ${BLUE}Container ID:${NC}    $CT_ID"
    echo -e "  ${BLUE}Container IP:${NC}    $ct_ip"
    echo -e "  ${BLUE}Container Name:${NC}  $CT_HOSTNAME"
    echo ""
    echo -e "  ${GREEN}Frontend URL:${NC}    http://${ct_ip}:3000"
    echo -e "  ${GREEN}Backend API:${NC}     http://${ct_ip}:8001/api/v1"
    echo -e "  ${GREEN}API Health:${NC}      http://${ct_ip}:8001/api/v1/health"
    echo ""
    echo -e "  ${YELLOW}Default Login:${NC}"
    echo -e "    Email:    admin@estatewise.it"
    echo -e "    Password: admin123"
    echo ""
    echo -e "  ${BLUE}Management Commands:${NC}"
    echo -e "    Enter container:  pct enter $CT_ID"
    echo -e "    View logs:        pct exec $CT_ID -- docker compose -f /opt/estatewise/docker-compose.prod.yml logs -f"
    echo -e "    Restart stack:    pct exec $CT_ID -- docker compose -f /opt/estatewise/docker-compose.prod.yml restart"
    echo ""
    echo -e "  ${BLUE}Status:${NC}          ${status}"
    echo "==============================================================================="
    echo ""
}

#===============================================================================
# MAIN EXECUTION
#===============================================================================
main() {
    echo ""
    echo "==============================================================================="
    echo "  EstateWise AutoInstaller for Proxmox VE"
    echo "  One-shot installation script"
    echo "==============================================================================="
    echo ""
    
    local start_time=$(date +%s)
    
    # Execute installation steps
    validate_environment
    create_storage
    create_container
    configure_lxc
    start_and_setup
    install_docker
    clone_repository
    apply_patches
    deploy_stack
    wait_for_services
    
    # Run self-tests
    if run_self_tests; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_ok "Installation completed in ${duration} seconds"
        print_summary "SUCCESS"
        exit 0
    else
        print_summary "FAILED"
        exit 1
    fi
}

# Run main
main "$@"
