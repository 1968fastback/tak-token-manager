#!/bin/bash

echo "════════════════════════════════════════════════════════════"
echo "  TAK Token Manager - Setup Script"
echo "════════════════════════════════════════════════════════════"
echo ""

# Create .env if doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your_random_secret_key_here/$SECRET_KEY/" .env
    
    echo "✅ .env created"
    echo "⚠️  Please edit .env and configure:"
    echo "   - Email settings (SMTP_USER, SMTP_PASSWORD)"
    echo "   - TAK Admin credentials (if using API)"
else
    echo "✅ .env file exists"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p config logs data packages
echo "✅ Directories created"

# Copy truststore
TRUSTSTORE_PATH="$HOME/tak-stack/tak/certs/files/truststore-root.p12"
if [ -f "$TRUSTSTORE_PATH" ]; then
    echo "📜 Copying truststore..."
    cp "$TRUSTSTORE_PATH" config/
    echo "✅ Truststore copied"
else
    echo "⚠️  Truststore not found at: $TRUSTSTORE_PATH"
    echo "   Please manually copy truststore-root.p12 to config/"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit .env: nano .env"
echo "  2. Configure firewall: sudo bash scripts/configure_firewall.sh"
echo "  3. Start: docker compose up -d"
echo "  4. View logs: docker compose logs -f"
echo ""
