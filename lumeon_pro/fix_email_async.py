content = open('backend/app.py', encoding='utf-8').read()

# Agregar import threading al inicio si no existe
if 'import threading' not in content:
    content = content.replace(
        'import sqlite3, os, smtplib, io, re',
        'import sqlite3, os, smtplib, io, re, threading'
    )
    print('✅ import threading agregado')

# Cambiar el bloque de envío de email para que sea asíncrono
viejo = """            if email_cliente:
                print(f"📧 Generando recibo para: {email_cliente}")
                pdf_buffer = generar_factura_pdf(vid)
                if pdf_buffer:
                    email_enviado = enviar_factura_email(email_cliente, nombre_cliente, numero_factura, pdf_buffer)
                    if email_enviado:
                        c.execute("UPDATE ventas SET pdf_enviado=1 WHERE id=?", (vid,))
                        conn.commit()
                else:
                    print("❌ No se pudo generar el PDF del recibo")
            else:
                print("⚠️  Venta registrada sin email de cliente — no se envió recibo")"""

nuevo = """            if email_cliente:
                print(f"📧 Generando recibo para: {email_cliente}")
                pdf_buffer = generar_factura_pdf(vid)
                if pdf_buffer:
                    # Enviar email en hilo separado para no bloquear la respuesta
                    def enviar_en_hilo(email, nombre, factura, pdf, venta_id):
                        try:
                            resultado = enviar_factura_email(email, nombre, factura, pdf)
                            if resultado:
                                conn2 = get_db()
                                conn2.execute("UPDATE ventas SET pdf_enviado=1 WHERE id=?", (venta_id,))
                                conn2.commit()
                                conn2.close()
                                print(f"✅ Email enviado en hilo: {email}")
                        except Exception as e:
                            print(f"❌ Error en hilo email: {e}")
                    
                    hilo = threading.Thread(
                        target=enviar_en_hilo,
                        args=(email_cliente, nombre_cliente, numero_factura, pdf_buffer, vid),
                        daemon=True
                    )
                    hilo.start()
                    email_enviado = True  # Optimista - se envía en background
                else:
                    print("❌ No se pudo generar el PDF del recibo")
            else:
                print("⚠️  Venta registrada sin email de cliente — no se envió recibo")"""

if viejo in content:
    content = content.replace(viejo, nuevo)
    open('backend/app.py', 'w', encoding='utf-8').write(content)
    print('✅ Envío de email ahora es asíncrono - no bloqueará la respuesta')
else:
    print('⚠️  No se encontró el bloque exacto')
    # Buscar líneas relacionadas
    for i, line in enumerate(content.split('\n'), 1):
        if 'pdf_buffer' in line or 'email_enviado' in line:
            print(f'  Linea {i}: {line.strip()}')
