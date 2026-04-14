import streamlit as st
import qrcode
from barcode import Code39
from barcode.writer import SVGWriter, ImageWriter
from PIL import Image
from io import BytesIO
import base64
import re


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

    # Logo SVG omitido (no se convierte a imagen)
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


# ─── Interfaz principal ───────────────────────────────────────────────
logo_path = "logo-MECE (1).svg"

# Logo
col_logo = st.columns([1, 2, 1])
with col_logo[1]:
    try:
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        st.markdown(
            f'<div style="text-align:center;">{svg_content}</div>',
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
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

st.markdown('<p class="footer-text">© 2026 MECE — Sistema de Comedor</p>', unsafe_allow_html=True)
