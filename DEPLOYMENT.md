# Brax Jewelers AI Assistant - Deployment Guide

## Architecture Overview

This application consists of two main components:

1. **Main AI Assistant Application** (this repository)
   - FastAPI backend with LangChain integration
   - Chat widget frontend
   - GHL MCP client integration

2. **GoHighLevel MCP Server** (separate repository)
   - Provides Model Context Protocol interface to GHL API
   - Must be deployed independently before main application

## Prerequisites

### 1. GoHighLevel MCP Server Deployment

**CRITICAL:** The MCP server must be deployed first as the main application depends on it.

```bash
# Deploy MCP server to Azure (separate repository)
# Update GHL_MCP_URL in .env with the deployed MCP server URL
GHL_MCP_URL=https://your-mcp-server.azurewebsites.net/mcp/
```

### 2. Required Azure Resources

- Azure App Service (Linux, Python 3.11)
- Azure Container Registry (optional, for containerized deployment)
- Application Insights (recommended for monitoring)

### 3. Environment Variables Configuration

Set these in Azure App Service Configuration > Application Settings:

```bash
# Core Application
ENVIRONMENT=production
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini

# GoHighLevel Integration
GHL_API_KEY=your-ghl-api-key
GHL_SUB_ACCOUNT_ID=your-sub-account-id
GHL_MCP_ENABLED=true
GHL_MCP_URL=https://your-mcp-server.azurewebsites.net/mcp/
GHL_PIT_TOKEN=your-private-integration-token
GHL_LOCATION_ID=your-location-id

# Security
TRUSTED_HOSTS=*.azurewebsites.net,yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://*.azurewebsites.net

# Feature Flags
ENABLE_RATE_LIMITING=true
ENABLE_CORS=true
ENABLE_SECURITY_HEADERS=true
```

## Deployment Strategy

### Phase 1: MCP Server Deployment (Prerequisite)
1. Deploy GHL MCP Server to Azure App Service
2. Configure MCP server environment variables
3. Test MCP server health endpoint
4. Document MCP server URL for main application

### Phase 2: Main Application Deployment
1. Configure environment variables with MCP server URL
2. Deploy main application using preferred method
3. Verify health checks include MCP connectivity
4. Test CRM integration endpoints

### Phase 3: Production Validation
1. End-to-end testing with real GHL data
2. Performance testing under load
3. Monitoring and alerting setup
4. Documentation and runbook completion

## Deployment Methods

### Method 1: Docker Deployment (Recommended)

```bash
# Build and push container
docker build -t brax-ai-assistant .
az acr login --name yourregistry
docker tag brax-ai-assistant yourregistry.azurecr.io/brax-ai-assistant:latest
docker push yourregistry.azurecr.io/brax-ai-assistant:latest

# Deploy to Azure App Service
az webapp create \
  --resource-group your-rg \
  --plan your-app-service-plan \
  --name brax-ai-assistant \
  --deployment-container-image-name yourregistry.azurecr.io/brax-ai-assistant:latest
```

### Method 2: Git Deployment

```bash
# Configure deployment source
az webapp deployment source config \
  --name brax-ai-assistant \
  --resource-group your-rg \
  --repo-url https://github.com/yourusername/brax-chatbot \
  --branch main \
  --manual-integration
```

### Method 3: ZIP Deployment

```bash
# Create deployment package
zip -r deployment.zip . -x "*.git*" "*node_modules*" "*.venv*" "*.pyc" "__pycache__*"

# Deploy via Azure CLI
az webapp deployment source config-zip \
  --name brax-ai-assistant \
  --resource-group your-rg \
  --src deployment.zip
```

## Dependency Management

### Critical Dependencies
1. **GHL MCP Server** - Must be running and accessible
2. **OpenAI API** - Valid API key with sufficient credits
3. **GoHighLevel API** - Valid PIT token and location access

### Health Check Monitoring
The application monitors all dependencies at `/health`:

```json
{
  "status": "healthy",
  "service": "Brax Fine Jewelers AI Assistant",
  "version": "2.0.0",
  "checks": {
    "llm_configured": true,
    "templates_loaded": true,
    "ghl_mcp_status": "connected",
    "active_sessions": 5
  }
}
```

## Post-Deployment Verification

### 1. Basic Functionality Test
```bash
curl -X GET "https://your-app.azurewebsites.net/health"
```

### 2. GHL MCP Integration Test
```bash
curl -X POST "https://your-app.azurewebsites.net/crm/contacts" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}'
```

### 3. Chat Functionality Test
Navigate to `https://your-app.azurewebsites.net/widget` and test the chat interface.

## Troubleshooting

### Common Issues

1. **MCP Connection Failed**
   - Verify MCP server is deployed and accessible
   - Check `GHL_MCP_URL` configuration
   - Validate PIT token and location ID
   - Test MCP server health endpoint directly

2. **OpenAI API Errors**
   - Verify API key is valid and has credits
   - Check rate limiting settings
   - Monitor usage quotas

3. **CORS Issues**
   - Update `ALLOWED_ORIGINS` in configuration
   - Verify domain settings
   - Check security headers

## Security Considerations

1. **API Key Management**
   - Use Azure Key Vault for production secrets
   - Rotate keys regularly
   - Monitor for unauthorized usage

2. **Network Security**
   - Configure proper CORS origins
   - Use HTTPS only in production
   - Implement rate limiting

3. **Monitoring and Alerting**
   - Set up Application Insights
   - Configure health check alerts
   - Monitor API costs and usage

## Maintenance and Updates

### Regular Tasks
1. Monitor MCP server health and performance
2. Update dependencies monthly
3. Review and rotate API keys quarterly
4. Monitor costs and optimize usage

### Emergency Procedures
1. Check all health endpoints
2. Verify MCP server connectivity
3. Review application logs
4. Restart services if needed
5. Escalate to development team

## Cost Optimization

1. **MCP Server Efficiency**
   - Monitor API call frequency
   - Implement caching where appropriate
   - Optimize request batching

2. **Resource Usage**
   - Use appropriate Azure service tiers
   - Scale down during low usage
   - Monitor compute and API costs