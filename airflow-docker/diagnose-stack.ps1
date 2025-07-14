# Script PowerShell de diagnostic pour la stack e-commerce
# Auteur: Data Team
# Description: Diagnostic complet de l'état de la stack

param(
    [switch]$Detailed,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== DIAGNOSTIC DE LA STACK E-COMMERCE ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\diagnose-stack.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -Detailed    Affichage détaillé avec logs"
    Write-Host "  -Help        Affiche cette aide"
    Write-Host ""
    Write-Host "Ce script vérifie:" -ForegroundColor White
    Write-Host "  • État de Docker"
    Write-Host "  • Disponibilité des ports"
    Write-Host "  • État des conteneurs"
    Write-Host "  • Santé des services"
    Write-Host "  • Connectivité des bases de données"
}

function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-ContainerStatus {
    param([string]$ContainerName)
    try {
        $status = docker ps -a --filter "name=$ContainerName" --format "{{.Status}}" 2>$null
        if ($status) {
            return $status
        } else {
            return "Non trouvé"
        }
    } catch {
        return "Erreur"
    }
}

function Test-DatabaseConnection {
    param(
        [string]$Type,
        [string]$HostName,
        [int]$Port,
        [string]$User,
        [string]$Password,
        [string]$Database
    )
    
    try {
        if ($Type -eq "MySQL") {
            # Test simple de connexion TCP
            $tcpTest = Test-Port -Port $Port
            return $tcpTest
        } elseif ($Type -eq "PostgreSQL") {
            # Test simple de connexion TCP
            $tcpTest = Test-Port -Port $Port
            return $tcpTest
        }
        return $false
    } catch {
        return $false
    }
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== DIAGNOSTIC DE LA STACK E-COMMERCE ===" -ForegroundColor Green
Write-Host "Généré le: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# 1. Vérification de Docker
Write-Host "🐳 VÉRIFICATION DE DOCKER" -ForegroundColor Cyan
Write-Host "=" * 50

try {
    $dockerVersion = docker version --format "{{.Server.Version}}" 2>$null
    if ($dockerVersion) {
        Write-Host "✅ Docker Server: v$dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker Server non disponible" -ForegroundColor Red
    }
    
    $dockerComposeVersion = docker-compose version --short 2>$null
    if ($dockerComposeVersion) {
        Write-Host "✅ Docker Compose: v$dockerComposeVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker Compose non disponible" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Docker non disponible" -ForegroundColor Red
}

Write-Host ""

# 2. Vérification des ports
Write-Host "🔌 VÉRIFICATION DES PORTS" -ForegroundColor Cyan
Write-Host "=" * 50

$ports = @{
    8090 = "Airflow UI"
    3307 = "MySQL OLTP"
    5435 = "PostgreSQL RAW"
    5434 = "PostgreSQL Airflow"
    6379 = "Redis"
    8081 = "phpMyAdmin"
    8082 = "pgAdmin"
    5555 = "Flower"
}

$portStatus = @{}
foreach ($port in $ports.Keys) {
    $isUsed = Test-Port -Port $port
    $portStatus[$port] = $isUsed
    
    if ($isUsed) {
        Write-Host "🟡 Port $port ($($ports[$port])) - OCCUPÉ" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Port $port ($($ports[$port])) - DISPONIBLE" -ForegroundColor Green
    }
}

Write-Host ""

# 3. État des conteneurs
Write-Host "📦 ÉTAT DES CONTENEURS" -ForegroundColor Cyan
Write-Host "=" * 50

$containers = @(
    "airflow-apiserver",
    "airflow-scheduler",
    "airflow-worker",
    "airflow-dag-processor",
    "airflow-triggerer",
    "mysql_ops_db",
    "postgres_raw_db",
    "postgres",
    "redis"
)

$containerStatus = @{}
foreach ($container in $containers) {
    $status = Get-ContainerStatus -ContainerName $container
    $containerStatus[$container] = $status
    
    if ($status -like "*Up*") {
        Write-Host "✅ $container - $status" -ForegroundColor Green
    } elseif ($status -like "*Exited*") {
        Write-Host "❌ $container - $status" -ForegroundColor Red
    } elseif ($status -eq "Non trouvé") {
        Write-Host "⚪ $container - Non démarré" -ForegroundColor Gray
    } else {
        Write-Host "🟡 $container - $status" -ForegroundColor Yellow
    }
}

Write-Host ""

# 4. Test de connectivité des bases de données
Write-Host "🗄️  CONNECTIVITÉ DES BASES DE DONNÉES" -ForegroundColor Cyan
Write-Host "=" * 50

$databases = @{
    "MySQL OLTP" = @{
        Type = "MySQL"
        Host = "localhost"
        Port = 3307
        User = "root"
        Password = "root_password"
        Database = "ecommerce_ops_db"
    }
    "PostgreSQL RAW" = @{
        Type = "PostgreSQL"
        Host = "localhost"
        Port = 5435
        User = "postgres"
        Password = "postgres_password"
        Database = "ecommerce_raw_db"
    }
    "PostgreSQL Airflow" = @{
        Type = "PostgreSQL"
        Host = "localhost"
        Port = 5434
        User = "airflow"
        Password = "airflow"
        Database = "airflow"
    }
}

foreach ($dbName in $databases.Keys) {
    $db = $databases[$dbName]
    $isConnectable = Test-DatabaseConnection -Type $db.Type -HostName $db.Host -Port $db.Port -User $db.User -Password $db.Password -Database $db.Database
    
    if ($isConnectable) {
        Write-Host "✅ $dbName ($($db.Host):$($db.Port)) - ACCESSIBLE" -ForegroundColor Green
    } else {
        Write-Host "❌ $dbName ($($db.Host):$($db.Port)) - NON ACCESSIBLE" -ForegroundColor Red
    }
}

Write-Host ""

# 5. Vérification des fichiers
Write-Host "📁 VÉRIFICATION DES FICHIERS" -ForegroundColor Cyan
Write-Host "=" * 50

$requiredFiles = @(
    "docker-compose-extended.yaml",
    "dags/setup_connections.py",
    "dags/init_ecommerce_oltp.py",
    "dags/process_payment_csv.py",
    "dags/sync_ecommerce_data.py",
    "resource/payment_history.csv"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file - PRÉSENT" -ForegroundColor Green
    } else {
        Write-Host "❌ $file - MANQUANT" -ForegroundColor Red
    }
}

Write-Host ""

# 6. Résumé et recommandations
Write-Host "📋 RÉSUMÉ ET RECOMMANDATIONS" -ForegroundColor Cyan
Write-Host "=" * 50

$issues = @()
$warnings = @()

# Analyser les résultats
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $issues += "Docker n'est pas installé ou pas dans le PATH"
}

