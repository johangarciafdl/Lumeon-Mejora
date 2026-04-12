nixpacks = """[phases.setup]
nixPkgs = ["python312"]

[phases.install]
cmds = ["pip install -r lumeon_pro/requirements.txt"]

[start]
cmd = "gunicorn --chdir lumeon_pro/backend app:app --bind 0.0.0.0:$PORT"
"""

procfile = "web: gunicorn --chdir lumeon_pro/backend app:app --bind 0.0.0.0:$PORT\n"

open('nixpacks.toml', 'w').write(nixpacks)
print('✅ nixpacks.toml creado')

open('Procfile', 'w').write(procfile)
print('✅ Procfile creado')
