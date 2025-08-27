// Azure Bicep template for Telegram Trading Bot infrastructure
@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the container app')
param containerAppName string = 'telegram-trading-bot'

@description('Name of the container registry')
param registryName string = 'telegramtradingregistry'

@description('Telegram API credentials')
@secure()
param telegramApiId string

@secure()
param telegramApiHash string

@secure()
param telegramPhoneNumber string

@description('Trading API endpoint')
param tradingApiEndpoint string = 'https://tip-based-trading.azurewebsites.net/'

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${containerAppName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${containerAppName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Key Vault for secrets
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${containerAppName}-kv'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enableRbacAuthorization: true
  }
}

// Store secrets in Key Vault
resource telegramApiIdSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'telegram-api-id'
  properties: {
    value: telegramApiId
  }
}

resource telegramApiHashSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'telegram-api-hash'
  properties: {
    value: telegramApiHash
  }
}

resource telegramPhoneSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'telegram-phone-number'
  properties: {
    value: telegramPhoneNumber
  }
}

// User Assigned Identity for Container App
resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${containerAppName}-identity'
  location: location
}

// Role assignment for Key Vault access
resource keyVaultSecretUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, userAssignedIdentity.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'telegram-api-id'
          keyVaultUrl: telegramApiIdSecret.properties.secretUri
          identity: userAssignedIdentity.id
        }
        {
          name: 'telegram-api-hash'
          keyVaultUrl: telegramApiHashSecret.properties.secretUri
          identity: userAssignedIdentity.id
        }
        {
          name: 'telegram-phone-number'
          keyVaultUrl: telegramPhoneSecret.properties.secretUri
          identity: userAssignedIdentity.id
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: userAssignedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'telegram-trading-bot'
          image: '${containerRegistry.properties.loginServer}/${containerAppName}:latest'
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
              value: tradingApiEndpoint
            }
            {
              name: 'TELEGRAM_SESSION_NAME'
              value: 'telegram_trading_session'
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
                start: '0 8 * * 1-5'  // 8 AM Monday-Friday IST
                end: '0 16 * * 1-5'   // 4 PM Monday-Friday IST
                desiredReplicas: '1'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerAppUrl string = containerApp.properties.configuration.ingress.fqdn
output keyVaultName string = keyVault.name