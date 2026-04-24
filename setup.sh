#!/bin/bash

# PokeSync Setup Script for Linux

echo "🚀 Starting PokeSync setup..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it and try again."
    exit 1
fi

# Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install it and try again."
    exit 1
fi

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p backups
mkdir -p save_repo

# Create config.json if it doesn't exist to prevent Docker volume issues
if [ ! -f config.json ]; then
    echo "⚙️ Initializing config.json..."
    echo "{}" > config.json
fi

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Setup complete! You can now run PokeSync using:"
    echo "   python3 main.py"
else
    echo "❌ Failed to install dependencies. Please check your internet connection and try again."
    exit 1
fi
