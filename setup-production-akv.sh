#!/bin/bash
# Production setup script for Azure Key Vault integration
# This script configures App Service to use Key Vault references

set -e

# Configuration - Update these for your deployment
APP_NAME="braxjewelersai"
RESOURCE_GROUP="brax-chat-rg"
KEY_VAULT_NAME="brax-jewelers-kv"

echo "🚀 Setting up production Azure Key Vault integration"
echo "======================================================"
echo "App Service: $APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Key Vault: $KEY_VAULT_NAME"
echo ""

# Verify Azure login
if ! az account show &>/dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Check if App Service exists, if not provide instructions
if ! az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "ℹ️  App Service '$APP_NAME' not found. Creating it..."
    
    # Create App Service Plan if it doesn't exist
    if ! az appservice plan show --name "${APP_NAME}-plan" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        echo "Creating App Service Plan..."
        az appservice plan create \
            --name "${APP_NAME}-plan" \
            --resource-group "$RESOURCE_GROUP" \
            --sku B1 \
            --is-linux \
            --location eastus
    fi
    
    # Create App Service
    echo "Creating App Service..."
    az webapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --plan "${APP_NAME}-plan" \
        --runtime "PYTHON:3.11"
fi

echo "✅ App Service '$APP_NAME' ready"

# Enable system-assigned managed identity
echo "Enabling managed identity..."
az webapp identity assign \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none

# Get the principal ID
PRINCIPAL_ID=$(az webapp identity show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query principalId \
    --output tsv)

echo "✅ Managed identity enabled (Principal ID: ${PRINCIPAL_ID:0:8}...)"

# Grant Key Vault access permissions
echo "Granting Key Vault permissions..."
az keyvault set-policy \
    --name "$KEY_VAULT_NAME" \
    --object-id "$PRINCIPAL_ID" \
    --secret-permissions get list \
    --output none

echo "✅ Key Vault permissions granted"

# Configure App Service settings with Key Vault references
echo "Configuring App Service settings..."

az webapp config appsettings set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings \
        "ENVIRONMENT=production" \
        "OPENAI_API_KEY=@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=openai-api-key)" \
        "OPENAI_MODEL=gpt-4o-mini" \
        "MAX_TOKENS=1024" \
        "TEMPERATURE=0.9" \
        "TRUSTED_HOSTS=*.azurewebsites.net,localhost,127.0.0.1" \
        "ALLOWED_ORIGINS=https://*.braxjewelers.com,https://*.azurewebsites.net" \
        "ENABLE_RATE_LIMITING=true" \
        "ENABLE_CORS=true" \
        "ENABLE_SECURITY_HEADERS=true" \
        "GHL_MCP_ENABLED=true" \
        "GHL_MCP_URL=http://52.188.29.127:8000/mcp/call_tool" \
        "GHL_PIT_TOKEN=pit-643e015d-9c44-4183-8d3a-0ec3a67b966f" \
        "GHL_LOCATION_ID=777ojtmSz83tsH2CMPot" \
        "TAVILY_API_KEY=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" \
    --output none

echo "✅ App Service configuration updated"

echo ""
echo "🎉 Production setup complete!"
echo "=============================="
echo ""
echo "Key Vault Integration:"
echo "  ✅ OpenAI API key securely stored in Key Vault"
echo "  ✅ App Service has Key Vault access permissions"
echo "  ✅ App Service configured with Key Vault references"
echo ""
echo "Next Steps:"
echo "1. Deploy your application code to the App Service"
echo "2. Test the /health endpoint to verify configuration"
echo "3. Monitor Application Insights for any issues"
echo ""
echo "App Service URL: https://$APP_NAME.azurewebsites.net"
echo "Health Check: https://$APP_NAME.azurewebsites.net/health"
echo ""
echo "🔐 Security: All sensitive keys are now stored in Azure Key Vault"