$runningContainers = ($containerStatus.Values | Where-Object { $_ -like "*Up*" }).Count
$totalContainers = $containers.Count

if ($runningContainers -eq 0) {
    $issues += "Aucun conteneur n'est en cours d'exécution"
} elseif ($runningContainers -lt $totalContainers) {
    $warnings += "$runningContainers/$totalContainers conteneurs en cours d'exécution"
}

$criticalPortsOccupied = @(8090, 3307, 5435, 5434, 6379) | Where-Object { $portStatus[$_] -eq $true }
if ($criticalPortsOccupied.Count -gt 0) {
    $warnings += "Ports critiques occupés: $($criticalPortsOccupied -join ', ')"
}

# Afficher le résumé
if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "🎉 TOUT SEMBLE FONCTIONNER CORRECTEMENT!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Prochaines étapes:" -ForegroundColor White
    Write-Host "1. Accédez à Airflow: http://localhost:8090" -ForegroundColor Gray
    Write-Host "2. Connectez-vous avec: airflow/airflow" -ForegroundColor Gray
    Write-Host "3. Exécutez les DAGs dans l'ordre recommandé" -ForegroundColor Gray
} else {
    if ($issues.Count -gt 0) {
        Write-Host "🚨 PROBLÈMES CRITIQUES:" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "   • $issue" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "⚠️  AVERTISSEMENTS:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
        Write-Host ""
    }
    
    Write-Host "🔧 ACTIONS RECOMMANDÉES:" -ForegroundColor Cyan
    if ($runningContainers -eq 0) {
        Write-Host "   1. Démarrez la stack: .\start-ecommerce-stack.ps1" -ForegroundColor White
    }
    if ($criticalPortsOccupied.Count -gt 0) {
        Write-Host "   2. Libérez les ports occupés ou modifiez la configuration" -ForegroundColor White
    }
    Write-Host "   3. Consultez les logs: docker-compose -f docker-compose-extended.yaml logs" -ForegroundColor White
}

# Affichage détaillé si demandé
if ($Detailed) {
    Write-Host ""
    Write-Host "🔍 INFORMATIONS DÉTAILLÉES" -ForegroundColor Cyan
    Write-Host "=" * 50
    
    Write-Host "Conteneurs Docker:" -ForegroundColor White
    try {
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    } catch {
        Write-Host "Impossible d'obtenir la liste des conteneurs" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Volumes Docker:" -ForegroundColor White
    try {
        docker volume ls --format "table {{.Name}}\t{{.Driver}}" 2>$null
    } catch {
        Write-Host "Impossible d'obtenir la liste des volumes" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== FIN DU DIAGNOSTIC ===" -ForegroundColor Green
Write-Host "Pour plus d'aide, consultez README-ECOMMERCE-DAGS.md" -ForegroundColor Gray