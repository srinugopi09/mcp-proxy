# Deployment Guide

## Overview

This guide covers deploying the MCP Registry in production environments.

## Prerequisites

- Python 3.10+
- UV package manager
- Database (SQLite for simple deployments, PostgreSQL for production)
- Reverse proxy (nginx, Apache, or cloud load balancer)

## Production Setup

### 1. Environment Preparation

```bash
# Create production user
sudo useradd -m -s /bin/bash mcp-registry

# Switch to production user
sudo su - mcp-registry

# Clone repository
git clone <repository-url>
cd mcp-registry
```

### 2. Install Dependencies

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync --no-dev
```

### 3. Configuration

Create production configuration:

```bash
# Create environment file
cat > .env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/mcp_registry

# API Server
HOST=127.0.0.1
PORT=8000
DEBUG=false
RELOAD=false

# Security
SECRET_KEY=$(openssl rand -hex 32)

# CORS (adjust for your domains)
CORS_ORIGINS=["https://yourdomain.com"]

# Logging
LOG_LEVEL=INFO
EOF
```

### 4. Database Setup

#### PostgreSQL (Recommended)
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE mcp_registry;
CREATE USER mcp_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_registry TO mcp_user;
EOF

# Install PostgreSQL adapter
uv add asyncpg
```

#### SQLite (Simple deployments)
```bash
# Initialize database
uv run mcp-registry db init
```

### 5. Run Migrations

```bash
uv run alembic upgrade head
```

## Deployment Options

### Option 1: Systemd Service

Create systemd service file:

```bash
sudo tee /etc/systemd/system/mcp-registry.service << EOF
[Unit]
Description=MCP Registry API Server
After=network.target

[Service]
Type=exec
User=mcp-registry
Group=mcp-registry
WorkingDirectory=/home/mcp-registry/mcp-registry
Environment=PATH=/home/mcp-registry/mcp-registry/.venv/bin
ExecStart=/home/mcp-registry/mcp-registry/.venv/bin/mcp-registry start --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable mcp-registry
sudo systemctl start mcp-registry
sudo systemctl status mcp-registry
```

### Option 2: Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "mcp-registry", "start", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mcp-registry:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/mcp_registry
      - DEBUG=false
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=mcp_registry
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

Deploy with Docker:

```bash
# Build and start
docker-compose up -d

# Initialize database
docker-compose exec mcp-registry uv run mcp-registry db init

# View logs
docker-compose logs -f mcp-registry
```

### Option 3: Cloud Deployment

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Heroku
```bash
# Create Procfile
echo "web: uv run mcp-registry start --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
git push heroku main
```

#### DigitalOcean App Platform
Create `app.yaml`:

```yaml
name: mcp-registry
services:
- name: api
  source_dir: /
  github:
    repo: your-username/mcp-registry
    branch: main
  run_command: uv run mcp-registry start --host 0.0.0.0 --port 8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
  env:
  - key: DEBUG
    value: "false"
databases:
- name: mcp-registry-db
  engine: PG
  version: "15"
```

## Reverse Proxy Setup

### Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Apache

```apache
<VirtualHost *:80>
    ServerName yourdomain.com
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```

## SSL/TLS Setup

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Logging

### Application Logs

```bash
# View systemd logs
sudo journalctl -u mcp-registry -f

# View Docker logs
docker-compose logs -f mcp-registry
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health/

# Readiness check
curl http://localhost:8000/health/ready
```

### Monitoring Setup

Create monitoring script:

```bash
#!/bin/bash
# health-check.sh

ENDPOINT="http://localhost:8000/health/"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT)

if [ $RESPONSE -eq 200 ]; then
    echo "Service is healthy"
    exit 0
else
    echo "Service is unhealthy (HTTP $RESPONSE)"
    exit 1
fi
```

Add to crontab:

```bash
# Check every 5 minutes
*/5 * * * * /path/to/health-check.sh
```

## Performance Tuning

### Database Optimization

```python
# In production settings
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?pool_size=20&max_overflow=0"
```

### Application Scaling

```bash
# Run multiple workers
uv run mcp-registry start --host 0.0.0.0 --port 8000 --workers 4
```

### Caching

Consider adding Redis for caching:

```bash
# Install Redis
sudo apt-get install redis-server

# Add to requirements
uv add redis[hiredis]
```

## Security Hardening

### Firewall Setup

```bash
# UFW firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Application Security

```bash
# Set secure environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export DEBUG=false
export CORS_ORIGINS='["https://yourdomain.com"]'
```

### Database Security

```bash
# PostgreSQL security
sudo -u postgres psql << EOF
ALTER USER mcp_user WITH PASSWORD 'new_secure_password';
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO mcp_user;
EOF
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="mcp_registry"

# PostgreSQL backup
pg_dump -h localhost -U mcp_user $DB_NAME > $BACKUP_DIR/mcp_registry_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/mcp_registry_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "mcp_registry_*.sql.gz" -mtime +7 -delete
```

### Application Backup

```bash
# Backup application files
tar -czf /backups/mcp-registry-app-$(date +%Y%m%d).tar.gz /home/mcp-registry/mcp-registry
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo systemctl status mcp-registry
   sudo journalctl -u mcp-registry -n 50
   ```

2. **Database connection errors**
   ```bash
   uv run mcp-registry db status
   ```

3. **Permission issues**
   ```bash
   sudo chown -R mcp-registry:mcp-registry /home/mcp-registry/mcp-registry
   ```

4. **Port conflicts**
   ```bash
   sudo netstat -tlnp | grep :8000
   ```

### Performance Issues

1. **High memory usage**
   - Reduce database pool size
   - Check for memory leaks
   - Monitor with `htop` or `ps`

2. **Slow responses**
   - Check database query performance
   - Add database indexes
   - Enable query logging

3. **High CPU usage**
   - Profile application code
   - Check for infinite loops
   - Monitor with `top` or `htop`

## Maintenance

### Regular Tasks

1. **Update dependencies**
   ```bash
   uv sync --upgrade
   ```

2. **Database maintenance**
   ```bash
   # PostgreSQL
   sudo -u postgres psql -c "VACUUM ANALYZE;" mcp_registry
   ```

3. **Log rotation**
   ```bash
   sudo logrotate /etc/logrotate.d/mcp-registry
   ```

4. **Security updates**
   ```bash
   sudo apt-get update && sudo apt-get upgrade
   ```

### Scaling Considerations

- Use load balancers for multiple instances
- Consider database read replicas
- Implement caching strategies
- Monitor resource usage and scale accordingly