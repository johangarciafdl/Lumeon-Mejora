@echo off
REM Script para ejecutar el servidor LUMEON PRO V2
REM ================================================

echo 🚀 Iniciando LUMEON PRO Server V2...
echo.

if not exist "backend\app_v2.py" (
    echo ❌ Error: Ejecuta este script desde la carpeta raiz de lumeon_pro
    pause
    exit /b 1
)

if not exist ".env" (
    echo ⚠️  Archivo .env no encontrado. Copiando de .env.example...
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo ✅ Archivo .env creado. Configura las variables de entorno antes de continuar.
        echo.
        pause
    ) else (
        echo ❌ Error: No se encuentra .env.example
        pause
        exit /b 1
    )
)

echo 🔍 Verificando dependencias...
python -c "import flask, flask_login, reportlab, dotenv" 2>nul
if errorlevel 1 (
    echo ⚠️  Instalando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Error al instalar dependencias
        pause
        exit /b 1
    )
)

echo ✅ Dependencias verificadas
echo.

echo 🌐 Iniciando servidor V2 en http://127.0.0.1:5000
echo 💡 Presiona Ctrl+C para detener el servidor
echo.

set LUMEON_AUTO_MIGRATE=true
python backend/app_v2.py
