# Azure App Service Deployment Guide
## Brax Fine Jewelers AI Assistant

### Prerequisites
- **Azure CLI**: Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
- **Python 3.11**: Already installed (FastAPI project requirement)
- **Active Azure Subscription**: Already available
- **PowerShell**: Built into Windows

---

## Step-by-Step Deployment

### 1. Install Azure CLI (if not already installed)
```powershell
# Download and install Azure CLI from Microsoft's official site
# Or use winget (Windows Package Manager)
winget install Microsoft.AzureCLI
```

### 2. Login to Azure
```powershell
# Login to your Azure account
az login

# Verify login and list subscriptions
az account list --output table

# Set your specific subscription
az account set --subscription "f61d0d8c-cae8-4ffc-b4a6-c696c5a0a7f8"

# Verify active subscription
az account show --query "name" --output tsv
```

### 3. Navigate to Project Directory
```powershell
# Navigate to your project folder
cd "C:\AI_src\Brax Chatbot"

# Verify you're in the right location
Get-ChildItem
```

### 4. Create Resource Group (Optional - az webapp up can create one)
```powershell
# Create a resource group in East US
az group create --name "brax-jewelers-rg" --location "eastus"
```

### 5. Deploy Application Using az webapp up
```powershell
# Deploy FastAPI app to Azure App Service
az webapp up `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --location "eastus" `
  --runtime "PYTHON|3.11" `
  --sku "B1"

# Note: If the app name is taken, Azure will suggest alternatives
# The --sku "B1" provides a basic paid tier suitable for production
```

### 6. Configure Environment Variables
```powershell
# Set OpenAI API Key (replace with your actual key)
az webapp config appsettings set `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --settings "OPENAI_API_KEY=your-openai-api-key-here"

# Set allowed origins for CORS (include your website domains)
az webapp config appsettings set `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --settings "ALLOWED_ORIGINS=https://www.braxjewelers.com,https://braxjewelers.com,https://braxjewelersassistant.azurewebsites.net"

# Set optional model configuration
az webapp config appsettings set `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --settings "OPENAI_MODEL=gpt-4o-mini" "MAX_TOKENS=1024" "TEMPERATURE=0.9"
```

### 7. Configure Startup Command (Important for FastAPI)
```powershell
# Set the startup command to use our startup script
az webapp config set `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --startup-file "python startup.py"
```

### 8. Restart Application
```powershell
# Restart the web app to apply all settings
az webapp restart `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg"
```

### 9. Verify Deployment
```powershell
# Get the application URL
az webapp show `
  --name "braxjewelersassistant" `
  --resource-group "brax-jewelers-rg" `
  --query "defaultHostName" `
  --output tsv

# Test the endpoints
# Health check: https://braxjewelersassistant.azurewebsites.net/health
# Widget: https://braxjewelersassistant.azurewebsites.net/widget
```

---

## Quick Commands Summary

```powershell
# Complete deployment in one go:
cd "C:\AI_src\Brax Chatbot"
az login
az account set --subscription "f61d0d8c-cae8-4ffc-b4a6-c696c5a0a7f8"
az webapp up --name "braxjewelersassistant" --resource-group "brax-jewelers-rg" --location "eastus" --runtime "PYTHON|3.11" --sku "B1"
az webapp config appsettings set --name "braxjewelersassistant" --resource-group "brax-jewelers-rg" --settings "OPENAI_API_KEY=your-key-here" "ALLOWED_ORIGINS=https://www.braxjewelers.com,https://braxjewelers.com"
az webapp config set --name "braxjewelersassistant" --resource-group "brax-jewelers-rg" --startup-file "python startup.py"
az webapp restart --name "braxjewelersassistant" --resource-group "brax-jewelers-rg"
```

---

## Expected URLs After Deployment

- **Widget**: `https://braxjewelersassistant.azurewebsites.net/widget`
- **Health Check**: `https://braxjewelersassistant.azurewebsites.net/health`
- **Chat API**: `https://braxjewelersassistant.azurewebsites.net/chat`

---

## iframe Embedding on Brax Website

```html
<!-- Add this iframe to your Brax website -->
<iframe 
  src="https://braxjewelersassistant.azurewebsites.net/widget" 
  width="100%" 
  height="700px" 
  frameborder="0"
  style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
</iframe>
```

---

## Troubleshooting

### Check Application Logs
```powershell
# View recent logs
az webapp log tail --name "braxjewelersassistant" --resource-group "brax-jewelers-rg"
```

### Update Application Code
```powershell
# Redeploy after making changes
cd "C:\AI_src\Brax Chatbot"
az webapp up --name "braxjewelersassistant" --resource-group "brax-jewelers-rg"
```

### View Configuration
```powershell
# List all app settings
az webapp config appsettings list --name "braxjewelersassistant" --resource-group "brax-jewelers-rg" --output table
```

---

## Cost Management
- **B1 Basic Plan**: ~$13/month (suitable for production)
- **F1 Free Plan**: Available but has limitations (60 CPU minutes/day)
- **Scale up/down**: Use Azure portal to adjust pricing tier as needed

---

**Note**: Replace `"braxjewelersassistant"` with your preferred app name if it's already taken. Azure will suggest alternatives during deployment.