"""
Genera un certificado de prueba .p12 para ambiente SRI de pruebas.

Uso: python sri/crear_certificado_prueba.py

Genera: media/sri/certificados/certificado_prueba.p12
"""
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

def crear_certificado_prueba():
    """Crea un certificado .p12 autofirmado para pruebas SRI."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    # Datos del certificado de prueba
    pais = "EC"
    provincia = "AZUAY"
    ciudad = "CUENCA"
    organizacion = "ODONTSMART TEST"
    nombre_comun = "TEST SRI"
    email = "test@odontsmart.com"
    clave_p12 = "12345678"

    # Generar clave privada RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Crear certificado autofirmado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, pais),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, provincia),
        x509.NameAttribute(NameOID.LOCALITY_NAME, ciudad),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organizacion),
        x509.NameAttribute(NameOID.COMMON_NAME, nombre_comun),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
    ])

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365 * 5))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256(), backend=default_backend())
    )

    # Guardar como .p12
    output_dir = Path("media/sri/certificados")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "certificado_prueba.p12"

    # Exportar a PKCS12
    from cryptography.hazmat.primitives.serialization import pkcs12

    p12_data = pkcs12.serialize_key_and_certificates(
        name=b"Certificado Prueba SRI",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            clave_p12.encode("utf-8")
        ),
    )
    output_path.write_bytes(p12_data)

    print(f"✅ Certificado de prueba creado: {output_path}")
    print(f"   Clave: {clave_p12}")
    print(f"   Válido hasta: {cert.not_valid_after}")
    print()
    print("📋 Para usarlo en Config. SRI:")
    print(f"   1. Sube el archivo: {output_path}")
    print(f"   2. Clave: {clave_p12}")
    print("   3. Ambiente: Pruebas")
    print("   4. Tipo Contribuyente: Régimen General")

if __name__ == "__main__":
    crear_certificado_prueba()
