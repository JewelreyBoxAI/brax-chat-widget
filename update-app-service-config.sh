#!/bin/bash
# Script to update Azure App Service configuration to use Key Vault reference
# Usage: ./update-app-service-config.sh

set -e

# Configuration - Update these values for your deployment
APP_NAME="brax-jewelers-ai"
RESOURCE_GROUP="brax-jewelers-rg"
KEY_VAULT_NAME="brax-jewelers-kv"
SECRET_NAME="openai-api-key"

echo "Updating App Service configuration to use Key Vault reference..."
echo "App Service: $APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Key Vault: $KEY_VAULT_NAME"
echo ""

# Check if user is logged in to Azure
if ! az account show &>/dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Check if App Service exists
if ! az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "❌ App Service '$APP_NAME' not found in resource group '$RESOURCE_GROUP'"
    echo "Please create the App Service first or update the configuration."
    exit 1
fi

echo "✅ App Service '$APP_NAME' found"

# Enable system-assigned managed identity for the App Service
echo "Enabling managed identity for App Service..."
az webapp identity assign \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ Managed identity enabled"
else
    echo "❌ Failed to enable managed identity"
    exit 1
fi

# Get the principal ID of the managed identity
PRINCIPAL_ID=$(az webapp identity show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query principalId \
    --output tsv)

echo "App Service Principal ID: $PRINCIPAL_ID"

# Grant Key Vault access to the App Service managed identity
echo "Granting Key Vault access permissions..."
az keyvault set-policy \
    --name "$KEY_VAULT_NAME" \
    --object-id "$PRINCIPAL_ID" \
    --secret-permissions get list \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ Key Vault permissions granted"
else
    echo "❌ Failed to grant Key Vault permissions"
    exit 1
fi

# Update App Service configuration to use Key Vault reference
echo "Updating App Service configuration..."
az webapp config appsettings set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "OPENAI_API_KEY=@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=$SECRET_NAME)" \
    --output none

if [ $? -eq 0 ]; then
    echo "✅ App Service configuration updated successfully"
    echo ""
    echo "Configuration Summary:"
    echo "  OPENAI_API_KEY = @Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=$SECRET_NAME)"
    echo ""
    echo "Next steps:"
    echo "1. Restart the App Service: az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP"
    echo "2. Test the /health endpoint to verify the API key is working"
    echo "3. Monitor Application Insights for any configuration errors"
else
    echo "❌ Failed to update App Service configuration"
    exit 1
fi

echo ""
echo "🔐 Security: OpenAI API key is now securely referenced from Key Vault"
echo "🚀 The App Service will automatically retrieve the key at runtime"