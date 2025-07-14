# Script de vérification post-installation
# Auteur: Data Team
# Description: Vérifie que l'installation est complète et fonctionnelle

param(
    [switch]$Quick,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== VÉRIFICATION POST-INSTALLATION ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\verify-installation.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -Quick    Vérification rapide (sans tests de connectivité)"
    Write-Host "  -Help     Affiche cette aide"
    Write-Host ""
    Write-Host "Ce script vérifie:" -ForegroundColor White
    Write-Host "  • Présence de tous les fichiers"
    Write-Host "  • État des conteneurs Docker"
    Write-Host "  • Accessibilité des services"
    Write-Host "  • Connectivité des bases de données"
}

function Test-ServiceHealth {
    param(
        [string]$Url,
        [string]$ServiceName,
        [int]$TimeoutSeconds = 10
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Test-DatabasePort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 5
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $tcpClient.BeginConnect($HostName, $Port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne($TimeoutSeconds * 1000, $false)
        
        if ($wait) {
            $tcpClient.EndConnect($asyncResult)
            $tcpClient.Close()
            return $true
        } else {
            $tcpClient.Close()
            return $false
        }
    } catch {
        return $false
    }
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== VÉRIFICATION POST-INSTALLATION E-COMMERCE STACK ===" -ForegroundColor Green
Write-Host "Démarré le: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

$allChecks = @()
$errors = @()
$warnings = @()

# 1. Vérification des fichiers essentiels
Write-Host "📁 VÉRIFICATION DES FICHIERS" -ForegroundColor Cyan
Write-Host "=" * 50

$requiredFiles = @{
    "docker-compose-extended.yaml" = "Configuration Docker Compose"
    "start-ecommerce-stack.ps1" = "Script de démarrage"
    "stop-ecommerce-stack.ps1" = "Script d'arrêt"
    "check-ports.ps1" = "Vérification des ports"
    "diagnose-stack.ps1" = "Diagnostic de la stack"
    "GUIDE-DEMARRAGE-RAPIDE.md" = "Guide de démarrage"
    "README-ECOMMERCE-DAGS.md" = "Documentation technique"
    "dags/setup_connections.py" = "DAG de configuration"
    "dags/init_ecommerce_oltp.py" = "DAG d'initialisation"
    "dags/process_payment_csv.py" = "DAG de traitement CSV"
    "dags/sync_ecommerce_data.py" = "DAG de synchronisation"
    "dags/demo_full_pipeline.py" = "DAG de démonstration"
    "resource/payment_history.csv" = "Fichier CSV de test"
}

$fileChecksPassed = 0
foreach ($file in $requiredFiles.Keys) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
        $fileChecksPassed++
    } else {
        Write-Host "❌ $file - MANQUANT" -ForegroundColor Red
        $errors += "Fichier manquant: $file ($($requiredFiles[$file]))"
    }
}

$allChecks += [PSCustomObject]@{
    Category = "Fichiers"
    Passed = $fileChecksPassed
    Total = $requiredFiles.Count
    Status = if ($fileChecksPassed -eq $requiredFiles.Count) { "✅" } else { "❌" }
}

Write-Host ""

# 2. Vérification de Docker
Write-Host "🐳 VÉRIFICATION DE DOCKER" -ForegroundColor Cyan
Write-Host "=" * 50

$dockerChecks = 0
$dockerTotal = 2

try {
    $dockerVersion = docker version --format "{{.Server.Version}}" 2>$null
    if ($dockerVersion) {
        Write-Host "✅ Docker Server: v$dockerVersion" -ForegroundColor Green
        $dockerChecks++
    } else {
        Write-Host "❌ Docker Server non disponible" -ForegroundColor Red
        $errors += "Docker Server non disponible"
    }
} catch {
    Write-Host "❌ Docker non accessible" -ForegroundColor Red
    $errors += "Docker non accessible"
}

try {
    $composeVersion = docker-compose version --short 2>$null
    if ($composeVersion) {
        Write-Host "✅ Docker Compose: v$composeVersion" -ForegroundColor Green
        $dockerChecks++
    } else {
        Write-Host "❌ Docker Compose non disponible" -ForegroundColor Red
        $errors += "Docker Compose non disponible"
    }
} catch {
    Write-Host "❌ Docker Compose non accessible" -ForegroundColor Red
    $errors += "Docker Compose non accessible"
}

$allChecks += [PSCustomObject]@{
    Category = "Docker"
    Passed = $dockerChecks
    Total = $dockerTotal
    Status = if ($dockerChecks -eq $dockerTotal) { "✅" } else { "❌" }
}

Write-Host ""

# 3. Vérification des conteneurs
Write-Host "📦 VÉRIFICATION DES CONTENEURS" -ForegroundColor Cyan
Write-Host "=" * 50

