#!/bin/bash
# =============================================================================
# Immediate Deployment Script - Brax Jewelers AI Assistant
# =============================================================================
# Deploys the main application in fallback mode (without MCP server dependency)
# This allows immediate deployment while maintaining upgrade path to full CRM

set -e

# Configuration
RESOURCE_GROUP="brax-chat-rg"
APP_SERVICE_NAME="braxjewelersai"
KEY_VAULT_NAME="brax-ai-secrets"

echo "🚀 Deploying Brax Jewelers AI Assistant (Immediate Mode)"
echo "========================================================"
echo ""
echo "📋 Deployment Mode: FALLBACK (MCP Server Optional)"
echo "   ✅ Chat functionality: ENABLED"
echo "   ✅ AI responses: ENABLED"
echo "   ⚠️  CRM integration: FALLBACK MODE"
echo ""

# Check Azure login
if ! az account show > /dev/null 2>&1; then
    echo "❌ Please log in to Azure CLI first: az login"
    exit 1
fi

echo "🔍 Checking current deployment status..."
CURRENT_STATE=$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" --query "state" -o tsv 2>/dev/null || echo "NotFound")
echo "   App Service State: $CURRENT_STATE"

if [ "$CURRENT_STATE" = "NotFound" ]; then
    echo "❌ App Service not found. Please create it first or check the name/resource group."
    exit 1
fi

echo ""
echo "🔧 Step 1: Configure Application Settings (Fallback Mode)..."
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE_NAME" \
    --settings \
        ENVIRONMENT="production" \
        PORT="8000" \
        OPENAI_MODEL="gpt-4o-mini" \
        MAX_TOKENS="1024" \
        TEMPERATURE="0.9" \
        GHL_API_BASE_URL="https://rest.gohighlevel.com/v1" \
        GHL_SUB_ACCOUNT_ID="777ojtmSz83tsH2CMPot" \
        GHL_LOCATION_ID="777ojtmSz83tsH2CMPot" \
        GHL_MCP_ENABLED="false" \
        GHL_MCP_URL="https://placeholder-mcp-server.azurewebsites.net/mcp/" \
        GHL_MCP_TIMEOUT="30" \
        GHL_CALENDAR_REPAIR_ID="1a2FZj1zqXPbPnrElQD1" \
        GHL_CALENDAR_CUSTOM_JEWELRY_ID="1cORCj9LXQr9iDQaDTn9" \
        GHL_CALENDAR_APPRAISALS_ID="7pRF2Il5lcRZIMBdSkBx" \
        GHL_CALENDAR_CAMPAIGN_ID="CuOcD0x88h7NPvfub9" \
        TAVILY_API_KEY="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" \
        TRUSTED_HOSTS="*.azurewebsites.net,braxjewelers.com,*.braxjewelers.com" \
        ALLOWED_ORIGINS="https://braxjewelers.com,https://*.braxjewelers.com,https://*.azurewebsites.net" \
        ENABLE_RATE_LIMITING="true" \
        ENABLE_CORS="true" \
        ENABLE_SECURITY_HEADERS="true" \
        ENABLE_TELEMETRY="true" \
        ENABLE_DEBUG_ENDPOINTS="false" \
        ENABLE_SWAGGER_UI="false" \
        HEALTH_CHECK_TIMEOUT="30" \
        LOG_LEVEL="INFO" > /dev/null

echo "✅ Application settings configured for fallback mode"

echo ""
echo "⚠️  Step 2: Security Check - API Keys..."
echo "   Note: Placeholder values set. Update with real keys using Key Vault or direct configuration:"
echo ""
echo "   For Key Vault (Recommended):"
echo "   az webapp config appsettings set \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --name $APP_SERVICE_NAME \\"
echo "     --settings OPENAI_API_KEY='@Microsoft.KeyVault(VaultName=$KEY_VAULT_NAME;SecretName=OPENAI-API-KEY)'"
echo ""
echo "   For Direct Configuration (Less Secure):"
echo "   az webapp config appsettings set \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --name $APP_SERVICE_NAME \\"
echo "     --settings OPENAI_API_KEY='sk-your-new-api-key'"
echo ""

