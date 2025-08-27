// Minimal deployment for Telegram Trading Bot using existing AlgoTrading resources
@description('Location for resources')
param location string = 'southindia'

@description('Docker Hub repository')
param dockerHubRepo string = 'your-dockerhub-username/telegram-trading-bot'

@description('Telegram API credentials')
@secure()
param telegramApiId string = 'placeholder'
@secure()
param telegramApiHash string = 'placeholder'
@secure()
param telegramPhoneNumber string = 'placeholder'

// Reference existing resources
resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: 'algo-secrets'
}

// Create new Container Apps Environment in South India
resource newContainerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'telegram-trading-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

// Create secrets in existing Key Vault
resource telegramApiIdSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: existingKeyVault
  name: 'telegram-api-id'
  properties: {
    value: telegramApiId
  }
}

resource telegramApiHashSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: existingKeyVault
  name: 'telegram-api-hash'
  properties: {
    value: telegramApiHash
  }
}

resource telegramPhoneSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: existingKeyVault
  name: 'telegram-phone-number'
  properties: {
    value: telegramPhoneNumber
  }
}

// Create User Assigned Identity
resource botIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'telegram-trading-identity'
  location: location
}

// Key Vault access for the identity
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingKeyVault.id, botIdentity.id, 'Key Vault Secrets User')
  scope: existingKeyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: botIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Container App
resource telegramTradingApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'telegram-trading-bot'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${botIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: newContainerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'telegram-api-id'
          keyVaultUrl: telegramApiIdSecret.properties.secretUri
          identity: botIdentity.id
        }
        {
          name: 'telegram-api-hash'
          keyVaultUrl: telegramApiHashSecret.properties.secretUri
          identity: botIdentity.id
        }
        {
          name: 'telegram-phone-number'
          keyVaultUrl: telegramPhoneSecret.properties.secretUri
          identity: botIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'telegram-trading-bot'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
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
              value: 'https://tip-based-trading.azurewebsites.net/'
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
    }
  }
  dependsOn: [
    keyVaultRoleAssignment
  ]
}

output containerAppFqdn string = telegramTradingApp.properties.latestRevisionFqdn
output identityClientId string = botIdentity.properties.clientId