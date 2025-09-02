#!/bin/bash
# =============================================================================
# Azure Key Vault Setup Script for Brax Jewelers AI Assistant
# =============================================================================
# This script creates and configures Azure Key Vault for secure secret management

set -e

# Configuration variables
RESOURCE_GROUP="brax-chat-rg"
KEY_VAULT_NAME="brax-ai-secrets"
APP_SERVICE_NAME="braxjewelersai"
LOCATION="centralus"

echo "🔐 Setting up Azure Key Vault for Brax AI Assistant..."
echo "=================================================="

# Check if user is logged in to Azure
if ! az account show > /dev/null 2>&1; then
    echo "❌ Please log in to Azure CLI first: az login"
    exit 1
fi

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📋 Using subscription: $SUBSCRIPTION_ID"

# Create Key Vault (skip if already exists)
echo "🏗️  Creating Key Vault: $KEY_VAULT_NAME"
az keyvault create \
    --name "$KEY_VAULT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku standard \
    --enable-soft-delete true \
    --enable-purge-protection false \
    --retention-days 7 \
    || echo "Key Vault may already exist"

# Enable system-assigned managed identity for App Service
echo "🆔 Enabling managed identity for App Service: $APP_SERVICE_NAME"
PRINCIPAL_ID=$(az webapp identity assign \
    --name "$APP_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query principalId -o tsv)

echo "✅ App Service Principal ID: $PRINCIPAL_ID"

# Grant App Service access to Key Vault
echo "🔑 Granting Key Vault access to App Service..."
az keyvault set-policy \
    --name "$KEY_VAULT_NAME" \
    --object-id "$PRINCIPAL_ID" \
    --secret-permissions get list

echo "📝 Setting up secrets in Key Vault..."
echo "⚠️  You'll need to set these secrets manually with your actual values:"

# Create placeholder secrets (to be updated with real values)
SECRETS=(
    "OPENAI-API-KEY:sk-your-new-openai-api-key-here"
    "GHL-API-KEY:your-ghl-api-key"
    "GHL-PIT-TOKEN:your-private-integration-token"
    "TAVILY-API-KEY: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"
    "WIDGET-SECRET-TOKEN:generate-a-secure-random-token"
)

for secret in "${SECRETS[@]}"; do
    IFS=":" read -r key value <<< "$secret"
    echo "  Setting placeholder for: $key"
    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "$key" \
        --value "$value" \
        --description "Production secret for Brax AI Assistant" \
        > /dev/null
done

echo ""
echo "✅ Azure Key Vault setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update secrets in Key Vault with real values:"
echo "   az keyvault secret set --vault-name $KEY_VAULT_NAME --name OPENAI-API-KEY --value 'your-real-key'"
echo ""
echo "2. Configure App Service to use Key Vault references:"
echo "   Run: ./azure-app-config.sh"
echo ""
echo "3. Test the configuration:"
echo "   curl https://$APP_SERVICE_NAME.azurewebsites.net/health"
echo ""
echo "🔐 Key Vault URL: https://$KEY_VAULT_NAME.vault.azure.net/"