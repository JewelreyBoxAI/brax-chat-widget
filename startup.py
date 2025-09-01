#!/usr/bin/env python3
"""
Azure App Service startup script for Brax Fine Jewelers AI Assistant
"""
import os
import sys
import subprocess

def main():
    """Start the FastAPI application with uvicorn"""
    # Set the port from environment variable (Azure sets this)
    port = os.environ.get("PORT", "8000")
    
    # Start uvicorn server
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "src.app:app", 
        "--host", "0.0.0.0", 
        "--port", port
    ]
    
    print(f"Starting Brax Fine Jewelers AI Assistant on port {port}")
    print(f"Command: {' '.join(cmd)}")
    
    # Execute the uvicorn server
    subprocess.run(cmd)

if __name__ == "__main__":
    main()