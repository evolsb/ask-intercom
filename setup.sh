#!/bin/bash
# Setup script for Ask-Intercom development environment

set -e  # Exit on any error

echo "🚀 Setting up Ask-Intercom development environment..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "📦 Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add to current session PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    echo "✅ Poetry installed to ~/.local/bin/poetry"
    echo "⚠️  You may need to restart your terminal or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Check Poetry path
POETRY_PATH=""
if command -v poetry &> /dev/null; then
    POETRY_PATH=$(which poetry)
elif [ -f "$HOME/.local/bin/poetry" ]; then
    POETRY_PATH="$HOME/.local/bin/poetry"
else
    echo "❌ Poetry installation failed or not found in PATH"
    exit 1
fi

echo "📦 Using Poetry at: $POETRY_PATH"

# Install dependencies
echo "📦 Installing Python dependencies..."
"$POETRY_PATH" install

# Check for .env file
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file from template..."
    cat > .env << 'EOF'
# Required API credentials
INTERCOM_ACCESS_TOKEN=your_intercom_token_here
OPENAI_API_KEY=your_openai_key_here

# Optional settings
# INTERCOM_APP_ID=your_intercom_app_id_here  # Auto-detected if not provided
OPENAI_MODEL=gpt-4
MAX_CONVERSATIONS=50
DEBUG=false
EOF
    echo "⚠️  Please edit .env file with your actual API credentials"
else
    echo "✅ .env file already exists"
fi

# Update test script to use correct Poetry path
echo "🔧 Updating test script with correct Poetry path..."
cat > test << EOF
#!/bin/bash
# Simple entry point for interactive testing
"$POETRY_PATH" run ask-intercom-interactive "\$@"
EOF

chmod +x test

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API credentials"
echo "2. Run: ./test"
echo "3. Or run directly: $POETRY_PATH run python -m src.cli \"your query\""
