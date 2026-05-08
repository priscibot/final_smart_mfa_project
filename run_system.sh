#!/bin/bash

echo "========================================================"
echo "Smart MFA System - Quick Start Script"
echo "========================================================"
echo ""

# Check if models exist
if [ ! -f "backend/models/isolation_forest_model.pkl" ]; then
    echo "⚠ Models not found. Training models..."
    cd backend/models
    python3 train_models.py
    cd ../..
    echo ""
fi

echo "✓ System ready!"
echo ""
echo "Demo Credentials:"
echo "  User 1: user_001 / password123"
echo "  User 2: user_002 / secure456"
echo "  Admin:  admin / admin123"
echo ""
echo "Starting Flask server..."
echo "========================================================"
echo ""

cd backend
python3 app.py
