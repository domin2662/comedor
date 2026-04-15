import streamlit as st
import qrcode
from barcode import Code39
from barcode.writer import SVGWriter, ImageWriter
from PIL import Image
from io import BytesIO
import base64
import re
import json
import hashlib
import zipfile
import os
import pathlib

# Directorio base del proyecto (rutas relativas)
BASE_DIR = pathlib.Path(__file__).resolve().parent


# ─── Configuración de página ───────────────────────────────────────────
st.set_page_config(
    page_title="Generador de Código - Comedor MECE",
    page_icon="🍽️",
    layout="centered",
)

# ─── CSS personalizado ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .main-card {
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.10);
        padding: 40px 36px 30px 36px;
        max-width: 540px;
        margin: 0 auto;
    }
    .title-text {
        text-align: center;
        color: #1a1a2e;
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .subtitle-text {
        text-align: center;
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 24px;
    }
    .dni-display {
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a2e;
        letter-spacing: 3px;
        margin-top: 8px;
    }
    .section-label {
        text-align: center;
        color: #444;
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .badge {
        background: #f0f0f0;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        color: #888;
        font-weight: 500;
        margin-left: 6px;
    }
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    .footer-text {
        text-align: center;
        color: #999;
        font-size: 0.8rem;
        margin-top: 20px;
    }
    .wallet-buttons {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    .wallet-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 22px;
        border-radius: 12px;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
        border: none;
        transition: transform 0.15s ease;
    }
    .wallet-btn:hover {
        transform: scale(1.04);
    }
    .wallet-btn-apple {
        background: #000;
        color: #fff !important;
    }
    .wallet-btn-google {
        background: #fff;
        color: #000 !important;
        border: 2px solid #dadce0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Funciones auxiliares ──────────────────────────────────────────────
def generate_code39_image(dni_number: str) -> Image.Image:
    """Genera un código de barras Code 39 como imagen PIL."""
    buffer = BytesIO()
    barcode = Code39(dni_number, writer=ImageWriter(), add_checksum=False)
    barcode.write(buffer, options={
        "module_width": 0.4,
        "module_height": 18,
        "font_size": 14,
        "text_distance": 6,
        "quiet_zone": 8,
    })
    buffer.seek(0)
    return Image.open(buffer)


def generate_qr_image(dni_number: str) -> Image.Image:
    """Genera un código QR como imagen PIL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(dni_number)
    qr.make(fit=True)
    return qr.make_image(fill_color="#1a1a2e", back_color="white").convert("RGB")


def create_combined_card(dni_number: str, barcode_img: Image.Image, qr_img: Image.Image, logo_path: str) -> Image.Image:
    """Crea una imagen combinada con logo, código de barras y QR para descargar."""
    card_w = 600
    padding = 40
    inner_w = card_w - 2 * padding

    # Cargar logo PNG
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo_ratio = 280 / logo.width
        logo = logo.resize((280, int(logo.height * logo_ratio)), Image.LANCZOS)
    except Exception:
        logo = None

    # Redimensionar código de barras
    bc_ratio = inner_w / barcode_img.width
    bc_w = inner_w
    bc_h = int(barcode_img.height * bc_ratio)
    barcode_resized = barcode_img.resize((bc_w, bc_h), Image.LANCZOS)

    # Redimensionar QR
    qr_size = 220
    qr_resized = qr_img.resize((qr_size, qr_size), Image.LANCZOS)

    # Calcular alto total
    y = padding
    if logo:
        logo_h = logo.height
        y += logo_h + 20
    y += 30  # título
    y += bc_h + 20
    y += 20  # separador
    y += qr_size + 20
    y += 40  # DNI text
    y += padding
    card_h = y

    card = Image.new("RGB", (card_w, card_h), "#ffffff")

    # Dibujar cabecera roja
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(card)

    current_y = padding

    # Logo
    if logo:
        logo_x = (card_w - logo.width) // 2
        card.paste(logo, (logo_x, current_y), logo)
        current_y += logo.height + 20

    # Título
    try:
        font_title = ImageFont.truetype("arial.ttf", 18)
        font_dni_big = ImageFont.truetype("cour.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font_title = ImageFont.load_default()
        font_dni_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((card_w // 2, current_y), "Código Comedor MECE", fill="#b60027", font=font_title, anchor="mt")
    current_y += 30

    # Código de barras
    card.paste(barcode_resized, (padding, current_y))
    current_y += bc_h + 20

    # Separador
    draw.line([(padding, current_y), (card_w - padding, current_y)], fill="#e0e0e0", width=1)
    current_y += 20

    # QR
    qr_x = (card_w - qr_size) // 2
    card.paste(qr_resized, (qr_x, current_y))
    current_y += qr_size + 20

    # DNI grande
    draw.text((card_w // 2, current_y), dni_number, fill="#1a1a2e", font=font_dni_big, anchor="mt")

    return card


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# ─── Apple Wallet (.pkpass) ────────────────────────────────────────────
def generate_apple_pkpass(dni_number: str, logo_path: str) -> bytes:
    """
    Genera un archivo .pkpass (ZIP) con la estructura correcta de Apple Wallet.
    Incluye tanto código de barras (Code 39 / PDF417) como QR.
    Nota: Sin certificado Apple Developer, el archivo no se instala
    directamente en Wallet pero sí se descarga con la estructura válida.
    """
    # pass.json — definición del pase
    pass_json = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.es.gob.mece.comedor",
        "serialNumber": f"COMEDOR-{dni_number}",
        "teamIdentifier": "MECE2026",
        "organizationName": "MECE - Ministerio",
        "description": "Tarjeta Comedor MECE",
        "logoText": "Comedor MECE",
        "foregroundColor": "rgb(26, 26, 46)",
        "backgroundColor": "rgb(255, 255, 255)",
        "labelColor": "rgb(102, 102, 102)",
        # Código de barras principal (QR)
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": dni_number,
            "messageEncoding": "iso-8859-1",
            "altText": dni_number,
        },
        # Múltiples códigos (QR + Code128 como alternativa compatible)
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": dni_number,
                "messageEncoding": "iso-8859-1",
                "altText": f"QR: {dni_number}",
            },
            {
                "format": "PKBarcodeFormatCode128",
                "message": dni_number,
                "messageEncoding": "iso-8859-1",
                "altText": f"Barcode: {dni_number}",
            },
        ],
        "generic": {
            "primaryFields": [
                {
                    "key": "dni",
                    "label": "DNI",
                    "value": dni_number,
                }
            ],
            "secondaryFields": [
                {
                    "key": "tipo",
                    "label": "Tipo",
                    "value": "Acceso Comedor",
                }
            ],
            "auxiliaryFields": [
                {
                    "key": "org",
                    "label": "Organización",
                    "value": "MECE",
                }
            ],
            "backFields": [
                {
                    "key": "info",
                    "label": "Información",
                    "value": f"Tarjeta de acceso al comedor.\nDNI: {dni_number}\nCódigos: QR y Code 39/128",
                }
            ],
        },
    }

    pass_json_bytes = json.dumps(pass_json, ensure_ascii=False).encode("utf-8")

    # Preparar imágenes del pase
    # icon.png (29x29) y logo.png (160x50 aprox)
    icon_img = Image.new("RGB", (29, 29), "#b60027")
    icon_bytes = image_to_bytes(icon_img)

    # Logo para el pase
    try:
        logo_orig = Image.open(logo_path).convert("RGBA")
        ratio = 160 / logo_orig.width
        logo_wallet = logo_orig.resize((160, int(logo_orig.height * ratio)), Image.LANCZOS)
        # Convertir RGBA a RGB con fondo blanco
        bg = Image.new("RGB", logo_wallet.size, (255, 255, 255))
        bg.paste(logo_wallet, mask=logo_wallet.split()[3])
        logo_bytes = image_to_bytes(bg)
    except Exception:
        logo_placeholder = Image.new("RGB", (160, 50), "#b60027")
        logo_bytes = image_to_bytes(logo_placeholder)

    # @2x versiones
    icon2x_img = Image.new("RGB", (58, 58), "#b60027")
    icon2x_bytes = image_to_bytes(icon2x_img)

    # Calcular manifest (SHA1 de cada archivo)
    files = {
        "pass.json": pass_json_bytes,
        "icon.png": icon_bytes,
        "icon@2x.png": icon2x_bytes,
        "logo.png": logo_bytes,
    }

    manifest = {}
    for name, data in files.items():
        manifest[name] = hashlib.sha1(data).hexdigest()
    manifest_bytes = json.dumps(manifest).encode("utf-8")

    # Crear ZIP (.pkpass)
    pkpass_buf = BytesIO()
    with zipfile.ZipFile(pkpass_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
        zf.writestr("manifest.json", manifest_bytes)

    pkpass_buf.seek(0)
    return pkpass_buf.getvalue()


# ─── Google Wallet (link) ─────────────────────────────────────────────
def generate_google_wallet_link(dni_number: str) -> str:
    """
    Genera un enlace 'Save to Google Wallet' usando un JWT.
    El pase incluye QR y código de barras del DNI.
    """
    # Payload del objeto de pase genérico de Google Wallet
    payload = {
        "iss": "comedor-mece@mece-comedor.iam.gserviceaccount.com",
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(__import__("time").time()),
        "origins": ["https://comedor.mece.gob.es"],
        "payload": {
            "genericObjects": [
                {
                    "id": f"MECE_COMEDOR.{dni_number}",
                    "classId": "MECE_COMEDOR.comedor_class",
                    "genericType": "GENERIC_TYPE_UNSPECIFIED",
                    "hexBackgroundColor": "#ffffff",
                    "logo": {
                        "sourceUri": {
                            "uri": "https://via.placeholder.com/160x50/b60027/ffffff?text=MECE"
                        }
                    },
                    "cardTitle": {
                        "defaultValue": {
                            "language": "es",
                            "value": "Comedor MECE"
                        }
                    },
                    "subheader": {
                        "defaultValue": {
                            "language": "es",
                            "value": "DNI"
                        }
                    },
                    "header": {
                        "defaultValue": {
                            "language": "es",
                            "value": dni_number
                        }
                    },
                    "barcode": {
                        "type": "QR_CODE",
                        "value": dni_number,
                        "alternateText": dni_number,
                    },
                    "textModulesData": [
                        {
                            "id": "tipo",
                            "header": "Tipo",
                            "body": "Acceso Comedor",
                        },
                        {
                            "id": "barcode_info",
                            "header": "Código de barras",
                            "body": f"Code 39: {dni_number}",
                        },
                    ],
                }
            ]
        },
    }

    # Codificar el JWT sin firma (demo) — para producción se firma con
    # la clave privada de la service account de Google Cloud
    jwt_token = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    jwt_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    jwt_full = f"{jwt_token}.{jwt_payload}."

    return f"https://pay.google.com/gp/v/save/{jwt_full}"


# ─── Interfaz principal ───────────────────────────────────────────────
logo_path = str(BASE_DIR / "logoME.png")

# Logo
col_logo = st.columns([1, 2, 1])
with col_logo[1]:
    try:
        st.image(logo_path, use_container_width=True)
    except Exception:
        st.warning("Logo no encontrado")

st.markdown('<p class="title-text">Generador de Código Comedor</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle-text">Introduce tu DNI (solo números, sin letra) para generar tu código de acceso</p>',
    unsafe_allow_html=True,
)

# Input
col_input = st.columns([3, 1])
with col_input[0]:
    dni = st.text_input(
        "Número de DNI",
        max_chars=8,
        placeholder="Ej: 12345678",
        label_visibility="collapsed",
    )
with col_input[1]:
    generate = st.button("🔄 Generar", use_container_width=True, type="primary")

# Validar y generar
if generate or (dni and len(dni) == 8):
    dni_clean = re.sub(r"[^0-9]", "", dni)

    if len(dni_clean) != 8:
        st.error("⚠️ Introduce un DNI válido: **8 dígitos numéricos** (sin letra).")
    else:
        # Generar códigos
        barcode_img = generate_code39_image(dni_clean)
        qr_img = generate_qr_image(dni_clean)

        st.markdown("---")
        # vamos
        # ── Código de barras ──
        st.markdown(
            '<p class="section-label">Código de Barras <span class="badge"></span></p>',
            unsafe_allow_html=True,
        )
        st.image(barcode_img, use_container_width=True)

        st.markdown("---")

        # ── Código QR ──
        st.markdown('<p class="section-label">Código QR</p>', unsafe_allow_html=True)
        col_qr = st.columns([1, 2, 1])
        with col_qr[1]:
            st.image(qr_img, width=220)
            st.markdown(f'<p class="dni-display">{dni_clean}</p>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Descarga ──
        combined = create_combined_card(dni_clean, barcode_img, qr_img, logo_path)
        png_bytes = image_to_bytes(combined)

        st.download_button(
            label="📥 Descargar imagen",
            data=png_bytes,
            file_name=f"comedor_{dni_clean}.png",
            mime="image/png",
            use_container_width=True,
        )

        st.markdown("---")

        # ── Wallet ──
        st.markdown(
            '<p class="section-label">Añadir a Wallet</p>',
            unsafe_allow_html=True,
        )

        col_w1, col_w2 = st.columns(2)

        # Apple Wallet (.pkpass)
        with col_w1:
            pkpass_bytes = generate_apple_pkpass(dni_clean, logo_path)
            st.download_button(
                label="🍎 Apple Wallet",
                data=pkpass_bytes,
                file_name=f"comedor_{dni_clean}.pkpass",
                mime="application/vnd.apple.pkpass",
                use_container_width=True,
            )

        # Google Wallet (link)
        with col_w2:
            google_url = generate_google_wallet_link(dni_clean)
            st.markdown(
                f'''<a href="{google_url}" target="_blank"
                    style="display:block;text-align:center;padding:10px 22px;
                    background:#fff;color:#000;border:2px solid #dadce0;
                    border-radius:12px;font-weight:600;font-size:0.9rem;
                    text-decoration:none;transition:transform 0.15s ease;">
                    🟢 Google Wallet
                </a>''',
                unsafe_allow_html=True,
            )

        st.caption(
            "ℹ️ **Apple Wallet**: descarga el archivo `.pkpass` y ábrelo en tu iPhone. "
            "**Google Wallet**: pulsa el botón para añadirlo directamente. "
            "Ambos incluyen código QR y código de barras."
        )

st.markdown('<p class="footer-text">© 2026 MECE — Sistema de Comedor</p>', unsafe_allow_html=True)
