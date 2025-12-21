#!/bin/bash
# =============================================================================
# EC2 User Data Script - Flask Backend with Gunicorn
# =============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=========================================="
echo "Starting Flask Backend Setup"
echo "=========================================="

# Update system
echo "Updating system packages..."
dnf update -y

# Install Python and dependencies
echo "Installing Python and dependencies..."
dnf install -y python3.11 python3.11-pip python3.11-devel gcc postgresql15-devel git nginx

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/cyberrisk
cd /opt/cyberrisk

# Create virtual environment
echo "Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install flask flask-cors gunicorn boto3 psycopg2-binary pandas numpy prophet yfinance requests beautifulsoup4 PyPDF2 python-dotenv

# Create environment file
echo "Creating environment configuration..."
cat > /opt/cyberrisk/.env << 'ENVEOF'
# Database Configuration
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_username}
DB_PASSWORD=${db_password}
DB_PORT=5432

# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
ARTIFACTS_BUCKET=${artifacts_bucket}

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0
ENVEOF

# Create a simple Flask app placeholder (will be replaced with actual code)
echo "Creating Flask application..."
cat > /opt/cyberrisk/app.py << 'APPEOF'
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv('/opt/cyberrisk/.env')

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'CyberRisk API is running'})

@app.route('/api/companies', methods=['GET'])
def get_companies():
    # This will be replaced with actual database query
    return jsonify([])

@app.route('/api/artifacts', methods=['GET'])
def get_artifacts():
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
APPEOF

# Create Gunicorn service
echo "Creating Gunicorn systemd service..."
cat > /etc/systemd/system/gunicorn.service << 'SERVICEEOF'
[Unit]
Description=Gunicorn instance for CyberRisk Flask app
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/opt/cyberrisk
Environment="PATH=/opt/cyberrisk/venv/bin"
EnvironmentFile=/opt/cyberrisk/.env
ExecStart=/opt/cyberrisk/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app --timeout 120 --access-logfile /var/log/gunicorn/access.log --error-logfile /var/log/gunicorn/error.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Create log directory
mkdir -p /var/log/gunicorn
chown -R ec2-user:ec2-user /var/log/gunicorn

# Set permissions
chown -R ec2-user:ec2-user /opt/cyberrisk

# Configure nginx as reverse proxy
echo "Configuring nginx..."
cat > /etc/nginx/conf.d/cyberrisk.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }

    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
}
NGINXEOF

# Remove default nginx config
rm -f /etc/nginx/conf.d/default.conf

# Enable and start services
echo "Enabling and starting services..."
systemctl daemon-reload
systemctl enable gunicorn
systemctl enable nginx
systemctl start gunicorn
systemctl start nginx

echo "=========================================="
echo "Flask Backend Setup Complete!"
echo "API available at http://localhost:5000"
echo "=========================================="
