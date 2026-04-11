#!/usr/bin/env python3
"""
SCRIPT RÁPIDO: Verificar configuración de email
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("🔍 VERIFICACIÓN RÁPIDA DE EMAIL")
print("=" * 40)

gmail_user = os.getenv("GMAIL_USER", "").strip()
gmail_pass = os.getenv("GMAIL_PASSWORD", "").strip()

print(f"GMAIL_USER: {gmail_user}")
print(f"GMAIL_PASSWORD: {'*' * len(gmail_pass) if gmail_pass else 'NO CONFIGURADO'}")

if not gmail_user or gmail_user == "tu_email@gmail.com":
    print("❌ GMAIL_USER no configurado correctamente")
elif not gmail_pass or gmail_pass == "tu_contraseña_app_gmail":
    print("❌ GMAIL_PASSWORD no configurado correctamente")
else:
    print("✅ Configuración parece correcta")

    # Probar conexión SMTP
    try:
        import smtplib
        print("\n🔍 Probando conexión SMTP...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(gmail_user, gmail_pass)
        print("✅ Conexión SMTP exitosa")
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación - verifica contraseña de aplicación")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")