$expectedContainers = @(
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

$runningContainers = 0
foreach ($container in $expectedContainers) {
    try {
        $status = docker ps --filter "name=$container" --format "{{.Status}}" 2>$null
        if ($status -and $status -like "*Up*") {
            Write-Host "✅ $container - En cours d'exécution" -ForegroundColor Green
            $runningContainers++
        } else {
            Write-Host "❌ $container - Non démarré" -ForegroundColor Red
            $errors += "Conteneur non démarré: $container"
        }
    } catch {
        Write-Host "❌ $container - Erreur de vérification" -ForegroundColor Red
        $errors += "Erreur de vérification pour: $container"
    }
}

$allChecks += [PSCustomObject]@{
    Category = "Conteneurs"
    Passed = $runningContainers
    Total = $expectedContainers.Count
    Status = if ($runningContainers -eq $expectedContainers.Count) { "✅" } elseif ($runningContainers -gt 0) { "🟡" } else { "❌" }
}

Write-Host ""

# 4. Vérification des services web (si pas en mode Quick)
if (-not $Quick) {
    Write-Host "🌐 VÉRIFICATION DES SERVICES WEB" -ForegroundColor Cyan
    Write-Host "=" * 50

    $webServices = @{
        "http://localhost:8090" = "Airflow UI"
        "http://localhost:8081" = "phpMyAdmin"
        "http://localhost:8082" = "pgAdmin"
    }

    $webServicesUp = 0
    foreach ($url in $webServices.Keys) {
        $serviceName = $webServices[$url]
        Write-Host "Vérification de $serviceName..." -ForegroundColor Gray
        
        if (Test-ServiceHealth -Url $url -ServiceName $serviceName -TimeoutSeconds 5) {
            Write-Host "✅ $serviceName - ACCESSIBLE" -ForegroundColor Green
            $webServicesUp++
        } else {
            Write-Host "❌ $serviceName - NON ACCESSIBLE" -ForegroundColor Red
            $warnings += "$serviceName non accessible sur $url"
        }
    }

    $allChecks += [PSCustomObject]@{
        Category = "Services Web"
        Passed = $webServicesUp
        Total = $webServices.Count
        Status = if ($webServicesUp -eq $webServices.Count) { "✅" } elseif ($webServicesUp -gt 0) { "🟡" } else { "❌" }
    }

    Write-Host ""

    # 5. Vérification des bases de données
    Write-Host "🗄️  VÉRIFICATION DES BASES DE DONNÉES" -ForegroundColor Cyan
    Write-Host "=" * 50

    $databases = @{
        "MySQL OLTP" = @{ Host = "localhost"; Port = 3307 }
        "PostgreSQL RAW" = @{ Host = "localhost"; Port = 5435 }
        "PostgreSQL Airflow" = @{ Host = "localhost"; Port = 5434 }
    }

    $dbConnections = 0
    foreach ($dbName in $databases.Keys) {
        $db = $databases[$dbName]
        Write-Host "Test de connectivité $dbName..." -ForegroundColor Gray
        
        if (Test-DatabasePort -HostName $db.Host -Port $db.Port -TimeoutSeconds 3) {
            Write-Host "✅ $dbName ($($db.Host):$($db.Port)) - ACCESSIBLE" -ForegroundColor Green
            $dbConnections++
        } else {
            Write-Host "❌ $dbName ($($db.Host):$($db.Port)) - NON ACCESSIBLE" -ForegroundColor Red
            $warnings += "$dbName non accessible sur $($db.Host):$($db.Port)"
        }
    }

    $allChecks += [PSCustomObject]@{
        Category = "Bases de Données"
        Passed = $dbConnections
        Total = $databases.Count
        Status = if ($dbConnections -eq $databases.Count) { "✅" } elseif ($dbConnections -gt 0) { "🟡" } else { "❌" }
    }

    Write-Host ""
}

# 6. Résumé final
Write-Host "📊 RÉSUMÉ DE LA VÉRIFICATION" -ForegroundColor Cyan
Write-Host "=" * 50

Write-Host "Résultats par catégorie:" -ForegroundColor White
foreach ($check in $allChecks) {
    $percentage = [math]::Round(($check.Passed / $check.Total) * 100, 1)
    Write-Host "  $($check.Status) $($check.Category): $($check.Passed)/$($check.Total) ($percentage%)" -ForegroundColor White
}

Write-Host ""

# Calcul du score global
$totalPassed = ($allChecks | Measure-Object -Property Passed -Sum).Sum
$totalChecks = ($allChecks | Measure-Object -Property Total -Sum).Sum
$globalScore = [math]::Round(($totalPassed / $totalChecks) * 100, 1)

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "🎉 INSTALLATION PARFAITE! ($globalScore%)" -ForegroundColor Green
    Write-Host ""
    Write-Host "✅ Tous les composants sont opérationnels" -ForegroundColor Green
    Write-Host "🚀 Vous pouvez commencer à utiliser la stack" -ForegroundColor Green
    Write-Host ""
    Write-Host "Prochaines étapes:" -ForegroundColor Cyan
    Write-Host "1. Accédez à Airflow: http://localhost:8090" -ForegroundColor White
    Write-Host "2. Connectez-vous avec: airflow/airflow" -ForegroundColor White
    Write-Host "3. Consultez le GUIDE-DEMARRAGE-RAPIDE.md" -ForegroundColor White
    
} elseif ($errors.Count -eq 0) {
    Write-Host "🟡 INSTALLATION FONCTIONNELLE ($globalScore%)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "⚠️  Avertissements détectés:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "   • $warning" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "💡 La stack peut fonctionner mais certains services optionnels ne sont pas accessibles" -ForegroundColor Cyan
    
} else {
    Write-Host "❌ PROBLÈMES DÉTECTÉS ($globalScore%)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🚨 Erreurs critiques:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "   • $error" -ForegroundColor Red
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  Avertissements:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "🔧 Actions recommandées:" -ForegroundColor Cyan
    Write-Host "1. Vérifiez que Docker est démarré" -ForegroundColor White
    Write-Host "2. Exécutez: .\start-ecommerce-stack.ps1 -WithAdmin" -ForegroundColor White
    Write-Host "3. Attendez 2-3 minutes et relancez cette vérification" -ForegroundColor White
    Write-Host "4. Consultez: .\diagnose-stack.ps1 pour plus de détails" -ForegroundColor White
}

Write-Host ""
Write-Host "=== FIN DE LA VÉRIFICATION ===" -ForegroundColor Green
Write-Host "Score global: $globalScore% ($totalPassed/$totalChecks vérifications réussies)" -ForegroundColor Gray