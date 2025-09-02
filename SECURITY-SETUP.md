# 🔒 Security Setup Guide - Brax Jewelers AI Assistant

## 🚨 IMMEDIATE ACTIONS COMPLETED

### ✅ Phase 1: Emergency Remediation (COMPLETED)
1. **Exposed API Key Secured** - Removed from .env file
2. **Git History Clean** - No sensitive data was committed to repository
3. **Enhanced .gitignore** - Prevents future credential exposure
4. **Template Created** - .env.example for safe reference

## 🔐 Phase 2: Production Security Setup

### Azure Key Vault Configuration

#### Step 1: Create Key Vault and Configure Access
```bash
# Run the automated setup script
./azure-keyvault-setup.sh
```

This script will:
- Create Azure Key Vault `brax-ai-secrets`
- Enable managed identity for App Service
- Grant Key Vault access permissions
- Create placeholder secrets

#### Step 2: Update Secrets with Real Values

**CRITICAL: Generate NEW API keys - the old one is compromised**

```bash
# 1. Generate new OpenAI API key at: https://platform.openai.com/api-keys
az keyvault secret set \
    --vault-name "brax-ai-secrets" \
    --name "OPENAI-API-KEY" \
    --value "sk-your-NEW-openai-api-key"

# 2. Update GHL credentials
az keyvault secret set \
    --vault-name "brax-ai-secrets" \
    --name "GHL-API-KEY" \
    --value "pit-3ceb610e-f49d-49c4-9eb5-b6ece59f5c0d"

az keyvault secret set \
    --vault-name "brax-ai-secrets" \
    --name "GHL-PIT-TOKEN" \
    --value "pit-3ceb610e-f49d-49c4-9eb5-b6ece59f5c0d"

# 3. Update other API keys
az keyvault secret set \
    --vault-name "brax-ai-secrets" \
    --name "TAVILY-API-KEY" \
    --value "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"

# 4. Generate secure widget token
WIDGET_TOKEN=$(openssl rand -hex 32)
az keyvault secret set \
    --vault-name "brax-ai-secrets" \
    --name "WIDGET-SECRET-TOKEN" \
    --value "$WIDGET_TOKEN"
```

#### Step 3: Configure App Service to Use Key Vault
```bash
# Run the App Service configuration script
./azure-app-config.sh
```

This configures the App Service with Key Vault references like:
```
OPENAI_API_KEY=@Microsoft.KeyVault(VaultName=brax-ai-secrets;SecretName=OPENAI-API-KEY)
```

## 🛡️ Security Verification Checklist

### ✅ Immediate Verification
1. **Check App Service Configuration**
   ```bash
   az webapp config appsettings list --resource-group brax-chat-rg --name braxjewelersai
   ```

2. **Test Health Endpoint**
   ```bash
   curl https://braxjewelersai.azurewebsites.net/health
   ```

3. **Verify Key Vault Access**
   ```bash
   az webapp log tail --resource-group brax-chat-rg --name braxjewelersai
   ```

### 🔍 Security Validation
- [ ] All secrets stored in Key Vault (not in code)
- [ ] App Service using managed identity
- [ ] Key Vault access properly scoped
- [ ] No sensitive data in git history
- [ ] .gitignore prevents future exposure
- [ ] New API keys generated and configured

## 🚨 API Key Rotation Process

### OpenAI API Key (IMMEDIATE)
1. **Go to**: https://platform.openai.com/api-keys
2. **Create** new API key
3. **Update** Key Vault secret
4. **Delete** old compromised key
5. **Test** application functionality

### GHL API Keys (As Needed)
1. **Go to**: GoHighLevel Settings → Private Integrations
2. **Regenerate** PIT token
3. **Update** Key Vault secrets
4. **Test** CRM functionality

## 📊 Monitoring and Alerting

### Key Vault Monitoring
```bash
# Enable Key Vault logging
az monitor diagnostic-settings create \
    --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/brax-chat-rg/providers/Microsoft.KeyVault/vaults/brax-ai-secrets" \
    --name "KeyVaultAuditLogs" \
    --logs '[{"category": "AuditEvent", "enabled": true}]' \
    --workspace "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/brax-chat-rg/providers/Microsoft.OperationalInsights/workspaces/brax-ai-logs"
```

### Set Up Alerts
1. **Failed Key Vault Access** - Alert on authentication failures
2. **High API Usage** - Monitor OpenAI API costs
3. **Application Errors** - Health check failures

## 🔄 Regular Security Tasks

### Weekly
- [ ] Review Key Vault access logs
- [ ] Monitor API usage and costs
- [ ] Check application health metrics

### Monthly  
- [ ] Review and rotate service tokens
- [ ] Update dependencies and security patches
- [ ] Audit access permissions

### Quarterly
- [ ] Rotate all API keys
- [ ] Security vulnerability assessment
- [ ] Review and update security policies

## 🚨 Incident Response

### If API Key Compromised
1. **Immediately** rotate the compromised key
2. **Review** access logs for unauthorized usage
3. **Monitor** for unexpected API charges
4. **Update** all affected applications
5. **Document** the incident and lessons learned

### If Unauthorized Access Detected
1. **Revoke** suspicious access immediately
2. **Change** all potentially affected credentials
3. **Review** audit logs for scope of access
4. **Implement** additional security measures
5. **Report** to security team and management

## 📞 Emergency Contacts

- **Azure Support**: [Your Azure support plan]
- **OpenAI Support**: https://help.openai.com/
- **GoHighLevel Support**: [Your GHL support contact]
- **Development Team**: [Your team contact info]

---

## ✅ Current Security Status

- **🟢 SECURED**: Exposed API key removed and secured
- **🟢 PROTECTED**: Git repository clean of credentials  
- **🟢 CONFIGURED**: Key Vault setup scripts ready
- **🟡 PENDING**: New API keys need to be generated
- **🟡 PENDING**: Key Vault secrets need real values
- **🟡 PENDING**: App Service configuration needs execution

**Next Action**: Execute `./azure-keyvault-setup.sh` to complete security setup.