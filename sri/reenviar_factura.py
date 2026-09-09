"""Reenviar factura al SRI - produccion."""
import django,os,sys,time,logging
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OdontoSmart.settings')
django.setup()

from django.utils import timezone as tz
from django.core.files.base import ContentFile
from facturacion.models import Factura
from sri.models import SriEmpresaConfig, SriDocumento
from sri.xml_generator import xml_factura
from sri.signature import firmar_xml_con_archivo
from sri.services import enviar_comprobante, autorizar_comprobante
from sri import enums

f = Factura.objects.get(id=9)
c = SriEmpresaConfig.objects.filter(empresa__id=1, activo=True).first()
if not c or not c.certificado_p12:
    print("ERROR: sin config/certificado"); sys.exit(1)

sec = c.next_secuencial()
pac = f.paciente

items = []
for item in (f.items or []):
    qty = float(item.get('cantidad', 1))
    price = float(item.get('precio_unitario', 0))
    items.append({'descripcion': item.get('descripcion', ''), 'cantidad': qty,
                  'precio_unitario': price, 'total': qty * price, 'descuento_item': 0})

data = {
    'fecha_emision': tz.datetime.combine(f.fecha_emision or tz.localdate(), tz.datetime.min.time()),
    'cliente_identificacion': pac.cedula or '',
    'cliente_razon_social': f'{pac.nombres} {pac.apellidos}',
    'cliente_direccion': pac.direccion or '',
    'cliente_email': pac.email or '',
    'cliente_telefono': pac.celular or pac.telefono or '',
    'items': items, 'subtotal': float(f.subtotal), 'descuento': 0.0,
    'iva_porcentaje': float(f.impuesto_porcentaje), 'iva_valor': float(f.impuesto_monto),
    'total': float(f.total),
    'forma_pago_sri': enums.MAPEO_FORMAS_PAGO.get(f.forma_pago, enums.PAGO_SIN_UTILIZACION),
}

print(f'Factura: {f.numero} | Amb: {c.ambiente} | Sec: {sec}')
clave, ndoc, xml_str = xml_factura(c, data, sec)
print(f'[1] XML: {len(xml_str)}b | Clave: {clave}')
xml_firmado = firmar_xml_con_archivo(xml_str, c.certificado_p12.read(), c.clave_certificado)
print(f'[2] Firmado: {len(xml_firmado)}b')
doc = SriDocumento.objects.create(
    empresa_config=c, tipo=enums.DOC_FACTURA, clave_acceso=clave,
    numero_documento=ndoc, factura_origen_id=f.id,
    factura_origen_modelo='facturacion.factura', xml_firmado=xml_firmado,
    ambiente=c.ambiente, estado='PENDIENTE',
    identificacion_comprador=pac.cedula or '',
    razon_social_comprador=f'{pac.nombres} {pac.apellidos}',
    total_sin_impuestos=Decimal(str(f.subtotal)), total=Decimal(str(f.total)),
    fecha_emision=tz.now())
print(f'[3] Doc ID={doc.id}')

r = enviar_comprobante(xml_firmado, ambiente=c.ambiente)
estado = r.get('estado', 'ERROR')
print(f'[4] SRI: {estado}')
for m in r.get('mensajes', [])[:3]:
    print(f'    {m.get("identificador")}: {m.get("mensaje")} - {m.get("informacionAdicional", "")[:80]}')

if estado == 'AUTORIZADO':
    doc.estado = 'AUTORIZADO'; doc.numero_autorizacion = clave
    doc.xml_autorizado = r.get('xml_autorizado', '')
    if doc.xml_autorizado:
        doc.archivo_xml_autorizado.save(f'sri_aut_{ndoc}.xml', ContentFile(doc.xml_autorizado.encode()))
    doc.save(); print('=> AUTORIZADO!')
elif estado == 'RECIBIDA':
    time.sleep(2)
    ar = autorizar_comprobante(clave, ambiente=c.ambiente)
    ae = ar.get('estado', 'ERROR')
    print(f'    Autoriz: {ae}')
    for m in ar.get('mensajes', [])[:3]:
        print(f'    {m.get("identificador")}: {m.get("mensaje")} - {m.get("informacionAdicional", "")[:120]}')
    if ae == 'AUTORIZADO':
        doc.estado = 'AUTORIZADO'; doc.numero_autorizacion = clave
        doc.xml_autorizado = ar.get('xml_autorizado', '')
        if doc.xml_autorizado:
            doc.archivo_xml_autorizado.save(f'sri_aut_{ndoc}.xml', ContentFile(doc.xml_autorizado.encode()))
        doc.save(); print('=> AUTORIZADO!')
    else:
        doc.estado = 'ENVIADO'; doc.mensajes = ar.get('mensajes', [])
        doc.save(); print('=> PENDIENTE')
else:
    doc.estado = 'ERROR'; doc.mensajes = r.get('mensajes', [])
    doc.save(); print('=> ERROR')
print(f'Final: {doc.estado}')
