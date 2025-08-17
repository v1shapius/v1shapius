#!/bin/bash

# Discord Rating Bot Deployment Script
# This script provides quick deployment options for the bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create environment file
create_env_file() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your Discord Bot Token and other settings"
        print_warning "You can find your Discord Bot Token at: https://discord.com/developers/applications"
    else
        print_status ".env file already exists"
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p config
    mkdir -p backups
    mkdir -p database/backups
    mkdir -p redis
    mkdir -p nginx/ssl
    mkdir -p monitoring/grafana/provisioning
    
    print_success "Directories created"
}

# Function to create basic configuration files
create_config_files() {
    print_status "Creating basic configuration files..."
    
    # Create Redis config
    if [ ! -f redis/redis.conf ]; then
        cat > redis/redis.conf << EOF
# Redis configuration for Discord Bot
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
EOF
    fi
    
    # Create basic Nginx config
    if [ ! -f nginx/nginx.conf ]; then
        cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream bot_backend {
        server bot:8000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location / {
            proxy_pass http://bot_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
    fi
    
    print_success "Configuration files created"
}

# Function to deploy development environment
deploy_dev() {
    print_status "Deploying development environment..."
    
    check_prerequisites
    create_env_file
    create_directories
    create_config_files
    
    print_status "Starting development services..."
    docker-compose up -d postgres redis
    
    print_status "Waiting for database to be ready..."
    sleep 10
    
    print_status "Starting bot..."
    docker-compose up -d bot
    
    print_success "Development environment deployed successfully!"
    print_status "You can view logs with: docker-compose logs -f bot"
    print_status "Stop services with: docker-compose down"
}

# Function to deploy production environment
deploy_prod() {
    print_status "Deploying production environment..."
    
    check_prerequisites
    create_env_file
    create_directories
    create_config_files
    
    print_status "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "Production environment deployed successfully!"
    print_status "You can view logs with: docker-compose -f docker-compose.prod.yml logs -f"
    print_status "Stop services with: docker-compose -f docker-compose.prod.yml down"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps -q | grep -q .; then
        docker-compose -f docker-compose.prod.yml down
        print_success "Production services stopped"
    elif docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "Development services stopped"
    else
        print_warning "No running services found"
    fi
}

# Function to view logs
view_logs() {
    print_status "Viewing logs..."
    
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps -q | grep -q .; then
        docker-compose -f docker-compose.prod.yml logs -f
    elif docker-compose ps -q | grep -q .; then
        docker-compose logs -f
    else
        print_warning "No running services found"
    fi
}

# Function to backup database
backup_database() {
    print_status "Creating database backup..."
    
    if [ ! -d backups ]; then
        mkdir -p backups
    fi
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="backups/discord_bot_backup_${timestamp}.sql"
    
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps -q postgres | grep -q .; then
        docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U bot_user discord_bot > "$backup_file"
    elif docker-compose ps -q postgres | grep -q .; then
        docker-compose exec -T postgres pg_dump -U bot_user discord_bot > "$backup_file"
    else
        print_error "PostgreSQL service not running"
        exit 1
    fi
    
    print_success "Database backup created: $backup_file"
}

# Function to restore database
restore_database() {
    if [ -z "$1" ]; then
        print_error "Please specify backup file to restore"
        print_status "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_status "Restoring database from backup: $backup_file"
    
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps -q postgres | grep -q .; then
        docker-compose -f docker-compose.prod.yml exec -T postgres psql -U bot_user -d discord_bot < "$backup_file"
    elif docker-compose ps -q postgres | grep -q .; then
        docker-compose exec -T postgres psql -U bot_user -d discord_bot < "$backup_file"
    else
        print_error "PostgreSQL service not running"
        exit 1
    fi
    
    print_success "Database restored successfully"
}

# Function to show status
show_status() {
    print_status "Service status:"
    
    if [ -f docker-compose.prod.yml ] && docker-compose -f docker-compose.prod.yml ps -q | grep -q .; then
        docker-compose -f docker-compose.prod.yml ps
    elif docker-compose ps -q | grep -q .; then
        docker-compose ps
    else
        print_warning "No running services found"
    fi
}

# Function to show help
show_help() {
    echo "Discord Rating Bot Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev         Deploy development environment"
    echo "  prod        Deploy production environment"
    echo "  stop        Stop all services"
    echo "  logs        View logs"
    echo "  backup      Create database backup"
    echo "  restore     Restore database from backup"
    echo "  status      Show service status"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev      # Deploy development environment"
    echo "  $0 prod     # Deploy production environment"
    echo "  $0 backup   # Create database backup"
    echo "  $0 restore backups/discord_bot_backup_20231201_120000.sql"
}

# Main script logic
case "${1:-help}" in
    dev)
        deploy_dev
        ;;
    prod)
        deploy_prod
        ;;
    stop)
        stop_services
        ;;
    logs)
        view_logs
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac