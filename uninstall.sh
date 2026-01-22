#!/bin/bash
#===============================================================================
# EstateWise Uninstaller for Proxmox VE
# Removes LXC container and optionally persistent data
#
# Usage: bash uninstall.sh
#===============================================================================

set -euo pipefail

#===============================================================================
# CONFIGURATION - Must match install.sh values
#===============================================================================
CT_ID="${CT_ID:-200}"
HOST_DATA_PATH="/srv/estatewise"

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

#===============================================================================
# CHECKS
#===============================================================================
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

if ! command -v pveversion &> /dev/null; then
    log_error "This script must be run on a Proxmox VE host"
    exit 1
fi

#===============================================================================
# MAIN
#===============================================================================
echo ""
echo "==============================================================================="
echo "  EstateWise Uninstaller"
echo "==============================================================================="
echo ""

# Check if container exists
if ! pct status "$CT_ID" &>/dev/null; then
    log_warn "Container $CT_ID does not exist"
else
    log_info "Found container $CT_ID"
    
    # Stop container if running
    if pct status "$CT_ID" | grep -q "running"; then
        log_info "Stopping container..."
        pct stop "$CT_ID"
        sleep 3
    fi
    
    # Destroy container
    log_info "Destroying container..."
    pct destroy "$CT_ID" --purge
    log_ok "Container $CT_ID destroyed"
fi

# Ask about persistent data
echo ""
read -p "Do you want to remove persistent data ($HOST_DATA_PATH)? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -d "$HOST_DATA_PATH" ]]; then
        log_info "Removing persistent data..."
        rm -rf "$HOST_DATA_PATH"
        log_ok "Persistent data removed"
    else
        log_info "Persistent data directory not found"
    fi
else
    log_info "Persistent data preserved at: $HOST_DATA_PATH"
fi

echo ""
echo "==============================================================================="
echo -e "  ${GREEN}EstateWise uninstallation complete${NC}"
echo "==============================================================================="
echo ""
echo "  To reinstall, run: bash install.sh"
echo ""

exit 0
