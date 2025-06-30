#!/usr/bin/env python3
"""
Main entry point for the Agile Project Insights Dashboard application.
"""

import os
from src.app import app
from pathlib import Path

# Create uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent / "src" / "app" / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
