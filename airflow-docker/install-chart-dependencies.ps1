#!/usr/bin/env pwsh

Write-Host "=== INSTALLATION DES DÉPENDANCES POUR GRAPHIQUES ===" -ForegroundColor Green
Write-Host ""

# Vérifier que Docker est en cours d'exécution
try {
    docker version | Out-Null
    Write-Host "✅ Docker est disponible" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker n'est pas disponible ou n'est pas démarré" -ForegroundColor Red
    exit 1
}

# Vérifier que les conteneurs Airflow sont en cours d'exécution
$containers = docker ps --format "table {{.Names}}" | Select-String "airflow"
if ($containers.Count -eq 0) {
    Write-Host "❌ Aucun conteneur Airflow en cours d'exécution" -ForegroundColor Red
    Write-Host "Démarrez d'abord la stack avec: .\start-ecommerce-stack.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "📦 Installation des dépendances Python pour les graphiques..." -ForegroundColor Cyan

# Liste des packages à installer
$packages = @(
    "matplotlib==3.7.2",
    "seaborn==0.12.2", 
    "pandas==2.0.3",
    "numpy==1.24.3"
)

# Conteneurs Airflow où installer les packages
$airflow_containers = @(
    "airflow-docker-airflow-scheduler-1",
    "airflow-docker-airflow-webserver-1",
    "airflow-docker-airflow-worker-1"
)

foreach ($container in $airflow_containers) {
    # Vérifier si le conteneur existe
    $container_exists = docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$container$"
    
    if ($container_exists) {
        Write-Host "🔧 Installation dans $container..." -ForegroundColor Yellow
        
        foreach ($package in $packages) {
            Write-Host "  📦 Installation de $package..." -ForegroundColor Gray
            
            try {
                $result = docker exec $container pip install $package 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    ✅ $package installé avec succès" -ForegroundColor Green
                } else {
                    Write-Host "    ⚠️ Problème avec $package : $result" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "    ❌ Erreur lors de l'installation de $package" -ForegroundColor Red
            }
        }
        
        Write-Host "✅ Installation terminée pour $container" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "⚠️ Conteneur $container non trouvé" -ForegroundColor Yellow
    }
}

# Vérifier l'installation
Write-Host "🔍 Vérification de l'installation..." -ForegroundColor Cyan

$test_script = @"
import sys
try:
    import matplotlib
    import seaborn
    import pandas
    import numpy
    print('✅ Tous les packages sont installés')
    print(f'matplotlib: {matplotlib.__version__}')
    print(f'seaborn: {seaborn.__version__}')
    print(f'pandas: {pandas.__version__}')
    print(f'numpy: {numpy.__version__}')
except ImportError as e:
    print(f'❌ Erreur d\'importation: {e}')
    sys.exit(1)
"@

try {
    $verification = docker exec airflow-docker-airflow-scheduler-1 python -c $test_script
    Write-Host $verification -ForegroundColor Green
} catch {
    Write-Host "❌ Erreur lors de la vérification" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎨 Configuration matplotlib pour environnement headless..." -ForegroundColor Cyan

# Configurer matplotlib pour fonctionner sans display
$matplotlib_config = @"
import matplotlib
matplotlib.use('Agg')  # Backend sans interface graphique
import matplotlib.pyplot as plt
plt.ioff()  # Mode non-interactif
print('✅ Matplotlib configuré pour environnement headless')
"@

try {
    $config_result = docker exec airflow-docker-airflow-scheduler-1 python -c $matplotlib_config
    Write-Host $config_result -ForegroundColor Green
} catch {
    Write-Host "⚠️ Problème de configuration matplotlib" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔄 Redémarrage des services Airflow..." -ForegroundColor Cyan

# Redémarrer les services pour prendre en compte les nouvelles dépendances
try {
    docker-compose -f docker-compose-extended.yaml restart airflow-scheduler airflow-webserver airflow-worker 2>$null
    Write-Host "✅ Services Airflow redémarrés" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Problème lors du redémarrage des services" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== INSTALLATION TERMINÉE ===" -ForegroundColor Green
Write-Host "Les dépendances pour les graphiques sont maintenant installées." -ForegroundColor White
Write-Host "Vous pouvez maintenant utiliser le DAG 'create_region_chart'." -ForegroundColor White
Write-Host ""