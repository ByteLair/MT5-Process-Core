#!/bin/bash

echo "Fixing Docker permissions and restarting services..."

# Stop Docker service
sudo systemctl stop docker

# Fix permissions
sudo usermod -aG docker $USER
sudo chmod 666 /var/run/docker.sock

# Start Docker service
sudo systemctl start docker

# Wait for Docker to be ready
echo "Waiting for Docker daemon to be ready..."
sleep 5

# Force remove all containers
echo "Removing all existing containers..."
sudo docker rm -f $(sudo docker ps -aq) || true

# Prune all unused Docker resources
echo "Cleaning up Docker system..."
sudo docker system prune -f

# Start services with docker-compose
echo "Starting services with docker-compose..."
docker-compose up -d

# Check status
echo "Checking container status..."
docker ps -a

echo "Done! Check the container status above."
