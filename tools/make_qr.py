"""
Make a QR code PNG for your deployed app.

    pip install "qrcode[pil]"
    python tools/make_qr.py https://your-app-name.streamlit.app
"""
import sys

try:
    import qrcode
except ImportError:
    sys.exit('Install it first:  pip install "qrcode[pil]"')

if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
    sys.exit("Usage: python tools/make_qr.py https://your-app-name.streamlit.app")

url = sys.argv[1]
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=14, border=3)
qr.add_data(url)
qr.make(fit=True)
qr.make_image(fill_color="#111111", back_color="#FFF6D6").save("docs/qr_code.png")
print(f"Saved docs/qr_code.png for {url}")
