// ============================================================================
// Azure Infrastructure as Code (Bicep) - STAGING Environment
// Phase 4: Staging Deployment
// Date: 26/02/2026
// ============================================================================

// ============================================================================
// PARAMETROS DE ENTRADA
// ============================================================================

@minLength(1)
@maxLength(11)
param environment string = 'staging'

@description('Prefixo para recurso naming')
param projectName string = 'operador-dt'

@description('Localizacao Azure')
param location string = resourceGroup().location

@description('Tags para recursos')
param tags object = {
  Project: 'operador-day-trade'
  Phase: 'Phase4-Staging'
  Environment: 'staging'
  CreatedDate: '2026-02-26'
  Owner: 'Engineering Team'
  CostCenter: 'Trading Operations'
}

// ============================================================================
// VARIAVEIS DERIVADAS
// ============================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)
var resourceNamePrefix = '${projectName}-${environment}'
var appServicePlanName = '${resourceNamePrefix}-asp'
var appServiceName = '${resourceNamePrefix}-app'
var postgresqlServerName = '${resourceNamePrefix}-db-${uniqueSuffix}'
var redisName = '${resourceNamePrefix}-cache'
var appInsightsName = '${resourceNamePrefix}-insights'
var storageAccountName = '${resourceNamePrefix}${uniqueSuffix}'.replace('-', '')
var keyVaultName = '${resourceNamePrefix}-kv-${uniqueSuffix}'
var nsgName = '${resourceNamePrefix}-nsg'

// ============================================================================
// NETWORKING - Network Security Group
// ============================================================================

resource nsg 'Microsoft.Network/networkSecurityGroups@2021-02-01' = {
  name: nsgName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHTTP'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHTTPS'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 101
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowWebSocket'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '8000'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 102
          direction: 'Inbound'
        }
      }
    ]
  }
}

// ============================================================================
// STORAGE - Azure Storage Account (para modelos ML + backups)
// ============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2021-04-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    encryption: {
      services: {
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource storageBlob 'Microsoft.Storage/storageAccounts/blobServices@2021-04-01' = {
  parent: storageAccount
  name: 'default'
}

resource storageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-04-01' = {
  parent: storageBlob
  name: 'ml-models'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// KEY VAULT - Armazenamento de Secrets
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2019-09-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    enabledForDeployment: true
    enabledForDiskEncryption: true
    enabledForTemplateDeployment: true
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
  }
}

// ============================================================================
// MONITORING - Application Insights
// ============================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 90
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ============================================================================
// CACHING - Azure Cache for Redis
// ============================================================================

resource redisCache 'Microsoft.Cache/redis@2021-06-01' = {
  name: redisName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 1  // 1GB para staging
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// ============================================================================
// DATABASE - Azure Database for PostgreSQL
// ============================================================================

resource postgresqlServer 'Microsoft.DBforPostgreSQL/servers@2017-12-01' = {
  name: postgresqlServerName
  location: location
  tags: tags
  sku: {
    name: 'B_Gen5_2'  // Basic, 2 vCores para staging
    tier: 'Basic'
    capacity: 2
    family: 'Gen5'
  }
  kind: 'v10.0'
  properties: {
    createMode: 'Default'
    version: '10.0'
    administratorLogin: 'adminuser'
    administratorLoginPassword: 'Staging@2026#Secure'  // NOTE: Should use Key Vault in production
    storageProfile: {
      storageMB: 51200  // 50GB
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    sslEnforcement: 'ENABLED'
    infrastructureEncryption: 'Disabled'
    publicNetworkAccess: 'Enabled'
  }
}

// Firewalls de banco de dados
resource postgresqlFirewall 'Microsoft.DBforPostgreSQL/servers/firewallRules@2017-12-01' = {
  parent: postgresqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource postgresqlFirewall2 'Microsoft.DBforPostgreSQL/servers/firewallRules@2017-12-01' = {
  parent: postgresqlServer
  name: 'AllowLocalDev'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'  // Staging: abrir para dev - restrict em prod
  }
}

// ============================================================================
// COMPUTE - App Service Plan + Web App
// ============================================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2021-01-15' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'B1'  // Basic B1 para staging (compartilhado)
    tier: 'Basic'
    size: 'B1'
    family: 'B'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource appService 'Microsoft.Web/sites@2021-01-15' = {
  name: appServiceName
  location: location
  tags: tags
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    reserved: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/appsvc/python:3.11'
      alwaysOn: true
      http20Enabled: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'
        }
        {
          name: 'XDT_MicrosoftApplicationInsights_Mode'
          value: 'recommended'
        }
        {
          name: 'ENVIRONMENT'
          value: 'staging'
        }
        {
          name: 'LOG_LEVEL'
          value: 'INFO'
        }
        {
          name: 'DATABASE_URL'
          value: 'postgresql://adminuser:Staging@2026#Secure@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/operador_db'
        }
        {
          name: 'REDIS_URL'
          value: 'redis://:${redisCache.listKeys().primaryKey}@${redisCache.properties.hostName}:6380?ssl=True'
        }
        {
          name: 'STORAGE_ACCOUNT_URL'
          value: storageAccount.properties.primaryEndpoints.blob
        }
      ]
      connectionStrings: [
        {
          name: 'PostgreSQL'
          connectionString: 'postgresql://adminuser:Staging@2026#Secure@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/operador_db'
          type: 'PostgreSQL'
        }
        {
          name: 'Redis'
          connectionString: '${redisCache.properties.hostName}:6380,password=${redisCache.listKeys().primaryKey},ssl=True'
          type: 'Custom'
        }
      ]
      healthCheckPath: '/health'
      numberOfWorkers: 1
    }
  }
}

// HTTPS apenas (redirecionar HTTP)
resource appServiceHttps 'Microsoft.Web/sites/config@2021-01-15' = {
  parent: appService
  name: 'web'
  properties: {
    httpLoggingEnabled: true
    detailedErrorLoggingEnabled: true
    requestTracingEnabled: true
    requestTracingExpirationTime: '2026-03-10T00:00:00Z'
  }
}

// ============================================================================
// OUTPUTS - Valores para uso posterior
// ============================================================================

output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output postgresqlHost string = postgresqlServer.properties.fullyQualifiedDomainName
output postgresqlPort int = 5432
output postgesqlDatabase string = 'operador_db'
output redisHost string = redisCache.properties.hostName
output redisPort int = 6380
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output storageAccountName string = storageAccount.name
output keyVaultUri string = keyVault.properties.vaultUri
output resourceGroupName string = resourceGroup().name
output resourceGroupId string = resourceGroup().id

// ============================================================================
// NOTAS IMPORTANTES:
// ============================================================================
// 1. Senhas hardcoded - usar Azure Key Vault em produção
// 2. Firewall PostgreSQL aberto para dev - restrict em produção
// 3. App Service B1 Basic - scale up para Standard/Premium em produção
// 4. Backup retention 7 dias - aumentar para 30+ em produção
// 5. Executar: az deployment group create --resource-group staging-rg --template-file staging.bicep
// ============================================================================
