import os
import smtplib
from dotenv import load_dotenv
from pathlib import Path

# Cargar configuración
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("🔍 PRUEBA DE CONEXIÓN GMAIL")
print("=" * 40)

gmail_user = os.getenv("GMAIL_USER", "").strip()
gmail_pass = os.getenv("GMAIL_PASSWORD", "").strip()

print(f"Usuario: {gmail_user}")
print(f"Contraseña: {'*' * len(gmail_pass)}")

if not gmail_user or not gmail_pass:
    print("❌ Configuración incompleta")
    exit(1)

try:
    print("\n🔗 Conectando a Gmail SMTP...")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
        server.login(gmail_user, gmail_pass)
    print("✅ ¡CONEXIÓN EXITOSA!")
    print("Tu configuración de Gmail está correcta.")
except smtplib.SMTPAuthenticationError as e:
    print("❌ ERROR DE AUTENTICACIÓN")
    print("Posibles causas:")
    print("1. Contraseña de aplicación incorrecta")
    print("2. Autenticación de 2 factores no habilitada")
    print("3. Contraseña de aplicación expirada")
    print(f"Detalle: {e}")
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN: {e}")
    print("Verifica tu conexión a internet")