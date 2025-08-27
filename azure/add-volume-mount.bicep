// Update Container App with Azure Files volume mount
param containerAppName string = 'telegram-trading-bot'
param location string = 'South India'
param storageAccountName string = 'telegramint6a7207'
param fileShareName string = 'telegram-sessions'
param storageAccountKey string

// Reference existing container app
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: '/subscriptions/a15f2ab5-5512-4e0e-a5e4-16a529fef591/resourceGroups/AlgoTrading/providers/Microsoft.App/managedEnvironments/telegram-trading-env'
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'telegram-api-id'
          keyVaultUrl: 'https://algo-secrets.vault.azure.net/secrets/telegram-api-id'
          identity: '/subscriptions/a15f2ab5-5512-4e0e-a5e4-16a529fef591/resourcegroups/AlgoTrading/providers/Microsoft.ManagedIdentity/userAssignedIdentities/telegram-trading-identity'
        }
        {
          name: 'telegram-api-hash'
          keyVaultUrl: 'https://algo-secrets.vault.azure.net/secrets/telegram-api-hash'
          identity: '/subscriptions/a15f2ab5-5512-4e0e-a5e4-16a529fef591/resourcegroups/AlgoTrading/providers/Microsoft.ManagedIdentity/userAssignedIdentities/telegram-trading-identity'
        }
        {
          name: 'telegram-phone-number'
          keyVaultUrl: 'https://algo-secrets.vault.azure.net/secrets/telegram-phone-number'
          identity: '/subscriptions/a15f2ab5-5512-4e0e-a5e4-16a529fef591/resourcegroups/AlgoTrading/providers/Microsoft.ManagedIdentity/userAssignedIdentities/telegram-trading-identity'
        }
        {
          name: 'storage-account-key'
          value: storageAccountKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'telegram-trading-bot'
          image: 'arunabhp/telegram-trading-bot:manual-deploy-20250827-151305'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'TELEGRAM_API_ID'
              secretRef: 'telegram-api-id'
            }
            {
              name: 'TELEGRAM_API_HASH'
              secretRef: 'telegram-api-hash'
            }
            {
              name: 'TELEGRAM_PHONE_NUMBER'
              secretRef: 'telegram-phone-number'
            }
            {
              name: 'TRADING_API_ENDPOINT'
              value: 'https://tip-based-trading.azurewebsites.net/tip'
            }
            {
              name: 'TELEGRAM_SESSION_NAME'
              value: 'telegram_trading_session'
            }
            {
              name: 'BTST_CHANNEL_ID'
              value: '-1001552501322'
            }
            {
              name: 'DAYTRADE_CHANNEL_ID'
              value: '-1001752927494'
            }
            {
              name: 'UNIVEST_CHANNEL_ID'
              value: '-1001983880498'
            }
          ]
          volumeMounts: [
            {
              mountPath: '/app/sessions'
              volumeName: 'telegram-sessions'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [
          {
            name: 'trading-hours'
            custom: {
              type: 'cron'
              metadata: {
                timezone: 'Asia/Kolkata'
                start: '0 8 * * 1-5'
                end: '0 16 * * 1-5'
                desiredReplicas: '1'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'telegram-sessions'
          storageType: 'AzureFile'
          storageName: 'telegram-sessions-storage'
        }
      ]
    }
  }
}

// Storage for Container Apps Environment
resource managedEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: 'telegram-trading-env'
  resource storage 'storages@2023-05-01' = {
    name: 'telegram-sessions-storage'
    properties: {
      azureFile: {
        accountName: storageAccountName
        accountKey: storageAccountKey
        shareName: fileShareName
        accessMode: 'ReadWrite'
      }
    }
  }
}