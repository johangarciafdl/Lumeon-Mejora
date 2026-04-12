content = open('backend/app.py', encoding='utf-8').read()

# Buscar el bloque final
lines = content.split('\n')
print("Ultimas 10 lineas del archivo:")
for i, l in enumerate(lines[-10:], len(lines)-10):
    print(f'{i}: {l}')

# Reemplazar el bloque if __name__
viejo = 'if __name__ == "__main__":\n    init_db()\n    print("🚀 LUMEON PRO corriendo en http://127.0.0.1:5000")\n    print("📧 Gmail configurado:", "✅ Sí" if os.getenv("GMAIL_USER") and os.getenv("GMAIL_USER") != "tu_email@gmail.com" else "❌ No (configura .env)")\n    app.run(debug=True, port=5000)'

nuevo = 'init_db()\n\nif __name__ == "__main__":\n    print("🚀 LUMEON PRO corriendo en http://127.0.0.1:5000")\n    app.run(debug=True, port=5000)'

if viejo in content:
    fixed = content.replace(viejo, nuevo)
    open('backend/app.py', 'w', encoding='utf-8').write(fixed)
    print('\n✅ init_db() movido correctamente - ahora se ejecuta con gunicorn')
else:
    print('\n⚠️ Texto exacto no encontrado, aplicando fix alternativo...')
    # Fix alternativo: agregar init_db() antes del if __name__
    if 'init_db()' in content and 'if __name__' in content:
        # Remover init_db del bloque if __name__ y ponerlo antes
        content = content.replace(
            'if __name__ == "__main__":\n    init_db()',
            'init_db()\n\nif __name__ == "__main__":'
        )
        open('backend/app.py', 'w', encoding='utf-8').write(content)
        print('✅ Fix alternativo aplicado')
    else:
        print('❌ No se pudo aplicar el fix automaticamente')
