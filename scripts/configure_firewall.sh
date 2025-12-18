#!/bin/bash
echo "🔥 Configuring UFW Firewall..."
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 5000/tcp comment 'TAK Token Manager'
sudo ufw allow 8089/tcp comment 'TAK Server TLS'
sudo ufw allow 8443/tcp comment 'TAK Server HTTPS'
sudo ufw allow 8446/tcp comment 'Certificate Enrollment'
sudo ufw --force enable
echo "✅ Firewall configured!"
sudo ufw status numbered
