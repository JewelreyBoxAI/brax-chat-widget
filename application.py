#!/usr/bin/env python3
"""
Azure App Service entry point for Brax Fine Jewelers AI Assistant
This file is required for Azure App Service Python deployment
"""

from src.app import app

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)