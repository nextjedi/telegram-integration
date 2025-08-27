#!/bin/bash

# Azure deployment script for Telegram Trading Bot
set -e

# Configuration
RESOURCE_GROUP="telegram-trading-rg"
LOCATION="East US"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Azure deployment for Telegram Trading Bot${NC}"

# Check if user is logged in to Azure
if ! az account show &>/dev/null; then
    echo -e "${YELLOW}⚠️  Please log in to Azure CLI first${NC}"
    az login
fi

# Set subscription if provided
if [ ! -z "$SUBSCRIPTION_ID" ]; then
    echo -e "${YELLOW}📋 Setting subscription to: $SUBSCRIPTION_ID${NC}"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Check if resource group exists
if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${YELLOW}📦 Creating resource group: $RESOURCE_GROUP${NC}"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
else
    echo -e "${GREEN}✅ Resource group $RESOURCE_GROUP already exists${NC}"
fi

# Prompt for required secrets
echo -e "${YELLOW}🔐 Please provide the required secrets:${NC}"

if [ -z "$TELEGRAM_API_ID" ]; then
    read -p "Telegram API ID: " TELEGRAM_API_ID
fi

if [ -z "$TELEGRAM_API_HASH" ]; then
    read -p "Telegram API Hash: " TELEGRAM_API_HASH
fi

if [ -z "$TELEGRAM_PHONE_NUMBER" ]; then
    read -p "Telegram Phone Number (with country code): " TELEGRAM_PHONE_NUMBER
fi

if [ -z "$TRADING_API_ENDPOINT" ]; then
    TRADING_API_ENDPOINT="https://tip-based-trading.azurewebsites.net/"
    echo "Using default Trading API Endpoint: $TRADING_API_ENDPOINT"
fi

# Deploy infrastructure using Bicep
echo -e "${YELLOW}🏗️  Deploying infrastructure...${NC}"
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "infrastructure.bicep" \
    --parameters \
        telegramApiId="$TELEGRAM_API_ID" \
        telegramApiHash="$TELEGRAM_API_HASH" \
        telegramPhoneNumber="$TELEGRAM_PHONE_NUMBER" \
        tradingApiEndpoint="$TRADING_API_ENDPOINT"

# Get deployment outputs
REGISTRY_SERVER=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "infrastructure" \
    --query "properties.outputs.containerRegistryLoginServer.value" \
    --output tsv)

KEY_VAULT_NAME=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "infrastructure" \
    --query "properties.outputs.keyVaultName.value" \
    --output tsv)

echo -e "${GREEN}✅ Infrastructure deployment completed${NC}"
echo -e "${GREEN}📋 Container Registry: $REGISTRY_SERVER${NC}"
echo -e "${GREEN}🔑 Key Vault: $KEY_VAULT_NAME${NC}"

# Instructions for GitHub Actions setup
echo -e "${YELLOW}⚡ Next steps for GitHub Actions setup:${NC}"
echo ""
echo "1. Add the following secrets to your GitHub repository:"
echo "   - AZURE_CREDENTIALS: Service principal credentials"
echo "   - AZURE_REGISTRY_USERNAME: Container registry username"
echo "   - AZURE_REGISTRY_PASSWORD: Container registry password"
echo "   - TRADING_API_ENDPOINT: $TRADING_API_ENDPOINT"
echo "   - BTST_CHANNEL_ID, DAYTRADE_CHANNEL_ID, UNIVEST_CHANNEL_ID"
echo ""
echo "2. Get registry credentials:"
echo "   az acr credential show --name telegramtradingregistry"
echo ""
echo "3. Create service principal:"
echo "   az ad sp create-for-rbac --name 'telegram-trading-sp' \\"
echo "     --role contributor \\"
echo "     --scopes /subscriptions/\$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \\"
echo "     --sdk-auth"
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"