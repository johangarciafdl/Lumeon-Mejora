import importlib.util
from pathlib import Path
import os

script_path = Path(__file__).parent / 'backend' / 'app.py'
spec = importlib.util.spec_from_file_location('backend_app', script_path)
backend = importlib.util.module_from_spec(spec)
loader = spec.loader
assert loader is not None
loader.exec_module(backend)

# Load environment explicitly
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

# Generate a PDF buffer for a dummy venta
# We need a dummy record in database? Instead we can call generar_factura_pdf on a known existing sale if one exists.
# For safety, just test enviar_factura_email directly with an empty PDF.
import io
pdf_buffer = io.BytesIO(b'%PDF-1.4\n%Dummy PDF content')
email_cliente = 'test@example.com'
nombre_cliente = 'Prueba'
numero_factura = 'TEST-EMAIL'

print('Calling enviar_factura_email...')
result = backend.enviar_factura_email(email_cliente, nombre_cliente, numero_factura, pdf_buffer)
print('Result:', result)
