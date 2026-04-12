content = open('backend/app.py', encoding='utf-8').read()

viejo = "with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:\n            server.login(gmail_user, gmail_pass)"

nuevo = "with smtplib.SMTP('smtp.gmail.com', 587) as server:\n            server.ehlo()\n            server.starttls()\n            server.ehlo()\n            server.login(gmail_user, gmail_pass)"

if viejo in content:
    content = content.replace(viejo, nuevo)
    open('backend/app.py', 'w', encoding='utf-8').write(content)
    print('✅ Gmail cambiado a puerto 587 STARTTLS')
else:
    print('⚠️  No encontrado, buscando SMTP en el archivo...')
    for i, line in enumerate(content.split('\n'), 1):
        if 'SMTP' in line and ('465' in line or '587' in line or 'gmail' in line.lower()):
            print(f'  Linea {i}: {line.strip()}')
