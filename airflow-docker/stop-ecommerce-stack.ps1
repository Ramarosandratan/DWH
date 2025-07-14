# Script PowerShell pour arrêter la stack e-commerce avec Airflow
# Auteur: Data Team
# Description: Arrête tous les services de la stack e-commerce

param(
    [switch]$RemoveVolumes,
    [switch]$RemoveImages,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== SCRIPT D'ARRÊT E-COMMERCE STACK ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage: .\stop-ecommerce-stack.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -RemoveVolumes    Supprime également les volumes Docker (DONNÉES PERDUES!)"
    Write-Host "  -RemoveImages     Supprime également les images Docker"
    Write-Host "  -Help             Affiche cette aide"
    Write-Host ""
    Write-Host "Exemples:" -ForegroundColor Magenta
    Write-Host "  .\stop-ecommerce-stack.ps1                      # Arrêt simple"
    Write-Host "  .\stop-ecommerce-stack.ps1 -RemoveVolumes       # Arrêt + suppression données"
    Write-Host "  .\stop-ecommerce-stack.ps1 -RemoveImages        # Arrêt + suppression images"
    Write-Host ""
    Write-Host "⚠️  ATTENTION:" -ForegroundColor Yellow
    Write-Host "  -RemoveVolumes supprimera TOUTES les données des bases!" -ForegroundColor Red
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== ARRÊT DE LA STACK E-COMMERCE ===" -ForegroundColor Red

# Vérifier que Docker est en cours d'exécution
try {
    docker version | Out-Null
    Write-Host "✓ Docker est disponible" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker n'est pas disponible" -ForegroundColor Red
    exit 1
}

# Arrêter les services
Write-Host "🛑 Arrêt des services..." -ForegroundColor Yellow

$composeCommand = "docker-compose -f docker-compose-extended.yaml down"

if ($RemoveVolumes) {
    Write-Host "⚠️  SUPPRESSION DES VOLUMES DEMANDÉE - TOUTES LES DONNÉES SERONT PERDUES!" -ForegroundColor Red
    $confirmation = Read-Host "Êtes-vous sûr? Tapez 'OUI' pour confirmer"
    if ($confirmation -eq "OUI") {
        $composeCommand += " -v"
        Write-Host "🗑️  Les volumes seront supprimés" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Suppression des volumes annulée" -ForegroundColor Green
    }
}

Write-Host "Commande: $composeCommand" -ForegroundColor Gray
Invoke-Expression $composeCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Services arrêtés avec succès" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors de l'arrêt des services" -ForegroundColor Red
}

# Supprimer les images si demandé
if ($RemoveImages) {
    Write-Host "🗑️  Suppression des images Docker..." -ForegroundColor Yellow
    
    $images = @(
        "apache/airflow:3.0.0",
        "mysql:8.0",
        "postgres:13",
        "redis:7.2-bookworm",
        "phpmyadmin/phpmyadmin",
        "dpage/pgadmin4"
    )
    
    foreach ($image in $images) {
        try {
            docker rmi $image -f 2>$null
            Write-Host "  ✓ Image $image supprimée" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Image $image non trouvée ou en cours d'utilisation" -ForegroundColor Yellow
        }
    }
}

# Nettoyer les ressources orphelines
Write-Host "🧹 Nettoyage des ressources orphelines..." -ForegroundColor Yellow
docker system prune -f | Out-Null

# Afficher l'état final
Write-Host ""
Write-Host "📊 État final des conteneurs:" -ForegroundColor Cyan
docker ps -a --filter "name=airflow" --filter "name=mysql" --filter "name=postgres" --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
if ($RemoveVolumes) {
    Write-Host "✅ STACK COMPLÈTEMENT SUPPRIMÉE" -ForegroundColor Red
    Write-Host "   Toutes les données ont été supprimées." -ForegroundColor Yellow
} else {
    Write-Host "✅ STACK ARRÊTÉE" -ForegroundColor Green
    Write-Host "   Les données sont conservées dans les volumes Docker." -ForegroundColor Yellow
    Write-Host "   Utilisez .\start-ecommerce-stack.ps1 pour redémarrer." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=== FIN DU SCRIPT ===" -ForegroundColor Red