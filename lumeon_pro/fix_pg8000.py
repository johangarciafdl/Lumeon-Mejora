content = open('backend/app.py', encoding='utf-8').read()

# Reemplazar imports de psycopg2 por pg8000
viejo = '''try:
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = True
except ImportError:
    USE_POSTGRES = False'''

nuevo = '''try:
    import pg8000
    USE_POSTGRES = True
except ImportError:
    USE_POSTGRES = False'''

if viejo in content:
    content = content.replace(viejo, nuevo)
    print('✅ import cambiado a pg8000')
else:
    print('⚠️  import no encontrado')

# Reemplazar get_db para usar pg8000
viejo_getdb = '''def get_db():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and database_url.startswith("postgresql"):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn'''

nuevo_getdb = '''def get_db():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and database_url.startswith("postgresql"):
        import pg8000.native
        import urllib.parse as urlparse
        result = urlparse.urlparse(database_url)
        conn = pg8000.dbapi.connect(
            host=result.hostname,
            port=result.port or 5432,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            ssl_context=True
        )
        return conn
    else:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn'''

if viejo_getdb in content:
    content = content.replace(viejo_getdb, nuevo_getdb)
    print('✅ get_db actualizado para pg8000')
else:
    print('⚠️  get_db no encontrado exactamente')
    for i, line in enumerate(content.split('\n'), 1):
        if 'psycopg2' in line:
            print(f'  Linea {i}: {line.strip()}')

open('backend/app.py', 'w', encoding='utf-8').write(content)
print('✅ app.py actualizado')
