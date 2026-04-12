# runtime.txt
open('runtime.txt', 'w').write('python-3.12.0\n')
print('✅ runtime.txt creado')

# nixpacks.toml corregido
nixpacks = '[phases.install]\ncmds = ["python -m pip install -r lumeon_pro/requirements.txt"]\n\n[start]\ncmd = "python -m gunicorn --chdir lumeon_pro/backend app:app --bind 0.0.0.0:$PORT"\n'
open('nixpacks.toml', 'w').write(nixpacks)
print('✅ nixpacks.toml actualizado')

# Procfile actualizado
open('Procfile', 'w').write('web: python -m gunicorn --chdir lumeon_pro/backend app:app --bind 0.0.0.0:$PORT\n')
print('✅ Procfile actualizado')
