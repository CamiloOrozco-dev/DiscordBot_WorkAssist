# Script de despliegue rápido a Railway
# Uso: .\deploy.ps1

Write-Host "🚀 Desplegando ZoroBot a Railway..." -ForegroundColor Cyan

# Verificar que railway CLI está instalado
if (!(Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Railway CLI no está instalado." -ForegroundColor Red
    Write-Host "Instala con: npm install -g @railway/cli" -ForegroundColor Yellow
    exit 1
}

# Verificar conexión con Railway
Write-Host "📡 Verificando conexión con Railway..." -ForegroundColor Yellow
railway status
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ No estás conectado a Railway." -ForegroundColor Red
    Write-Host "Ejecuta: railway link" -ForegroundColor Yellow
    exit 1
}

# Hacer commit si hay cambios pendientes
$status = git status --porcelain
if ($status) {
    Write-Host "📝 Detectados cambios sin commit." -ForegroundColor Yellow
    $commit = Read-Host "¿Deseas hacer commit de los cambios? (s/n)"
    if ($commit -eq "s") {
        $message = Read-Host "Mensaje del commit"
        git add .
        git commit -m "$message"
        Write-Host "✅ Commit realizado" -ForegroundColor Green
    }
}

# Desplegar
Write-Host "🚀 Desplegando a Railway..." -ForegroundColor Cyan
railway up

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Desplegado exitosamente!" -ForegroundColor Green
    Write-Host "📊 Ver logs: railway logs" -ForegroundColor Cyan
} else {
    Write-Host "❌ Error en el despliegue" -ForegroundColor Red
    exit 1
}
