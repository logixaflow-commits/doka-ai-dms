#!/bin/bash

# Enterprise AI DMS - Setup Script
# This script sets up the environment for development/production

set -e

echo "🔧 Setting up Enterprise AI DMS environment..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

success() {
    log "${GREEN}✓ $1${NC}"
}

error() {
    log "${RED}✗ $1${NC}"
}

warning() {
    log "${YELLOW}⚠ $1${NC}"
}

# Create .env file if it doesn't exist
setup_env() {
    log "Setting up environment variables..."
    
    if [ ! -f "dms/.env" ]; then
        cp dms/.env.example dms/.env
        success "Created .env file"
        warning "Please update dms/.env with your configuration"
    else
        success ".env file already exists"
    fi
    
    if [ ! -f "app/.env.local" ]; then
        cp app/.env.example app/.env.local
        success "Created .env.local file"
        warning "Please update app/.env.local with your configuration"
    else
        success ".env.local file already exists"
    fi
}

# Generate secrets
generate_secrets() {
    log "Generating secrets..."
    
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" dms/.env
        sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" dms/.env
        
        success "Secrets generated"
    else
        warning "Python not found, secrets not generated"
    fi
}

# Create directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p storage/documents
    mkdir -p storage/versions
    mkdir -p storage/workflows
    mkdir -p storage/reports
    mkdir -p storage/quotas
    mkdir -p storage/usage
    mkdir -p storage/rate_limit_rules
    mkdir -p storage/api_usage
    mkdir -p storage/report_templates
    mkdir -p storage/report_schedules
    mkdir -p storage/workflow_instances
    mkdir -p backups
    mkdir -p logs
    
    success "Directories created"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    cd dms
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        python3 -m venv venv
        source venv/bin/activate
    fi
    
    pip install --upgrade pip
    pip install -r requirements-dev.txt
    pip install -r requirements-test.txt
    
    cd ..
    
    success "Python dependencies installed"
}

# Install Node.js dependencies
install_node_deps() {
    log "Installing Node.js dependencies..."
    
    cd app
    npm install
    cd ..
    
    cd mobile
    npm install
    cd ..
    
    success "Node.js dependencies installed"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    cd dms
    source venv/bin/activate
    python -c "from app.core.database import init_database; init_database()" || true
    cd ..
    
    success "Database initialized"
}

# Setup Git
setup_git() {
    log "Setting up Git..."
    
    if [ ! -d ".git" ]; then
        git init
        success "Git repository initialized"
    else
        success "Git repository already exists"
    fi
}

# Create logs directory
setup_logs() {
    log "Setting up logs..."
    
    mkdir -p logs
    touch logs/app.log
    touch logs/error.log
    touch logs/access.log
    
    success "Logs directory created"
}

# Setup permissions
setup_permissions() {
    log "Setting up permissions..."
    
    chmod +x scripts/*.sh
    chmod -R 755 storage
    chmod -R 755 logs
    
    success "Permissions set"
}

# Main setup function
setup() {
    log "Starting setup process..."
    
    setup_env
    generate_secrets
    create_directories
    install_python_deps
    install_node_deps
    init_database
    setup_git
    setup_logs
    setup_permissions
    
    success "Setup completed successfully!"
    log "🎉 Enterprise AI DMS is ready to use!"
    log ""
    log "Next steps:"
    log "1. Update dms/.env with your configuration"
    log "2. Update app/.env.local with your configuration"
    log "3. Run 'docker-compose up -d' to start services"
    log "4. Or run 'cd dms && source venv/bin/activate && uvicorn app.main:app --reload' for development"
}

# Run setup
setup