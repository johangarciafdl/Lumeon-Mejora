content = open('backend/app.py', encoding='utf-8').read()

viejo = "with smtplib.SMTP('smtp.office365.com', 587) as server:\n            server.starttls()\n            server.login(gmail_user, gmail_pass)"
nuevo = "with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:\n            server.login(gmail_user, gmail_pass)"

if viejo in content:
    fixed = content.replace(viejo, nuevo)
    open('backend/app.py', 'w', encoding='utf-8').write(fixed)
    print('✅ app.py revertido a Gmail correctamente')
else:
    print('⚠️  No se encontró el texto, revisa manualmente')
    for i, line in enumerate(content.split('\n'), 1):
        if 'SMTP' in line:
            print(f'  Línea {i}: {line.strip()}')
