#!/bin/bash

echo "Setting up Flight Planning LLM Web Application..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads static

# Create .env file template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat > .env << EOL
# OpenAI API Key (required for GPT models)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (required for Claude models)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Flask configuration
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
EOL
    echo "Please edit .env file and add your API keys"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file and add your API keys"
echo "2. Run the application with: python run.py"
echo "3. For local access: http://localhost:5000"
echo "4. For SSH access: http://your-server-ip:5000" 