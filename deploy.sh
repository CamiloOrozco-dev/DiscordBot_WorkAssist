#!/bin/bash
# Script de despliegue rápido a Railway
# Uso: ./deploy.sh

echo "🚀 Desplegando ZoroBot a Railway..."

# Verificar que railway CLI está instalado
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI no está instalado."
    echo "Instala con: npm install -g @railway/cli"
    exit 1
fi

# Verificar conexión con Railway
echo "📡 Verificando conexión con Railway..."
railway status
if [ $? -ne 0 ]; then
    echo "❌ No estás conectado a Railway."
    echo "Ejecuta: railway link"
    exit 1
fi

# Hacer commit si hay cambios pendientes
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 Detectados cambios sin commit."
    read -p "¿Deseas hacer commit de los cambios? (s/n): " commit
    if [ "$commit" = "s" ]; then
        read -p "Mensaje del commit: " message
        git add .
        git commit -m "$message"
        echo "✅ Commit realizado"
    fi
fi

# Desplegar
echo "🚀 Desplegando a Railway..."
railway up

if [ $? -eq 0 ]; then
    echo "✅ Desplegado exitosamente!"
    echo "📊 Ver logs: railway logs"
else
    echo "❌ Error en el despliegue"
    exit 1
fi
