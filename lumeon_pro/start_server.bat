@echo off
REM Script para ejecutar el servidor LUMEON PRO
REM ============================================

echo 🚀 Iniciando LUMEON PRO Server...
echo.

REM Verificar que estamos en el directorio correcto
if not exist "backend\app.py" (
    echo ❌ Error: Ejecuta este script desde la carpeta raiz de lumeon_pro
    echo    Ejemplo: cd C:\Users\johan\Downloads\LUMEON_PRO_SOFTWARE\lumeon_pro
    pause
    exit /b 1
)

REM Verificar que .env existe
if not exist ".env" (
    echo ⚠️  Archivo .env no encontrado. Copiando de .env.example...
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo ✅ Archivo .env creado. Edítalo con tus credenciales de Gmail.
        echo.
        echo 💡 IMPORTANTE: Configura GMAIL_USER y GMAIL_PASSWORD en .env
        echo    1. Ve a: https://myaccount.google.com/apppasswords
        echo    2. Genera contraseña de aplicación
        echo    3. Actualiza el .env
        echo.
        pause
    ) else (
        echo ❌ Error: No se encuentra .env.example
        pause
        exit /b 1
    )
)

REM Verificar dependencias
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

REM Ejecutar el servidor
echo 🌐 Iniciando servidor en http://127.0.0.1:5000
echo 📧 Sistema de correos automáticos activado
echo.
echo 💡 Presiona Ctrl+C para detener el servidor
echo.

python backend/app.py