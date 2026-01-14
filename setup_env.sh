#!/bin/bash

echo "🚀 Creating isolated environment for Code Research Assistant..."
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    VENV_ACTIVATE=".venv/Scripts/activate"
else
    VENV_ACTIVATE=".venv/bin/activate"
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Please install Python 3.11+"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Create virtual environment with UV
echo "📦 Creating virtual environment with UV..."
if command -v uv &> /dev/null; then
    echo "✅ UV found, using UV for environment..."
    uv venv .venv
    source $VENV_ACTIVATE 2>/dev/null || . $VENV_ACTIVATE
    uv pip install -r requirements.txt
else
    echo "⚠️  UV not found, using standard venv..."
    $PYTHON_CMD -m venv .venv
    source $VENV_ACTIVATE 2>/dev/null || . $VENV_ACTIVATE
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "Creating .env template..."
    cat > .env << EOF
# Groq API Key (Required)
GROQ_API_KEY=your_groq_api_key_here

# GCP Configuration (For deployment)
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GCP_SERVICE_NAME=code-research-assistant

# Application Configuration
PORT=8000
HOST=0.0.0.0
EOF
    echo ""
    echo "📝 Please edit .env and add your credentials:"
    echo "   - Groq API key: https://console.groq.com"
    echo "   - GCP Project ID: Your GCP project"
fi

echo ""
echo "✅ Environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Activate environment: source .venv/bin/activate"
echo "2. Edit .env with your API keys"
echo "3. Run locally: python api.py"
echo "4. Deploy to GCP: ./deploy_gcp.sh"
echo ""