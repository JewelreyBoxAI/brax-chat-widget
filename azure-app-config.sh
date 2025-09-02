#!/bin/bash
# =============================================================================
# Azure App Service Configuration Script
# =============================================================================
# Configures App Service to use Azure Key Vault references for secrets

set -e

# Configuration variables
RESOURCE_GROUP="brax-chat-rg"
KEY_VAULT_NAME="brax-ai-secrets"
APP_SERVICE_NAME="braxjewelersai"

echo "⚙️  Configuring App Service to use Key Vault references..."
echo "========================================================"

# Check if user is logged in to Azure
if ! az account show > /dev/null 2>&1; then
    echo "❌ Please log in to Azure CLI first: az login"
    exit 1
fi

echo "🔧 Setting App Service configuration..."

# Configure App Service settings with Key Vault references
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE_NAME" \
    --settings \
        ENVIRONMENT="production" \
        PORT="8000" \
        OPENAI_MODEL="gpt-4o-mini" \
        MAX_TOKENS="1024" \
        TEMPERATURE="0.9" \
        OPENAI_API_KEY="@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=OPENAI-API-KEY)" \
        GHL_API_KEY="@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=GHL-API-KEY)" \
        GHL_PIT_TOKEN="@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=GHL-PIT-TOKEN)" \
        TAVILY_API_KEY="@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=TAVILY-API-KEY)" \
        WIDGET_SECRET_TOKEN="@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=WIDGET-SECRET-TOKEN)" \
        GHL_API_BASE_URL="https://rest.gohighlevel.com/v1" \
        GHL_SUB_ACCOUNT_ID="777ojtmSz83tsH2CMPot" \
        GHL_LOCATION_ID="777ojtmSz83tsH2CMPot" \
        GHL_MCP_ENABLED="false" \
        GHL_MCP_URL="https://placeholder-mcp-server.azurewebsites.net/mcp/" \
        GHL_MCP_TIMEOUT="30" \
        GHL_DEFAULT_CONTACT_LIMIT="100" \
        GHL_DEFAULT_MESSAGE_LIMIT="20" \
        GHL_DEFAULT_TRANSACTION_LIMIT="20" \
        GHL_CALENDAR_REPAIR_ID="1a2FZj1zqXPbPnrElQD1" \
        GHL_CALENDAR_CUSTOM_JEWELRY_ID="1cORCj9LXQr9iDQaDTn9" \
        GHL_CALENDAR_APPRAISALS_ID="7pRF2Il5lcRZIMBdSkBx" \
        GHL_CALENDAR_CAMPAIGN_ID="CuOcD0x88h7NPvfub9" \
        TRUSTED_HOSTS="*.azurewebsites.net,braxjewelers.com,*.braxjewelers.com" \
        ALLOWED_ORIGINS="https://braxjewelers.com,https://*.braxjewelers.com,https://*.azurewebsites.net" \
        ENABLE_RATE_LIMITING="true" \
        ENABLE_CORS="true" \
        ENABLE_SECURITY_HEADERS="true" \
        ENABLE_TELEMETRY="true" \
        ENABLE_DEBUG_ENDPOINTS="false" \
        ENABLE_SWAGGER_UI="false" \
        HEALTH_CHECK_TIMEOUT="30" \
        LOG_LEVEL="INFO"

echo ""
echo "✅ App Service configuration complete!"
echo ""
echo "🔍 Verification steps:"
echo "1. Check App Service configuration:"
echo "   az webapp config appsettings list --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME"
echo ""
echo "2. Test health endpoint:"
echo "   curl https://$APP_SERVICE_NAME.azurewebsites.net/health"
echo ""
echo "3. Monitor application logs:"
echo "   az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME"
echo ""
echo "⚠️  Remember to update Key Vault secrets with real values!"
echo "🔐 Key Vault: https://$KEY_VAULT_NAME.vault.azure.net/"