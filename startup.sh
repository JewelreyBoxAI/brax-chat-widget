#!/bin/bash
# Azure App Service startup script
cd /home/site/wwwroot
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000