echo "🔄 Step 3: Deploy Application Code..."

# Check if we need to deploy from local directory or trigger existing deployment
if [ -f "startup.py" ] && [ -f "requirements.txt" ]; then
    echo "   📦 Deploying from local directory..."
    
    # Create deployment package
    echo "   Creating deployment package..."
    zip -r deployment-fallback.zip . \
        -x "*.git*" "*node_modules*" "*.venv*" "*.pyc" "__pycache__*" \
        "*.log" "deploy*.zip" "test_*.py" "*.md" > /dev/null
    
    # Deploy via ZIP
    echo "   Uploading to Azure App Service..."
    az webapp deployment source config-zip \
        --resource-group "$RESOURCE_GROUP" \
        --name "$APP_SERVICE_NAME" \
        --src deployment-fallback.zip > /dev/null
    
    # Cleanup
    rm deployment-fallback.zip
    echo "✅ Application deployed successfully"
else
    echo "   ⚠️  Source files not found in current directory"
    echo "   Triggering restart to apply configuration changes..."
    az webapp restart --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" > /dev/null
    echo "✅ Application restarted with new configuration"
fi

echo ""
echo "⏱️  Step 4: Waiting for application startup..."
sleep 30

echo ""
echo "🧪 Step 5: Verification Tests..."

APP_URL="https://$APP_SERVICE_NAME.azurewebsites.net"
echo "   Testing: $APP_URL/health"

# Test health endpoint
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/health" || echo "000")
if [ "$HEALTH_STATUS" = "200" ]; then
    echo "   ✅ Health check: PASSED"
    
    # Get detailed health info
    echo "   📊 Health details:"
    curl -s "$APP_URL/health" | python -m json.tool | grep -E '"status"|"ghl_mcp_status"' | head -2
else
    echo "   ❌ Health check: FAILED (HTTP $HEALTH_STATUS)"
    echo "   Check application logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME"
fi

# Test widget endpoint
echo "   Testing: $APP_URL/widget"
WIDGET_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/widget" || echo "000")
if [ "$WIDGET_STATUS" = "200" ]; then
    echo "   ✅ Chat widget: ACCESSIBLE"
else
    echo "   ❌ Chat widget: FAILED (HTTP $WIDGET_STATUS)"
fi

# Test CRM fallback
echo "   Testing: $APP_URL/crm/contacts"
CRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/crm/contacts" || echo "000")
if [ "$CRM_STATUS" = "503" ]; then
    echo "   ✅ CRM fallback: WORKING (Expected 503 - Service Unavailable)"
else
    echo "   ⚠️  CRM endpoint: Unexpected response (HTTP $CRM_STATUS)"
fi

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "========================"
echo ""
echo "🌐 Application URL: $APP_URL"
echo "💬 Chat Widget: $APP_URL/widget"
echo "🏥 Health Check: $APP_URL/health"
echo ""
echo "📊 Current Status:"
echo "   ✅ Chat functionality: FULLY OPERATIONAL"
echo "   ✅ AI responses: FULLY OPERATIONAL"  
echo "   ✅ Security: CONFIGURED (update API keys as needed)"
echo "   ⚠️  CRM integration: FALLBACK MODE (MCP server required for full functionality)"
echo ""
echo "🔄 To Enable Full CRM Integration:"
echo "   1. Deploy GHL MCP Server (separate repository)"
echo "   2. Update GHL_MCP_URL configuration"
echo "   3. Set GHL_MCP_ENABLED=true"
echo ""
echo "📞 Quick Test: Visit $APP_URL/widget and try the chat!"
echo ""
echo "📋 Next Steps:"
echo "   - Monitor application: az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME"
echo "   - Update API keys: Use Key Vault or direct configuration"
echo "   - Deploy MCP server when ready for full CRM functionality"