# Nginx Setup for VM Deployment

## Setup Instructions

### 1. Install Nginx
```bash
sudo apt update
sudo apt install nginx
```

### 2. Create Static/Media Directories
```bash
sudo mkdir -p /var/www/cynosure-static
sudo mkdir -p /var/www/cynosure-media
```

### 3. Copy Static/Media Files from Docker
```bash
# Start Docker services
docker-compose up -d

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Copy files to VM
sudo docker cp $(docker-compose ps -q web):/app/staticfiles/. /var/www/cynosure-static/
sudo docker cp $(docker-compose ps -q web):/app/media/. /var/www/cynosure-media/

# Set permissions
sudo chown -R www-data:www-data /var/www/cynosure-static
sudo chown -R www-data:www-data /var/www/cynosure-media
```

### 4. Install Nginx Configuration
```bash
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl restart nginx
```

## Verify
```bash
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```
