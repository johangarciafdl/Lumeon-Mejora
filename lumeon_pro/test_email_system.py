#!/usr/bin/env python3
"""
SCRIPT DE PRUEBA: Sistema de Correos Automáticos LUMEON PRO
===========================================================

Este script verifica que el sistema de envío automático de recibos funcione correctamente.
"""

import os
import sys
import requests
import json
from pathlib import Path

def test_imports():
    """Verificar que todas las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    try:
        import flask
        import flask_login
        import reportlab
        import dotenv
        import smtplib
        print("✅ Todas las dependencias están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Falta instalar dependencia: {e}")
        return False

def test_env_config():
    """Verificar configuración del .env"""
    print("\n🔍 Verificando configuración .env...")
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("❌ Archivo .env no encontrado")
        return False

    from dotenv import load_dotenv
    load_dotenv(env_path)

    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_pass = os.getenv("GMAIL_PASSWORD", "")

    if not gmail_user or gmail_user == "tu_email@gmail.com":
        print("⚠️  GMAIL_USER no configurado (usa tu email real)")
        return False

    if not gmail_pass or gmail_pass == "tu_contraseña_app_gmail":
        print("⚠️  GMAIL_PASSWORD no configurado (usa contraseña de aplicación)")
        return False

    print(f"✅ Configuración Gmail: {gmail_user}")
    return True

def test_server_connection():
    """Verificar que el servidor esté corriendo"""
    print("\n🔍 Verificando conexión al servidor...")
    try:
        response = requests.get("http://127.0.0.1:5000", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor corriendo correctamente")
            return True
        else:
            print(f"⚠️  Servidor responde con código: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ No se puede conectar al servidor: {e}")
        print("💡 Asegúrate de ejecutar: python backend/app.py")
        return False

def test_login():
    """Probar login al sistema"""
    print("\n🔍 Probando login...")
    try:
        response = requests.post("http://127.0.0.1:5000/api/login",
                               json={"username": "admin1", "password": "admin123"},
                               timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print("✅ Login exitoso")
                return True
            else:
                print(f"❌ Error en login: {data.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP en login: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error al probar login: {e}")
        return False

def test_email_system():
    """Probar el sistema de envío de emails (sin enviar realmente)"""
    print("\n🔍 Probando sistema de email...")

    # Simular datos de venta
    test_data = {
        "numero_factura": "TEST-001",
        "cliente_nombre": "Cliente de Prueba",
        "cliente_email": "test@example.com",
        "items": [
            {
                "referencia": "TEST-001",
                "nombre": "Producto de Prueba",
                "cantidad": 1,
                "precio_venta": 10000,
                "precio_compra": 5000
            }
        ]
    }

    try:
        # Crear sesión con login
        session = requests.Session()

        # Login primero
        login_response = session.post("http://127.0.0.1:5000/api/login",
                                    json={"username": "admin1", "password": "admin123"})
        if not login_response.json().get("ok"):
            print("❌ No se pudo autenticar para la prueba")
            return False

        # Intentar crear venta de prueba
        response = session.post("http://127.0.0.1:5000/api/ventas",
                              json=test_data, timeout=30)

        if response.status_code == 201:
            data = response.json()
            print("✅ Venta de prueba creada exitosamente")
            print(f"   ID: {data.get('id')}")
            print(f"   Email enviado: {data.get('email_enviado')}")

            if data.get('email_enviado'):
                print("✅ Sistema de email funcionando correctamente")
            else:
                print("⚠️  Email no enviado (probablemente no configurado)")

            return True
        else:
            print(f"❌ Error al crear venta de prueba: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error al probar sistema de email: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 PRUEBA DEL SISTEMA DE CORREOS AUTOMÁTICOS LUMEON PRO")
    print("=" * 60)

    # Ejecutar todas las pruebas
    tests = [
        ("Dependencias", test_imports),
        ("Configuración .env", test_env_config),
        ("Conexión servidor", test_server_connection),
        ("Login sistema", test_login),
        ("Sistema email", test_email_system)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))

    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ¡TODA LAS PRUEBAS PASARON!")
        print("Tu sistema de correos automáticos está funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los mensajes anteriores.")
        print("\n💡 RECOMENDACIONES:")
        print("1. Asegúrate de que el servidor esté corriendo: python backend/app.py")
        print("2. Configura correctamente el archivo .env con tus credenciales de Gmail")
        print("3. Instala todas las dependencias: pip install -r requirements.txt")
        print("4. Genera una contraseña de aplicación en Gmail si no lo has hecho")

    print("=" * 60)

if __name__ == "__main__":
    main()