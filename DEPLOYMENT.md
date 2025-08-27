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

The Telegram session file needs to be created once and stored securely:

### 3.1 Generate Session Locally
```bash
# Run locally first to generate session
python src/telegram_bot.py
# This will prompt for phone number and verification code
```

### 3.2 Upload Session to Azure (Manual Step)
The session file (`telegram_trading_session.session`) should be uploaded to Azure Key Vault or Container App persistent storage.

## Step 4: Deployment

### 4.1 Automatic Deployment
Push to `main` or `feature/telegram` branch to trigger deployment:

```bash
git add .
git commit -m "Deploy trading bot"
git push origin main
```

### 4.2 Manual Deployment
Trigger deployment manually via GitHub Actions:
1. Go to **Actions** tab in GitHub
2. Select **Deploy Telegram Trading Bot to Azure**
3. Click **Run workflow**
4. Select **deploy** action

## Step 5: Monitoring and Management

### 5.1 View Logs
```bash
# Container App logs
az containerapp logs show \
  --name telegram-trading-bot \
  --resource-group telegram-trading-rg \
  --follow

# Log Analytics query
az monitor log-analytics query \
  --workspace telegram-trading-bot-logs \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'telegram-trading-bot' | order by TimeGenerated desc"
```

### 5.2 Manual Control
```bash
# Start bot manually
az containerapp update \
  --name telegram-trading-bot \
  --resource-group telegram-trading-rg \
  --min-replicas 1

# Stop bot manually  
az containerapp update \
  --name telegram-trading-bot \
  --resource-group telegram-trading-rg \
  --min-replicas 0
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
az containerapp show --name telegram-trading-bot --resource-group telegram-trading-rg

# View recent deployments
az containerapp revision list --name telegram-trading-bot --resource-group telegram-trading-rg

# Check scaling rules
az containerapp show --name telegram-trading-bot --resource-group telegram-trading-rg --query "properties.template.scale"
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