# Azure CLI Authentication Troubleshooting Guide
## Brax Fine Jewelers AI Assistant

### Problem: Azure CLI Login Using Wrong Account/Tenant

When Azure CLI keeps trying to authenticate with the wrong Azure account or cached credentials, follow these steps to force a clean authentication.

---

## ✅ **Solution: Complete Cache Clear and Forced Authentication**

### Step-by-Step Process That Worked:

#### 1. **Clear All Azure CLI Cache**
```powershell
# Logout from any existing sessions
az logout

# Clear all cached account information
az account clear
```

#### 2. **Disable Azure CLI Broker (Optional but Helpful)**
```powershell
# Disable broker authentication to avoid cached credentials
az config set core.allow_broker=false
```

#### 3. **Force Login with Specific Tenant**
```powershell
# Method 1: Login with specific tenant ID (most reliable)
az login --use-device-code --tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"

# Method 2: Standard device code login (if tenant method doesn't work)
az login --use-device-code
```

#### 4. **Complete Device Code Authentication**
- **Go to**: `https://microsoft.com/devicelogin`
- **Enter the device code** provided by the CLI
- **Sign in** with the correct Azure account for Anthonyyummyimagemedia.onmicrosoft.com
- **Select the correct subscription** if prompted

#### 5. **Verify Authentication**
```powershell
# Check that you're logged into the correct account/subscription
az account show --query "{subscriptionId:id, tenantId:tenantId, name:name}" --output table

# Expected output:
# SubscriptionId: f61d0d8c-cae8-4ffc-b4a6-c696c5a0a7f8
# TenantId: 4ceaeb6a-c5a7-40cd-98ef-a578bc94192f
# Name: Azure subscription 1
```

---

## 🔧 **What We Did to Fix It**

### **Root Cause:**
- Azure CLI was using cached credentials from a different Azure account
- Browser session was logged into different Microsoft account
- CLI was defaulting to wrong tenant/directory

### **Solution Applied:**
1. **Complete cache clearing**: `az logout` + `az account clear`
2. **Disabled broker authentication**: `az config set core.allow_broker=false`
3. **Forced tenant-specific login**: `--tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"`
4. **Fresh device code authentication**: New device code with clean session

### **Key Commands That Resolved the Issue:**
```powershell
az logout
az account clear
az config set core.allow_broker=false
az login --use-device-code --tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"
```

---

## 📋 **Quick Reference for Future Use**

### **When Azure CLI Login Fails or Uses Wrong Account:**

```powershell
# Nuclear option - complete reset
az logout && az account clear && az config set core.allow_broker=false

# Force clean login with your specific tenant
az login --use-device-code --tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"

# Verify success
az account show --query "{subscriptionId:id, tenantId:tenantId, name:name}" --output table
```

### **Your Specific Azure Details:**
- **Subscription ID**: `f61d0d8c-cae8-4ffc-b4a6-c696c5a0a7f8`
- **Tenant ID**: `4ceaeb6a-c5a7-40cd-98ef-a578bc94192f`  
- **Directory**: `Anthonyyummyimagemedia.onmicrosoft.com`
- **Subscription Name**: `Azure subscription 1`

---

## 🚨 **Alternative Methods (If Above Doesn't Work)**

### **Method 1: Browser-Based Login**
```powershell
# If device code fails, try interactive browser login
az login --tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"
```

### **Method 2: Service Principal (For CI/CD)**
```powershell
# For automated deployments (requires service principal setup)
az login --service-principal -u <app-id> -p <password> --tenant "4ceaeb6a-c5a7-40cd-98ef-a578bc94192f"
```

### **Method 3: Azure Cloud Shell**
- Use Azure Portal > Cloud Shell if local CLI continues to have issues
- All authentication is handled automatically in Cloud Shell

---

## ✅ **Success Indicators**

You know the authentication worked when:

1. **Device code authentication completes** without errors
2. **`az account show` returns your correct subscription details**
3. **Tenant ID matches**: `4ceaeb6a-c5a7-40cd-98ef-a578bc94192f`
4. **Subscription ID matches**: `f61d0d8c-cae8-4ffc-b4a6-c696c5a0a7f8`

---

**Note**: This process was tested and confirmed working for the Brax Fine Jewelers Azure deployment on 2025-01-09.