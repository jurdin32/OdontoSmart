"""Compara XML del facturador SRI vs nuestro XML."""
import os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OdontoSmart.settings')
import django; django.setup()

from lxml import etree
from cryptography import x509

path1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    '1507202601070388669700120010010000000011229174418.xml')

from sri.models import SriDocumento
doc = SriDocumento.objects.latest('id')
path2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'media', 'sri', 'documentos', 'firmados',
    f'sri_firmado_{doc.numero_documento.replace("-", "_")}.xml')

ns = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
r1 = etree.parse(path1).getroot()
r2 = etree.parse(path2).getroot()

def info(root, label):
    sig = root.find('ds:Signature', ns)
    si = sig.find('ds:SignedInfo', ns)
    refs = sig.findall('.//ds:Reference', ns)
    cm = si.find('ds:CanonicalizationMethod', ns).get('Algorithm','').split('/')[-1]
    sm = si.find('ds:SignatureMethod', ns).get('Algorithm','').split('#')[-1]
    print(f'{label}: ver={root.get("version")} sigId={sig.get("Id","")[:20]}...')
    print(f'  SignedInfo nsmap={si.nsmap} Id={si.get("Id","NO")}')
    print(f'  C14N={cm} SigMethod={sm}')
    for r in refs:
        uri=r.get('URI',''); rid=r.get('Id',''); dm=r.find('ds:DigestMethod',ns)
        da=dm.get('Algorithm','').split('#')[-1] if dm is not None else '?'
        tr=[t.get('Algorithm','').split('#')[-1] for t in r.findall('ds:Transforms/ds:Transform',ns)]
        print(f'  Ref: URI={uri} Id={rid} Alg={da} Transforms={tr}')
    c14n=etree.tostring(si, method='c14n')
    print(f'  SignedInfo c14n={len(c14n)}b')
    ki=sig.find('ds:KeyInfo',ns); kv=ki.find('ds:KeyValue',ns)
    print(f'  KeyInfo Id={ki.get("Id","NO")} KeyValue={kv is not None}')
    obj=sig.find('ds:Object',ns)
    if obj is not None:
        qp=obj[0]; sp=qp[0] if len(qp)>0 else None
        dof=sp.find('{http://uri.etsi.org/01903/v1.3.2#}SignedDataObjectProperties/{http://uri.etsi.org/01903/v1.3.2#}DataObjectFormat') if sp is not None else None
        print(f'  QP Target={qp.get("Target","")}')
        print(f'  SP Id={sp.get("Id","") if sp is not None else ""}')
        if dof is not None:
            d=dof.find('{http://uri.etsi.org/01903/v1.3.2#}Description')
            e=dof.find('{http://uri.etsi.org/01903/v1.3.2#}Encoding')
            print(f'  DOF ref={dof.get("ObjectReference","")} Desc={d.text if d is not None else ""} Enc={e.text if e is not None else ""}')
    sv=sig.find('ds:SignatureValue',ns)
    print(f'  SigValue len={len(sv.text if sv is not None else "")}')

info(r1, 'FACTURADOR SRI')
info(r2, 'NUESTRO')

# Mismo certificado?
c1=r1.find('.//ds:X509Certificate',ns).text
c2=r2.find('.//ds:X509Certificate',ns).text
cert1=x509.load_der_x509_certificate(base64.b64decode(''.join(c1.split())))
cert2=x509.load_der_x509_certificate(base64.b64decode(''.join(c2.split())))
print(f'\nMismo cert: {cert1.serial_number==cert2.serial_number}')
