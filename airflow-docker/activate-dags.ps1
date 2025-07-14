# Script PowerShell pour activer et gérer les DAGs
# Auteur: Data Team
# Description: Active les DAGs e-commerce et vérifie leur statut

param(
    [switch]$Activate,
    [switch]$Deactivate,
    [switch]$Status,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== GESTION DES DAGS E-COMMERCE ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\activate-dags.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -Activate     Active tous les DAGs e-commerce"
    Write-Host "  -Deactivate   Désactive tous les DAGs e-commerce"
    Write-Host "  -Status       Affiche le statut des DAGs"
    Write-Host "  -Help         Affiche cette aide"
    Write-Host ""
    Write-Host "DAGs gérés:" -ForegroundColor White
    Write-Host "  • setup_connections (configuration)"
    Write-Host "  • init_ecommerce_oltp (initialisation)"
    Write-Host "  • process_payment_csv (traitement CSV)"
    Write-Host "  • load_raw_data (chargement RAW)"
    Write-Host "  • load_dwh_star (Data Warehouse étoile)"
    Write-Host "  • load_dwh_olap (Data Warehouse OLAP)"
    Write-Host "  • sync_ecommerce_data (synchronisation)"
    Write-Host "  • demo_full_pipeline (démonstration)"
}

function Get-DagStatus {
    Write-Host "📊 STATUT DES DAGS E-COMMERCE" -ForegroundColor Cyan
    Write-Host "=" * 50
    
    try {
        $dagList = docker exec airflow-docker-airflow-scheduler-1 airflow dags list 2>$null
        
        $ecommerceDags = @(
            "setup_connections",
            "init_ecommerce_oltp", 
            "process_payment_csv",
            "load_raw_data",
            "load_dwh_star",
            "load_dwh_olap",
            "sync_ecommerce_data",
            "demo_full_pipeline"
        )
        
        foreach ($dagId in $ecommerceDags) {
            $dagInfo = $dagList | Select-String -Pattern $dagId
            if ($dagInfo) {
                $isPaused = if ($dagInfo -match "True") { "❌ PAUSÉ" } else { "✅ ACTIF" }
                Write-Host "  $dagId - $isPaused" -ForegroundColor $(if ($isPaused -eq "✅ ACTIF") { "Green" } else { "Yellow" })
            } else {
                Write-Host "  $dagId - ❓ NON TROUVÉ" -ForegroundColor Red
            }
        }
        
    } catch {
        Write-Host "❌ Erreur lors de la récupération du statut des DAGs" -ForegroundColor Red
        Write-Host "Vérifiez que la stack Airflow est démarrée" -ForegroundColor Yellow
    }
}

function Set-DagState {
    param(
        [string]$Action,
        [array]$DagIds
    )
    
    $actionText = if ($Action -eq "unpause") { "ACTIVATION" } else { "DÉSACTIVATION" }
    Write-Host "🔧 $actionText DES DAGS" -ForegroundColor Cyan
    Write-Host "=" * 50
    
    foreach ($dagId in $DagIds) {
        try {
            Write-Host "Traitement de $dagId..." -ForegroundColor Gray
            $result = docker exec airflow-docker-airflow-scheduler-1 airflow dags $Action $dagId 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                $status = if ($Action -eq "unpause") { "✅ ACTIVÉ" } else { "❌ DÉSACTIVÉ" }
                Write-Host "  $dagId - $status" -ForegroundColor $(if ($Action -eq "unpause") { "Green" } else { "Yellow" })
            } else {
                Write-Host "  $dagId - ❌ ERREUR" -ForegroundColor Red
                Write-Host "    $result" -ForegroundColor Red
            }
        } catch {
            Write-Host "  $dagId - ❌ EXCEPTION" -ForegroundColor Red
            Write-Host "    $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== GESTION DES DAGS E-COMMERCE ===" -ForegroundColor Green
Write-Host ""

$ecommerceDags = @(
    "setup_connections",
    "init_ecommerce_oltp", 
    "process_payment_csv",
    "load_raw_data",
    "load_dwh_star",
    "load_dwh_olap",
    "sync_ecommerce_data",
    "demo_full_pipeline"
)

# Vérifier que la stack est démarrée
try {
    $containerStatus = docker ps --filter "name=airflow-scheduler" --format "{{.Status}}" 2>$null
    if (-not $containerStatus -or $containerStatus -notlike "*Up*") {
        Write-Host "❌ ERREUR: La stack Airflow n'est pas démarrée" -ForegroundColor Red
        Write-Host "Démarrez la stack avec: .\start-ecommerce-stack.ps1" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ ERREUR: Impossible de vérifier l'état de Docker" -ForegroundColor Red
    exit 1
}

if ($Activate) {
    Set-DagState -Action "unpause" -DagIds $ecommerceDags
    Write-Host ""
    Write-Host "✅ ACTIVATION TERMINÉE" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Prochaines étapes recommandées:" -ForegroundColor Cyan
    Write-Host "1. Accédez à Airflow: http://localhost:8090" -ForegroundColor White
    Write-Host "2. Exécutez manuellement 'setup_connections'" -ForegroundColor White
    Write-Host "3. Exécutez manuellement 'init_ecommerce_oltp'" -ForegroundColor White
    Write-Host "4. Les autres DAGs s'exécuteront selon leur planning" -ForegroundColor White
    
} elseif ($Deactivate) {
    Set-DagState -Action "pause" -DagIds $ecommerceDags
    Write-Host ""
    Write-Host "⏸️  DÉSACTIVATION TERMINÉE" -ForegroundColor Yellow
    Write-Host "Les DAGs ne s'exécuteront plus automatiquement" -ForegroundColor Gray
    
} elseif ($Status) {
    Get-DagStatus
    
} else {
    # Affichage du statut par défaut
    Get-DagStatus
    Write-Host ""
    Write-Host "💡 ACTIONS DISPONIBLES:" -ForegroundColor Cyan
    Write-Host "  .\activate-dags.ps1 -Activate    # Active tous les DAGs" -ForegroundColor White
    Write-Host "  .\activate-dags.ps1 -Deactivate  # Désactive tous les DAGs" -ForegroundColor White
    Write-Host "  .\activate-dags.ps1 -Status      # Affiche le statut" -ForegroundColor White
}

Write-Host ""
Write-Host "=== FIN DE LA GESTION DES DAGS ===" -ForegroundColor Green