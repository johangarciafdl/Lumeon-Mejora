#!/usr/bin/env python3
"""
Script para testear envío de recibos PDF con email a clientes REALES
Sin emails ficticios como test@example.com
"""
import sqlite3
import os
import sys
import smtplib
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app import enviar_factura_email, generar_factura_pdf, get_db
from dotenv import load_dotenv

load_dotenv()

def test_email_pdf():
    """Test completo de PDF y email"""
    print("\n" + "="*70)
    print("TEST: GENERACIÓN Y ENVÍO DE RECIBOS PDF")
    print("="*70 + "\n")
    
    # 1. Verificar configuración Gmail
    print("📧 [1] Verificando configuración Gmail...")
    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_PASSWORD", "").strip()
    
    if not gmail_user or not gmail_pass:
        print("❌ GMAIL_USER o GMAIL_PASSWORD no están configurados en .env")
        return False
    
    print(f"   ✓ GMAIL_USER: {gmail_user}")
    print(f"   ✓ GMAIL_PASSWORD: {'*' * len(gmail_pass)} ({len(gmail_pass)} chars)")
    
    # 2. Probar conexión SMTP
    print("\n📧 [2] Probando conexión SMTP...")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_pass)
        print("   ✓ SMTP login exitoso")
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación SMTP. Verifica contraseña de aplicación.")
        return False
    except Exception as e:
        print(f"❌ Error SMTP: {e}")
        return False
    
    # 3. Buscar ventas en la BD
    print("\n📊 [3] Buscando ventas en base de datos...")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, numero_factura, cliente_email, cliente_nombre FROM ventas WHERE cliente_email IS NOT NULL AND cliente_email != '' ORDER BY id DESC LIMIT 5")
    ventas = c.fetchall()
    conn.close()
    
    if not ventas:
        print("❌ No hay ventas con email de cliente en la BD")
        print("   Necesitas crear una venta CON EMAIL de cliente para probar")
        return False
    
    print(f"   ✓ Encontradas {len(ventas)} ventas con email:")
    for i, v in enumerate(ventas, 1):
        print(f"      {i}. Factura {v[1]} → {v[2]} (Cliente: {v[3]})")
    
    # 4. Probar PDF con la primera venta
    venta = ventas[0]
    venta_id = venta[0]
    numero_factura = venta[1]
    cliente_email = venta[2]
    cliente_nombre = venta[3]
    
    print(f"\n📄 [4] Generando PDF para Factura {numero_factura}...")
    pdf_buffer = generar_factura_pdf(venta_id)
    
    if not pdf_buffer:
        print("❌ No se pudo generar el PDF")
        return False
    
    pdf_buffer.seek(0)
    pdf_content = pdf_buffer.read()
    pdf_size = len(pdf_content)
    
    print(f"   ✓ PDF generado exitosamente")
    print(f"   ✓ Tamaño del PDF: {pdf_size:,} bytes")
    
    if pdf_size < 100:
        print("❌ ADVERTENCIA: El PDF es muy pequeño, podría estar corrupto")
        return False
    
    # 5. Verificar estructura del PDF
    print(f"\n📋 [5] Verificando estructura del PDF...")
    pdf_buffer.seek(0)
    primera_linea = pdf_buffer.read(10)
    
    if primera_linea.startswith(b'%PDF'):
        print("   ✓ Estructura PDF válida (comienza con %PDF)")
    else:
        print(f"❌ Estructura PDF inválida. Comienza con: {primera_linea}")
        return False
    
    # 6. Guardar PDF local para inspección
    print(f"\n💾 [6] Guardando copia local del PDF...")
    pdf_path = Path(__file__).parent / f"test_receipt_{numero_factura}.pdf"
    with open(pdf_path, 'wb') as f:
        pdf_buffer.seek(0)
        f.write(pdf_buffer.read())
    print(f"   ✓ PDF guardado en: {pdf_path}")
    
    # 7. Intentar enviar el email
    print(f"\n✉️  [7] Intentando enviar recibo a: {cliente_email}")
    print(f"   Cliente: {cliente_nombre}")
    print(f"   Factura: {numero_factura}")
    
    # Resetear buffer
    pdf_buffer.seek(0)
    
    resultado = enviar_factura_email(cliente_email, cliente_nombre, numero_factura, pdf_buffer)
    
    if resultado:
        print(f"   ✅ Email enviado exitosamente a {cliente_email}")
        print("\n✅ TEST COMPLETADO: Todo funciona correctamente")
        print(f"   1. Verifica tu bandeja en {cliente_email}")
        print(f"   2. Descarga el PDF adjunto y ábrelo")
        print(f"   3. Si abre correctamente, el sistema está funcionando")
        return True
    else:
        print(f"   ❌ Fallo al enviar email")
        print("   Revisa los mensajes de error arriba")
        return False

if __name__ == '__main__':
    success = test_email_pdf()
    sys.exit(0 if success else 1)
