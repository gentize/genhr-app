#!/bin/bash

# GenHR Deployment Script for Ubuntu
# Run as sudo

echo "Updating system..."
sudo apt update && sudo apt upgrade -y

echo "Installing Python and Nginx..."
sudo apt install python3-pip python3-venv nginx git -y

echo "Creating Project Directory..."
sudo mkdir -p /var/www/GenHR
sudo chown $USER:$USER /var/www/GenHR

echo "Setup Complete. Now upload your files to /var/www/GenHR and run setup_venv.sh"
