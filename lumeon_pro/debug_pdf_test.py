import importlib.util
from pathlib import Path
import os
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

script_path = Path(__file__).parent / 'backend' / 'app.py'
spec = importlib.util.spec_from_file_location('backend_app', script_path)
backend = importlib.util.module_from_spec(spec)
loader = spec.loader
assert loader is not None
loader.exec_module(backend)

sale_id = 20
print(f'Testing generar_factura_pdf({sale_id})')
pdf = backend.generar_factura_pdf(sale_id)
print('PDF buffer:', type(pdf), 'len:', len(pdf.getvalue()) if pdf else None)
