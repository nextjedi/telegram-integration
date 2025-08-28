#!/bin/bash

# Azure Container Apps Logs Checker
echo "🔍 Checking Azure Container Apps logs..."
echo "======================================"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed."
    exit 1
fi

# Login check
echo "🔐 Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "Please login to Azure first: az login"
    exit 1
fi

APP_NAME="telegram-trading-bot"
RESOURCE_GROUP="AlgoTrading"

echo "📱 App Name: $APP_NAME"
echo "📦 Resource Group: $RESOURCE_GROUP"
echo ""

# Check app status
echo "📊 Checking app status..."
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{name:name,status:properties.provisioningState,replicas:properties.configuration.activeRevisionsMode}" \
  --output table

echo ""

# Get current replicas
echo "🔄 Current replica status..."
az containerapp replica list \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "[].{name:name,status:properties.runningState,created:properties.createdTime}" \
  --output table

echo ""

# Get recent logs (last 1 hour)
echo "📋 Recent logs (last 1 hour)..."
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow false \
  --tail 50

echo ""
echo "✅ Use this command to follow live logs:"
echo "az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"