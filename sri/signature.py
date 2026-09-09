"""
Firma XAdES-BES para SRI Ecuador.
Basado en:
  - Ficha Técnica de Comprobantes Electrónicos Esquema Off-line v2.33 (SRI)
  - XML de factura firmada oficial del SRI
  - Estándar XAdES (ETSI TS 101 903)
  - XML Signature Syntax and Processing (W3C)

Especificaciones:
  - RSA-SHA256 para SignatureMethod
  - SHA-256 para DigestMethod (http://www.w3.org/2001/04/xmlenc#sha256)
  - Canonicalization XML-C14N 1.0
  - Enveloped Signature
  - 2 referencias: SignedProperties + Comprobante
"""

import base64
import hashlib
import os
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree

# Namespaces
DS = "http://www.w3.org/2000/09/xmldsig#"
XADES = "http://uri.etsi.org/01903/v1.3.2#"
XADES141 = "http://uri.etsi.org/01903/v1.4.1#"

# Algoritmos según Ficha Técnica SRI v2.33
C14N_ALG = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ENVELOPED_ALG = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
SIG_METHOD_ALG = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
DIGEST_METHOD_ALG = "http://www.w3.org/2001/04/xmlenc#sha256"


def firmar_xml(xml_str: str, p12_path: str, p12_clave: str) -> str:
    """
    Firma un XML de comprobante electrónico con XAdES-BES.

    Args:
        xml_str: XML del comprobante (factura, NC, ND, etc.)
        p12_path: Ruta al archivo .p12 del certificado de firma electrónica
        p12_clave: Contraseña del archivo .p12

    Returns:
        XML firmado como string con codificación UTF-8
    """
    root = etree.fromstring(xml_str.encode("utf-8"))

    # Cargar certificado
    with open(p12_path, "rb") as f:
        private_key, cert, _ = pkcs12.load_key_and_certificates(
            f.read(), p12_clave.encode()
        )

    # ========================================================================
    # Preparar datos del certificado
    # ========================================================================
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode()

    # Generar IDs únicos
    sig_uuid = str(uuid4())
    sig_id = f"xmldsig-{sig_uuid}"
    ref0_id = f"{sig_id}-ref0"
    sp_id = f"{sig_id}-signedprops"
    sig_value_id = f"{sig_id}-sigvalue"

    # Timestamp en hora de Ecuador (UTC-5, sin DST) con milisegundos.
    # Usar Ecuador real, NO UTC etiquetado como -05:00 para evitar
    # error SRI "fecha posterior a la actual".
    from datetime import timezone as dt_tz, timedelta
    ecuador = dt_tz(timedelta(hours=-5))
    now_ecu = datetime.now(ecuador)
    # Restar 2 min como margen para evitar skew de reloj vs SRI
    now_ecu = now_ecu - timedelta(minutes=2)
    now = now_ecu.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-05:00"

    # ========================================================================
    # Calcular digest del comprobante usando C14N (determinista)
    # ========================================================================
    # El digest se calcula ANTES de agregar la firma.
    # La transform 'enveloped-signature' elimina el nodo Signature, pero como
    # aún no está presente, serializamos con C14N directamente.
    doc_c14n = etree.tostring(root, method="c14n")
    doc_digest = base64.b64encode(
        hashlib.sha256(doc_c14n).digest()
    ).decode()

    cert_digest = base64.b64encode(
        hashlib.sha256(cert_der).digest()
    ).decode()

    # ========================================================================
    # Construir SignedProperties (XAdES-BES)
    # ========================================================================
    sp = etree.Element(
        f"{{{XADES}}}SignedProperties",
        nsmap={"xades": XADES, "xades141": XADES141, "ds": DS},
        Id=sp_id,
    )

    ssp = etree.SubElement(sp, f"{{{XADES}}}SignedSignatureProperties")
    etree.SubElement(ssp, f"{{{XADES}}}SigningTime").text = now

    sc = etree.SubElement(ssp, f"{{{XADES}}}SigningCertificate")
    ce = etree.SubElement(sc, f"{{{XADES}}}Cert")

    cd = etree.SubElement(ce, f"{{{XADES}}}CertDigest")
    etree.SubElement(cd, f"{{{DS}}}DigestMethod", Algorithm=DIGEST_METHOD_ALG)
    etree.SubElement(cd, f"{{{DS}}}DigestValue").text = cert_digest

    iss = etree.SubElement(ce, f"{{{XADES}}}IssuerSerial")
    etree.SubElement(iss, f"{{{DS}}}X509IssuerName").text = (
        cert.issuer.rfc4514_string()
    )
    etree.SubElement(iss, f"{{{DS}}}X509SerialNumber").text = str(
        cert.serial_number
    )

    sdop = etree.SubElement(sp, f"{{{XADES}}}SignedDataObjectProperties")
    dof = etree.SubElement(
        sdop, f"{{{XADES}}}DataObjectFormat",
        ObjectReference=f"#{ref0_id}",
    )
    etree.SubElement(dof, f"{{{XADES}}}Description").text = "FIRMA DIGITAL SRI"
    etree.SubElement(dof, f"{{{XADES}}}MimeType").text = "text/xml"
    etree.SubElement(dof, f"{{{XADES}}}Encoding").text = "UTF-8"

    # ========================================================================
    # Construir SignedInfo (mismo orden que facturador SRI)
    # ========================================================================
    si = etree.Element(f"{{{DS}}}SignedInfo", nsmap={"ds": DS})
    etree.SubElement(si, f"{{{DS}}}CanonicalizationMethod", Algorithm=C14N_ALG)
    etree.SubElement(si, f"{{{DS}}}SignatureMethod", Algorithm=SIG_METHOD_ALG)

    # Reference 0: Comprobante
    ref0 = etree.SubElement(
        si, f"{{{DS}}}Reference", Id=ref0_id, URI="#comprobante"
    )
    tr = etree.SubElement(ref0, f"{{{DS}}}Transforms")
    etree.SubElement(tr, f"{{{DS}}}Transform", Algorithm=ENVELOPED_ALG)
    etree.SubElement(ref0, f"{{{DS}}}DigestMethod", Algorithm=DIGEST_METHOD_ALG)
    etree.SubElement(ref0, f"{{{DS}}}DigestValue").text = doc_digest

    # Reference 1: SignedProperties
    ref1 = etree.SubElement(
        si, f"{{{DS}}}Reference",
        Type="http://uri.etsi.org/01903#SignedProperties",
        URI=f"#{sp_id}",
    )
    etree.SubElement(ref1, f"{{{DS}}}DigestMethod", Algorithm=DIGEST_METHOD_ALG)
    dv_sp = etree.SubElement(ref1, f"{{{DS}}}DigestValue")

    # ========================================================================
    # Construir Signature completo
    # ========================================================================
    sig = etree.Element(
        f"{{{DS}}}Signature", nsmap={"ds": DS}, Id=sig_id
    )
    sig.append(si)

    # SignatureValue con Id (según XML oficial SRI)
    sv = etree.SubElement(sig, f"{{{DS}}}SignatureValue", Id=sig_value_id)

    # KeyInfo
    ki = etree.SubElement(sig, f"{{{DS}}}KeyInfo")
    xd = etree.SubElement(ki, f"{{{DS}}}X509Data")
    etree.SubElement(xd, f"{{{DS}}}X509Certificate").text = cert_b64

    # Object > QualifyingProperties > SignedProperties
    obj = etree.SubElement(sig, f"{{{DS}}}Object")
    qp = etree.SubElement(
        obj, f"{{{XADES}}}QualifyingProperties",
        nsmap={"xades": XADES, "xades141": XADES141},
        Target=f"#{sig_id}",
    )
    qp.append(sp)

    # Agregar firma al documento
    root.append(sig)

    # ========================================================================
    # Calcular digest de SignedProperties desde el árbol
    # ========================================================================
    sp_in_tree = root.find(f'.//*[@Id="{sp_id}"]')
    sp_c14n = etree.tostring(sp_in_tree, method="c14n")
    dv_sp.text = base64.b64encode(
        hashlib.sha256(sp_c14n).digest()
    ).decode()

    # ========================================================================
    # Firmar SignedInfo con RSA-SHA256
    # ========================================================================
    si_c14n = etree.tostring(si, method="c14n")
    signature_bytes = private_key.sign(
        si_c14n, padding.PKCS1v15(), hashes.SHA256()
    )
    sv.text = base64.b64encode(signature_bytes).decode()

    # ========================================================================
    # Serializar XML final
    # ========================================================================
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
    return xml_declaration + etree.tostring(root, encoding="unicode")


def firmar_xml_con_archivo(
    xml_str: str, p12_content: bytes, clave: str
) -> str:
    """
    Firma un XML usando el contenido del archivo .p12 en memoria.

    Args:
        xml_str: XML del comprobante
        p12_content: Contenido binario del archivo .p12
        clave: Contraseña del certificado

    Returns:
        XML firmado como string
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".p12") as tmp:
        tmp.write(p12_content)
        tmp_path = tmp.name
    try:
        return firmar_xml(xml_str, tmp_path, clave)
    finally:
        os.unlink(tmp_path)
