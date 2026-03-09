# Nginx Setup for VM Deployment

## Changes Made
- Removed nginx from Docker Compose
- Updated port bindings to localhost only (127.0.0.1:8000, 127.0.0.1:8001)
- Updated nginx.conf to proxy to localhost instead of Docker service names

## Setup Instructions

### 1. Install Nginx on VM
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

### 2. Create Static/Media Directories
```bash
sudo mkdir -p /var/www/cynosure/staticfiles
sudo mkdir -p /var/www/cynosure/media
```

### 3. Copy Nginx Configuration
```bash
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Collect Static Files
After starting Docker services, run:
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker cp $(docker-compose ps -q web):/app/staticfiles/. /var/www/cynosure/staticfiles/
docker cp $(docker-compose ps -q web):/app/media/. /var/www/cynosure/media/
```

### 5. Update Nginx Static Paths
Edit `/etc/nginx/nginx.conf` and update:
```nginx
location /static/ {
    alias /var/www/cynosure/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

location /media/ {
    alias /var/www/cynosure/media/;
    expires 7d;
    add_header Cache-Control "public";
}
```

### 6. Set Permissions
```bash
sudo chown -R nginx:nginx /var/www/cynosure
sudo chmod -R 755 /var/www/cynosure
```

### 7. Enable and Start Services
```bash
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Verify Setup
- Check nginx status: `sudo systemctl status nginx`
- Test configuration: `sudo nginx -t`
- View logs: `sudo tail -f /var/log/nginx/error.log`
