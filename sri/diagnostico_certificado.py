"""Diagnóstico del certificado digital p12."""
import django, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'OdontoSmart.settings'
django.setup()

from sri.models import SriEmpresaConfig
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509

cfg = SriEmpresaConfig.objects.first()
p12_data = cfg.certificado_p12.read()
_, cert, _ = pkcs12.load_key_and_certificates(p12_data, cfg.clave_certificado.encode())

print("=== CERTIFICADO ===")
print(f"Subject: {cert.subject.rfc4514_string()}")
print(f"Issuer: {cert.issuer.rfc4514_string()}")
print(f"Serial: {cert.serial_number} (hex: {hex(cert.serial_number)})")
print(f"Valido desde: {cert.not_valid_before_utc}")
print(f"Valido hasta: {cert.not_valid_after_utc}")

print("\n=== EXTENSIONES ===")
for ext in cert.extensions:
    print(f"  {ext.oid._name}: {ext.value}")

# Verificar si el certificado es para firma digital
print("\n=== VERIFICACION ===")
try:
    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    usages = [u._name if hasattr(u, '_name') else str(u) for u in eku.value]
    print(f"Extended Key Usage: {usages}")
except x509.ExtensionNotFound:
    print("Extended Key Usage: NO ENCONTRADO")

try:
    ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
    u = ku.value
    print(f"Key Usage: digital_signature={u.digital_signature}")
    print(f"Key Usage: content_commitment (non-repudiation)={u.content_commitment}")
except x509.ExtensionNotFound:
    print("Key Usage: NO ENCONTRADO")
