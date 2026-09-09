"""
Validador de XML contra el XSD oficial del SRI para factura electrónica.
"""
import os, sys, urllib.request
from pathlib import Path

XSD_URL = 'https://www.sri.gob.ec/sri/descargas/factura_v1_0_0.xsd'
XSD_PATH = 'media/sri/factura_v1_0_0.xsd'

print('Descargando XSD del SRI...')
try:
    urllib.request.urlretrieve(XSD_URL, XSD_PATH)
    print(f'XSD descargado: {XSD_PATH}')
except Exception as e:
    print(f'No se pudo descargar el XSD: {e}')
    if os.path.exists(XSD_PATH):
        print(f'Usando XSD local: {XSD_PATH}')
    else:
        print('No hay XSD disponible')
        sys.exit(1)

import xmlschema

firmados = sorted(Path('media/sri/documentos/firmados').glob('*.xml'))
if not firmados:
    print('No hay XML firmados para validar')
    sys.exit(1)

xml_path = firmados[-1]
xml_content = xml_path.read_text(encoding='utf-8')
print(f'\nValidando: {xml_path.name} ({len(xml_content)} bytes)')

try:
    schema = xmlschema.XMLSchema(XSD_PATH)
    schema.validate(xml_content)
    print('\n✅ VALIDACIÓN EXITOSA - El XML cumple con el XSD del SRI')
except xmlschema.XMLSchemaValidationError as e:
    print(f'\n❌ ERROR {e.reason}')
    if hasattr(e, 'path') and e.path:
        print(f'   Ruta: {e.path}')
    print(f'\nDetalle:')
    for err in e.error_layout:
        print(f'  - {err}')
except Exception as e:
    print(f'\nError: {e}')
