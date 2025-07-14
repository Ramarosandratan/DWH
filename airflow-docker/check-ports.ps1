# Script PowerShell pour vérifier la disponibilité des ports
# Auteur: Data Team
# Description: Vérifie que tous les ports nécessaires sont disponibles

param(
    [switch]$Help
)

function Show-Help {
    Write-Host "=== VÉRIFICATION DES PORTS ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\check-ports.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ce script vérifie la disponibilité des ports suivants:" -ForegroundColor White
    Write-Host "  - 8090: Airflow UI"
    Write-Host "  - 3307: MySQL OLTP"
    Write-Host "  - 5435: PostgreSQL RAW"
    Write-Host "  - 5434: PostgreSQL Airflow"
    Write-Host "  - 6379: Redis"
    Write-Host "  - 8081: phpMyAdmin (optionnel)"
    Write-Host "  - 8082: pgAdmin (optionnel)"
    Write-Host "  - 5555: Flower (optionnel)"
}

function Test-Port {
    param(
        [int]$Port,
        [string]$Service
    )
    
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-ProcessUsingPort {
    param([int]$Port)
    
    try {
        $netstat = netstat -ano | Select-String ":$Port "
        if ($netstat) {
            $pid = ($netstat -split '\s+')[-1]
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                return $process.ProcessName
            }
        }
        return "Inconnu"
    } catch {
        return "Erreur"
    }
}

if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== VÉRIFICATION DES PORTS POUR E-COMMERCE STACK ===" -ForegroundColor Green
Write-Host ""

# Définir les ports à vérifier
$ports = @{
    8090 = "Airflow UI"
    3307 = "MySQL OLTP"
    5435 = "PostgreSQL RAW"
    5434 = "PostgreSQL Airflow"
    6379 = "Redis"
    8081 = "phpMyAdmin (optionnel)"
    8082 = "pgAdmin (optionnel)"
    5555 = "Flower (optionnel)"
}

$conflicts = @()
$available = @()

foreach ($port in $ports.Keys) {
    $service = $ports[$port]
    $isUsed = Test-Port -Port $port -Service $service
    
    if ($isUsed) {
        $process = Get-ProcessUsingPort -Port $port
        $conflicts += [PSCustomObject]@{
            Port = $port
            Service = $service
            Process = $process
        }
        Write-Host "❌ Port $port ($service) - OCCUPÉ par $process" -ForegroundColor Red
    } else {
        $available += [PSCustomObject]@{
            Port = $port
            Service = $service
        }
        Write-Host "✅ Port $port ($service) - DISPONIBLE" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== RÉSUMÉ ===" -ForegroundColor Cyan

if ($conflicts.Count -eq 0) {
    Write-Host "🎉 TOUS LES PORTS SONT DISPONIBLES!" -ForegroundColor Green
    Write-Host "Vous pouvez démarrer la stack sans problème." -ForegroundColor White
} else {
    Write-Host "⚠️  CONFLITS DÉTECTÉS:" -ForegroundColor Yellow
    Write-Host ""
    
    $criticalPorts = $conflicts | Where-Object { $_.Port -in @(8090, 3307, 5435, 5434, 6379) }
    $optionalPorts = $conflicts | Where-Object { $_.Port -in @(8081, 8082, 5555) }
    
    if ($criticalPorts.Count -gt 0) {
        Write-Host "🚨 PORTS CRITIQUES OCCUPÉS:" -ForegroundColor Red
        foreach ($conflict in $criticalPorts) {
            Write-Host "   Port $($conflict.Port) ($($conflict.Service)) - Processus: $($conflict.Process)" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "ACTIONS RECOMMANDÉES:" -ForegroundColor Yellow
        Write-Host "1. Arrêtez les processus utilisant ces ports" -ForegroundColor White
        Write-Host "2. Ou modifiez les ports dans docker-compose-extended.yaml" -ForegroundColor White
        Write-Host ""
        
        # Suggestions spécifiques
        foreach ($conflict in $criticalPorts) {
            switch ($conflict.Port) {
                3307 { 
                    Write-Host "💡 Pour MySQL (port 3307): Arrêtez votre instance MySQL locale ou changez le port dans docker-compose" -ForegroundColor Cyan
                }
                5435 { 
                    Write-Host "💡 Pour PostgreSQL (port 5435): Arrêtez votre instance PostgreSQL locale ou changez le port" -ForegroundColor Cyan
                }
                8090 { 
                    Write-Host "💡 Pour Airflow (port 8090): Arrêtez les autres services web ou changez le port" -ForegroundColor Cyan
                }
                6379 { 
                    Write-Host "💡 Pour Redis (port 6379): Arrêtez votre instance Redis locale" -ForegroundColor Cyan
                }
            }
        }
    }
    
    if ($optionalPorts.Count -gt 0) {
        Write-Host ""
        Write-Host "ℹ️  PORTS OPTIONNELS OCCUPÉS:" -ForegroundColor Blue
        foreach ($conflict in $optionalPorts) {
            Write-Host "   Port $($conflict.Port) ($($conflict.Service)) - Processus: $($conflict.Process)" -ForegroundColor Blue
        }
        Write-Host "Ces services sont optionnels et peuvent être désactivés." -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=== COMMANDES UTILES ===" -ForegroundColor Magenta
Write-Host "Voir tous les ports utilisés: netstat -ano | findstr LISTENING" -ForegroundColor Gray
Write-Host "Tuer un processus: taskkill /PID <PID> /F" -ForegroundColor Gray
Write-Host "Démarrer sans services optionnels: .\start-ecommerce-stack.ps1" -ForegroundColor Gray
Write-Host "Démarrer avec services optionnels: .\start-ecommerce-stack.ps1 -WithAdmin" -ForegroundColor Gray

Write-Host ""
Write-Host "=== FIN DE LA VÉRIFICATION ===" -ForegroundColor Green