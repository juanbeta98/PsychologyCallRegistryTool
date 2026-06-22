#!/bin/bash
# Herramienta de Gestión de Llamadas — Bienestar UNAD
# Primera vez: instala todo automáticamente (1-2 minutos)
# Siguientes veces: abre directamente en el navegador

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.psicologia_app_venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "============================================"
    echo " Primera vez: instalando la herramienta..."
    echo " Esto toma 1-2 minutos."
    echo " No cierres esta ventana."
    echo "============================================"

    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: No se pudo crear el entorno. Verifica que Python 3 este instalado."
        read -p "Presiona Enter para cerrar..."
        exit 1
    fi

    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$APP_DIR/app/requirements.txt"
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Fallo la instalacion de paquetes."
        echo "Verifica que tengas conexion a internet e intenta de nuevo."
        rm -rf "$VENV_DIR"
        read -p "Presiona Enter para cerrar..."
        exit 1
    fi

    echo ""
    echo "Instalacion completada exitosamente."
fi

echo "Abriendo la herramienta..."
(sleep 3 && open http://127.0.0.1:5050) &

cd "$APP_DIR"
"$VENV_DIR/bin/python" app/app.py
