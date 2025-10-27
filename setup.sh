#!/bin/bash

# Azure DevOps PR Review Agent Setup Script

echo "========================================="
echo "Azure DevOps PR Review Agent Setup"
echo "========================================="
echo ""

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Check if pip is installed
echo "Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    python3 -m ensurepip --upgrade
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Create config file if it doesn't exist
echo ""
if [ ! -f "config.env" ]; then
    echo "Creating config.env from example..."
    cp config.env.example config.env
    echo "✅ config.env created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit config.env and add your credentials:"
    echo "   - AZURE_DEVOPS_ORG_URL"
    echo "   - AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN"
    echo "   - AZURE_DEVOPS_PROJECT"
    echo "   - OPENAI_API_KEY"
    echo ""
else
    echo "✅ config.env already exists"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit config.env with your credentials"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the agent: python main.py"
echo ""
echo "Or use Docker:"
echo "1. Edit config.env"
echo "2. Run: docker-compose up -d"
echo ""

