# Script PowerShell pour démarrer la stack e-commerce avec Airflow
# Auteur: Data Team
# Description: Démarre tous les services nécessaires pour le projet e-commerce

param(
    [switch]$WithAdmin,
    [switch]$WithFlower,
    [switch]$Clean,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== SCRIPT DE DÉMARRAGE E-COMMERCE STACK ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\start-ecommerce-stack.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -WithAdmin    Démarre phpMyAdmin et pgAdmin pour l'administration des bases"
    Write-Host "  -WithFlower   Démarre Flower pour le monitoring Celery"
    Write-Host "  -Clean        Nettoie les volumes Docker avant le démarrage"
    Write-Host "  -Help         Affiche cette aide"
    Write-Host ""
    Write-Host "Exemples:" -ForegroundColor Magenta
    Write-Host "  .\start-ecommerce-stack.ps1                    # Démarrage standard"
    Write-Host "  .\start-ecommerce-stack.ps1 -WithAdmin         # Avec outils d'admin"
    Write-Host "  .\start-ecommerce-stack.ps1 -Clean -WithAdmin  # Nettoyage + admin"
    Write-Host ""
    Write-Host "Services démarrés:" -ForegroundColor White
    Write-Host "  - Airflow (http://localhost:8090) - airflow/airflow"
    Write-Host "  - MySQL OLTP (localhost:3307) - root/root_password"
    Write-Host "  - PostgreSQL RAW (localhost:5435) - postgres/postgres_password"
    Write-Host "  - Redis (localhost:6379)"
    Write-Host ""
    Write-Host "Services optionnels:" -ForegroundColor White
    Write-Host "  - phpMyAdmin (http://localhost:8081) - avec -WithAdmin"
    Write-Host "  - pgAdmin (http://localhost:8082) - admin@example.com/admin - avec -WithAdmin"
    Write-Host "  - Flower (http://localhost:5555) - avec -WithFlower"
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== DÉMARRAGE DE LA STACK E-COMMERCE ===" -ForegroundColor Green

# Vérifier la disponibilité des ports critiques
Write-Host "🔍 Vérification des ports..." -ForegroundColor Yellow
$criticalPorts = @{
    8090 = "Airflow UI"
    3307 = "MySQL OLTP"
    5435 = "PostgreSQL RAW"
    5434 = "PostgreSQL Airflow"
    6379 = "Redis"
}

$portConflicts = @()
foreach ($port in $criticalPorts.Keys) {
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $port)
        $connection.Close()
        $portConflicts += "$port ($($criticalPorts[$port]))"
    } catch {
        # Port disponible
    }
}

if ($portConflicts.Count -gt 0) {
    Write-Host "❌ PORTS OCCUPÉS DÉTECTÉS:" -ForegroundColor Red
    foreach ($conflict in $portConflicts) {
        Write-Host "   Port $conflict" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "💡 Solutions:" -ForegroundColor Yellow
    Write-Host "   1. Exécutez .\check-ports.ps1 pour plus de détails" -ForegroundColor White
    Write-Host "   2. Arrêtez les services utilisant ces ports" -ForegroundColor White
    Write-Host "   3. Ou modifiez les ports dans docker-compose-extended.yaml" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Voulez-vous continuer malgré tout? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Démarrage annulé." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ Tous les ports critiques sont disponibles" -ForegroundColor Green
}

# Vérifier que Docker est en cours d'exécution
try {
    docker version | Out-Null
    Write-Host "✓ Docker est disponible" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker n'est pas disponible ou n'est pas démarré" -ForegroundColor Red
    Write-Host "Veuillez démarrer Docker Desktop et réessayer." -ForegroundColor Yellow
    exit 1
}

# Vérifier que docker-compose est disponible
try {
    docker-compose version | Out-Null
    Write-Host "✓ Docker Compose est disponible" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose n'est pas disponible" -ForegroundColor Red
    exit 1
}

# Nettoyer les volumes si demandé
if ($Clean) {
    Write-Host "🧹 Nettoyage des volumes Docker..." -ForegroundColor Yellow
    docker-compose -f docker-compose-extended.yaml down -v
    docker volume prune -f
    Write-Host "✓ Nettoyage terminé" -ForegroundColor Green
}

# Créer les répertoires nécessaires
$directories = @("logs", "plugins", "config", "resource")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✓ Répertoire $dir créé" -ForegroundColor Green
    }
}

# Créer le fichier .env si il n'existe pas
if (!(Test-Path ".env")) {
    Write-Host "📝 Création du fichier .env..." -ForegroundColor Yellow
    @"
AIRFLOW_UID=50000
AIRFLOW_PROJ_DIR=.
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
_PIP_ADDITIONAL_REQUIREMENTS=apache-airflow-providers-mysql apache-airflow-providers-postgres pandas
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ Fichier .env créé" -ForegroundColor Green
}

# Construire la commande docker-compose
$profiles = @()
if ($WithAdmin) {
    $profiles += "admin"
    Write-Host "🔧 Mode administrateur activé" -ForegroundColor Cyan
}
if ($WithFlower) {
    $profiles += "flower"
    Write-Host "🌸 Flower monitoring activé" -ForegroundColor Cyan
}

$composeCommand = "docker-compose -f docker-compose-extended.yaml"
if ($profiles.Count -gt 0) {
    $profilesStr = $profiles -join ","
    $composeCommand += " --profile $profilesStr"
}

Write-Host "🚀 Démarrage des services..." -ForegroundColor Yellow
Write-Host "Commande: $composeCommand up -d" -ForegroundColor Gray

# Démarrer les services
Invoke-Expression "$composeCommand up -d"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ STACK DÉMARRÉE AVEC SUCCÈS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Services disponibles:" -ForegroundColor Cyan
    Write-Host "  • Airflow UI: http://localhost:8090 (airflow/airflow)" -ForegroundColor White
    Write-Host "  • MySQL OLTP: localhost:3307 (root/root_password)" -ForegroundColor White
    Write-Host "  • PostgreSQL RAW: localhost:5435 (postgres/postgres_password)" -ForegroundColor White
    
    if ($WithAdmin) {
        Write-Host "  • phpMyAdmin: http://localhost:8081" -ForegroundColor White
        Write-Host "  • pgAdmin: http://localhost:8082 (admin@example.com/admin)" -ForegroundColor White
    }
    
    if ($WithFlower) {
        Write-Host "  • Flower: http://localhost:5555" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "📋 Prochaines étapes:" -ForegroundColor Yellow
    Write-Host "  1. Attendez que tous les services soient prêts (2-3 minutes)"
    Write-Host "  2. Accédez à Airflow: http://localhost:8090"
    Write-Host "  3. Exécutez le DAG 'setup_connections' pour configurer les connexions"
    Write-Host "  4. Exécutez le DAG 'init_ecommerce_oltp' pour initialiser les données"
    Write-Host "  5. Lancez le DAG 'process_payment_csv' pour traiter le CSV"
    Write-Host ""
    Write-Host "🔍 Pour voir les logs: docker-compose -f docker-compose-extended.yaml logs -f" -ForegroundColor Gray
    Write-Host "🛑 Pour arrêter: docker-compose -f docker-compose-extended.yaml down" -ForegroundColor Gray
    
} else {
    Write-Host ""
    Write-Host "❌ ERREUR LORS DU DÉMARRAGE" -ForegroundColor Red
    Write-Host "Vérifiez les logs avec: docker-compose -f docker-compose-extended.yaml logs" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== FIN DU SCRIPT ===" -ForegroundColor Green