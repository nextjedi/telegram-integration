# Telegram Trading Bot - Azure Deployment Guide

This guide explains how to deploy the Telegram Trading Bot to Azure with automated scheduling for Monday-Friday 8 AM to 4 PM operation.

## Architecture

- **Azure Container Apps**: Hosts the containerized bot with auto-scaling
- **Azure Container Registry**: Stores the Docker images
- **Azure Key Vault**: Securely stores Telegram credentials
- **GitHub Actions**: Automated CI/CD pipeline
- **Cron-based Scheduling**: Automatic start/stop during trading hours

## Prerequisites

1. **Azure Subscription** with appropriate permissions
2. **Telegram API Credentials** from [my.telegram.org](https://my.telegram.org/auth)
3. **GitHub Repository** with Actions enabled
4. **Azure CLI** installed locally

## Step 1: Initial Azure Setup

### 1.1 Clone and Navigate to Repository
```bash
git clone <your-repo-url>
cd telegram-integration-com
```

### 1.2 Login to Azure
```bash
az login
az account set --subscription "your-subscription-id"
```

### 1.3 Deploy Infrastructure
```bash
cd azure
chmod +x deploy.sh
./deploy.sh
```

The script will prompt for:
- Telegram API ID
- Telegram API Hash  
- Telegram Phone Number
- Trading API Endpoint (optional)

## Step 2: GitHub Actions Configuration

### 2.1 Create Service Principal
```bash
az ad sp create-for-rbac --name "telegram-trading-sp" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/telegram-trading-rg \
  --sdk-auth
```

### 2.2 Get Container Registry Credentials
```bash
az acr credential show --name telegramtradingregistry
```

### 2.3 Add GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and Variables > Actions** and add:

#### Required Secrets:
- `AZURE_CREDENTIALS`: Complete JSON output from service principal creation
- `AZURE_REGISTRY_USERNAME`: Registry username from step 2.2
- `AZURE_REGISTRY_PASSWORD`: Registry password from step 2.2
- `TRADING_API_ENDPOINT`: Your trading API endpoint
- `BTST_CHANNEL_ID`: Channel ID for BTST (-1001552501322)
- `DAYTRADE_CHANNEL_ID`: Channel ID for day trading (-1001752927494)  
- `UNIVEST_CHANNEL_ID`: Channel ID for Univest (-1001983880498)

## Step 3: Session File Handling

The Telegram session file is stored in Azure File Share for persistence across deployments.

### 3.1 Initial Setup - Azure File Share Storage

#### Create Storage Account and File Share
```bash
# Storage account already exists: telegramint6a7207
# File share already exists: telegram-sessions

# If you need to create new ones:
az storage account create --name <storage-name> --resource-group AlgoTrading --location southindia --sku Standard_LRS
az storage share create --name telegram-sessions --account-name <storage-name>
```

#### Add Storage to Container Apps Environment
```bash
# Get storage account key
STORAGE_KEY=$(az storage account keys list --account-name telegramint6a7207 --resource-group AlgoTrading --query "[0].value" --output tsv)

# Add storage to Container Apps environment
az containerapp env storage set \
  --name telegram-trading-env \
  --resource-group AlgoTrading \
  --storage-name telegram-sessions-storage \
  --access-mode ReadWrite \
  --azure-file-account-name telegramint6a7207 \
  --azure-file-account-key "$STORAGE_KEY" \
  --azure-file-share-name telegram-sessions
```

### 3.2 Generate Session File Locally
```bash
# Method 1: Run the bot locally to generate session
cd src/
python telegram_bot.py
# This will prompt for phone number and verification code
# Session file created: session_name.session

# Method 2: Run groupmessage.py (if telegram_bot.py fails)
python groupmessage.py
# Session file created: session_name.session
```

### 3.3 Upload Session File to Azure File Share

#### Option A: Using Azure CLI
```bash
# Upload session file to Azure File Share
az storage file upload \
  --share-name telegram-sessions \
  --source src/session_name.session \
  --path telegram_trading_session.session \
  --account-name telegramint6a7207
```

#### Option B: Using Azure Portal
1. Navigate to Storage Account `telegramint6a7207`
2. Go to File shares → `telegram-sessions`
3. Upload `session_name.session` as `telegram_trading_session.session`

#### Option C: Using Azure Storage Explorer
1. Download and install Azure Storage Explorer
2. Connect to your Azure account
3. Navigate to `telegramint6a7207` → File Shares → `telegram-sessions`
4. Upload the session file

### 3.4 Update Session File When Needed

If you need to update the session file (e.g., after rate limiting or session expiry):

#### Step 1: Generate New Session Locally
```bash
# Remove old session file
rm src/session_name.session

# Generate new session
cd src/
python telegram_bot.py
# Enter phone number and verification code when prompted
```

#### Step 2: Replace Session in Azure File Share
```bash
# Delete old session from Azure
az storage file delete \
  --share-name telegram-sessions \
  --path telegram_trading_session.session \
  --account-name telegramint6a7207

# Upload new session
az storage file upload \
  --share-name telegram-sessions \
  --source src/session_name.session \
  --path telegram_trading_session.session \
  --account-name telegramint6a7207
```

#### Step 3: Restart Container App
```bash
# Force restart to use new session
az containerapp revision restart \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --revision $(az containerapp revision list --name telegram-trading-bot --resource-group AlgoTrading --query "[0].name" -o tsv)
```

### 3.5 Troubleshooting Session Issues

#### Check if session file exists in Azure
```bash
az storage file list \
  --share-name telegram-sessions \
  --account-name telegramint6a7207 \
  --output table
```

#### Download session from Azure for inspection
```bash
az storage file download \
  --share-name telegram-sessions \
  --path telegram_trading_session.session \
  --dest ./downloaded_session.session \
  --account-name telegramint6a7207
```

#### Common Issues and Solutions

1. **"Database is locked" error**
   - The bot automatically copies session from read-only mount to writable location
   - If issue persists, check container logs

2. **"A wait of X seconds is required" (Rate Limiting)**
   - Wait for the specified time (usually 24 hours)
   - OR generate session from a different IP/device
   - OR use an existing valid session file

3. **Session expired or invalid**
   - Generate a new session file locally
   - Replace the old session in Azure File Share
   - Restart the container app

### 3.6 Volume Mount Configuration

The Container App is configured with Azure File Share volume mount:

```json
{
  "volumes": [
    {
      "name": "telegram-sessions",
      "storageType": "AzureFile",
      "storageName": "telegram-sessions-storage"
    }
  ],
  "volumeMounts": [
    {
      "mountPath": "/app/sessions",
      "volumeName": "telegram-sessions"
    }
  ]
}
```

The bot automatically:
1. Checks for session at `/app/sessions/telegram_trading_session.session`
2. Copies it to writable location `/app/telegram_trading_session.session`
3. Uses the local copy for Telegram authentication

## Step 4: Deployment

### 4.1 Automatic Deployment
Push to `main` or `feature/telegram` branch to trigger deployment:

```bash
git add .
git commit -m "Deploy trading bot"
git push origin main
```

### 4.2 Manual Deployment via GitHub Actions
Trigger deployment manually via GitHub Actions:
1. Go to **Actions** tab in GitHub
2. Select **Deploy Telegram Trading Bot to Azure**
3. Click **Run workflow**
4. Select **deploy** action

### 4.3 Manual Docker Deployment
Deploy directly using Docker commands when GitHub Actions is unavailable:

```bash
# Build Docker image
docker build -t arunabhp/telegram-trading-bot:latest .

# Tag with timestamp
docker tag arunabhp/telegram-trading-bot:latest arunabhp/telegram-trading-bot:manual-$(date +%Y%m%d-%H%M%S)

# Push to Docker Hub
docker push arunabhp/telegram-trading-bot:latest
docker push arunabhp/telegram-trading-bot:manual-$(date +%Y%m%d-%H%M%S)

# Update Azure Container App
az containerapp update \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --image arunabhp/telegram-trading-bot:manual-$(date +%Y%m%d-%H%M%S)
```

## Step 5: Monitoring and Management

### 5.1 View Logs
```bash
# Container App logs (real-time)
az containerapp logs show \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --follow

# Container App logs (last N lines)
az containerapp logs show \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --tail 50

# Log Analytics query (if configured)
az monitor log-analytics query \
  --workspace telegram-trading-bot-logs \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'telegram-trading-bot' | order by TimeGenerated desc"
```

### 5.2 Manual Control
```bash
# Start bot manually
az containerapp update \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --min-replicas 1

# Stop bot manually  
az containerapp update \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --min-replicas 0

# Restart current revision
az containerapp revision restart \
  --name telegram-trading-bot \
  --resource-group AlgoTrading \
  --revision $(az containerapp revision list --name telegram-trading-bot --resource-group AlgoTrading --query "[0].name" -o tsv)
```

### 5.3 GitHub Actions Manual Control
Use the workflow dispatch with `stop` action to manually stop the bot.

## Scheduling Details

### Automatic Schedule
- **Start**: Monday-Friday at 8:00 AM IST (2:30 AM UTC)
- **Stop**: Monday-Friday at 4:00 PM IST (10:30 AM UTC)
- **Weekend**: Automatically scaled to 0 replicas

### Cron Expressions Used
- Start: `0 2 * * 1-5` (2:00 AM UTC, Mon-Fri)
- Stop: `0 11 * * 1-5` (11:00 AM UTC, Mon-Fri)
- Weekend: `0 11 * * 6` (Saturday 11:00 AM UTC)

## Security Features

1. **Key Vault Integration**: All secrets stored in Azure Key Vault
2. **Managed Identity**: Secure access to Azure resources
3. **RBAC**: Role-based access control
4. **Container Security**: Non-root user, minimal base image
5. **Environment Variables**: No hardcoded secrets in code

## Cost Optimization

- **Auto-scaling**: Scales to 0 when not needed
- **Resource Limits**: 0.25 CPU, 0.5 GB memory
- **Basic Registry**: Cost-effective container registry tier
- **Scheduled Operations**: Only runs during trading hours

## Troubleshooting

### Common Issues:

1. **Session Expired**: Re-generate session file locally and re-upload
2. **API Limits**: Check Telegram API rate limits
3. **Container Startup**: Check logs for environment variable issues
4. **Network Issues**: Verify firewall rules and DNS resolution

### Debug Commands:
```bash
# Check container status
az containerapp show --name telegram-trading-bot --resource-group AlgoTrading

# View recent deployments
az containerapp revision list --name telegram-trading-bot --resource-group AlgoTrading

# Check scaling rules
az containerapp show --name telegram-trading-bot --resource-group AlgoTrading --query "properties.template.scale"

# Check current revision status
az containerapp revision list --name telegram-trading-bot --resource-group AlgoTrading --query "[0].{name:name,replicas:properties.replicas,status:properties.runningStatus}" --output table
```

## Maintenance

### Regular Tasks:
1. **Monitor logs** for any errors or issues
2. **Update dependencies** in requirements.txt periodically  
3. **Rotate secrets** in Key Vault annually
4. **Review scaling metrics** to optimize costs
5. **Test deployments** in staging environment

### Updates:
1. Push code changes to trigger automatic deployment
2. Monitor deployment status in GitHub Actions
3. Verify bot functionality through logs
4. Rollback if needed using Azure Container Apps revisions

## Support

For issues or questions:
1. Check the logs first using commands above
2. Review GitHub Actions workflow runs
3. Verify Azure resource status
4. Check Telegram API status and limits