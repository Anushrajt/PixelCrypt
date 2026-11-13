"""
PixelCrypt - Dual-Layer Image Steganography System
==================================================
Dual-Layer Image Steganography & AES-256-GCM Cryptographic System.
Features:
- AES-256-GCM Authenticated Encryption with PBKDF2-HMAC-SHA256
- LSB Lossless Pixel Embedding & Extraction
- Live Steganalysis: MSE, PSNR (dB), 50x Difference Map, and RGB Histograms
- 1-Click Sample Image Loaders for Viva Demonstrations
"""

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

from src.crypto_engine import encrypt_message, decrypt_message
from src.stego_engine import encode_data_into_image, extract_data_from_image, calculate_capacity
from src.steganalysis import calculate_fidelity_metrics, generate_comparison_plot

app = Flask(__name__)
app.config["SECRET_KEY"] = "pixelcrypt-secret-key-2026"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
SAMPLE_DIR = os.path.join(BASE_DIR, "static", "sample_images")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "bmp", "webp", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def prune_uploads(max_files=30):
    """Keeps the upload folder tidy to avoid disk bloat on cloud containers."""
    try:
        files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if not f.startswith('.')]
        if len(files) > max_files:
            files.sort(key=os.path.getmtime)
            for f in files[:-max_files]:
                try:
                    os.remove(f)
                except OSError:
                    pass
    except Exception:
        pass


@app.route("/", methods=["GET"])
def index():
    """Main dashboard with Encode and Decode tabs."""
    samples = []
    if os.path.exists(SAMPLE_DIR):
        samples = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(".png")]
    return render_template("index.html", samples=samples)


@app.route("/encode", methods=["POST"])
def encode():
    """
    Handles encryption of plaintext using AES-256-GCM and embedding into carrier image.
    """
    secret_text = request.form.get("secret_text", "").strip()
    password = request.form.get("password", "").strip()
    sample_name = request.form.get("sample_image", "").strip()

    if not secret_text:
        return render_template("index.html", error_encode="Please enter a secret message to encrypt and hide.")
    if not password:
        return render_template("index.html", error_encode="Please provide an encryption passphrase.")

    carrier_path = None

    # Priority 1: User-uploaded custom image (e.g. from smartphone or PC)
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            ext = "png"
            unique_name = f"orig_{uuid.uuid4().hex[:8]}.{ext}"
            saved_path = os.path.join(UPLOAD_DIR, unique_name)
            
            # Correct smartphone orientation (EXIF) and convert to lossless RGB
            raw_img = Image.open(file.stream)
            img = ImageOps.exif_transpose(raw_img).convert("RGB")
            
            # Constrain to Full HD+ (max 1600px) - Razor-sharp on phones and projectors,
            # but guarantees RAM usage stays under 25 MB on Render's 512 MB free tier
            if max(img.size) > 1600:
                img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                
            img.save(saved_path, format="PNG")
            carrier_path = saved_path
            prune_uploads()

    # Priority 2: Sample image (only used if no user photo was uploaded)
    if not carrier_path and sample_name:
        candidate = os.path.join(SAMPLE_DIR, secure_filename(sample_name))
        if os.path.exists(candidate):
            carrier_path = candidate

    if not carrier_path:
        return render_template("index.html", error_encode="Please upload a photo or select a sample image.")

    try:
        # 1. AES-256-GCM Encrypt
        encrypted_payload = encrypt_message(secret_text, password)

        # 2. LSB Embed into Image with Innocent Camera Filename (Plausible Deniability)
        custom_name = request.form.get("custom_name", "").strip()
        if custom_name:
            if not custom_name.lower().endswith(".png"):
                custom_name += ".png"
            clean_name = secure_filename(custom_name)
            if not clean_name or clean_name == ".png":
                clean_name = f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            stego_filename = clean_name
        else:
            # Generate authentic smartphone / DSLR camera filename: IMG_YYYYMMDD_HHMMSS.png
            stego_filename = f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        stego_path = os.path.join(UPLOAD_DIR, stego_filename)
        meta = encode_data_into_image(carrier_path, encrypted_payload, stego_path)

        # 3. Calculate Fidelity & Plot
        plot_filename = f"analysis_{uuid.uuid4().hex[:8]}.png"
        plot_path = os.path.join(UPLOAD_DIR, plot_filename)
        metrics = calculate_fidelity_metrics(carrier_path, stego_path)
        generate_comparison_plot(carrier_path, stego_path, plot_path)

        encode_result = {
            "stego_filename": stego_filename,
            "stego_url": f"/static/uploads/{stego_filename}",
            "plot_url": f"/static/uploads/{plot_filename}",
            "payload_bytes": len(encrypted_payload),
            "plaintext_len": len(secret_text),
            "psnr_db": metrics["psnr_db"],
            "mse": metrics["mse"],
            "modified_percent": metrics["modified_percent"],
            "capacity_used": meta["capacity_used_percent"]
        }
        return render_template("index.html", encode_result=encode_result, active_tab="encode")

    except Exception as e:
        return render_template("index.html", error_encode=str(e), active_tab="encode")


@app.route("/decode", methods=["POST"])
def decode():
    """
    Extracts LSB binary payload from uploaded stego-image and decrypts with AES-256-GCM.
    """
    password = request.form.get("password", "").strip()
    if not password:
        return render_template("index.html", error_decode="Password is required to decrypt the stego vault.", active_tab="decode")

    if "stego_image" not in request.files:
        return render_template("index.html", error_decode="Please upload a stego-image to extract data from.", active_tab="decode")

    file = request.files["stego_image"]
    if not file or not file.filename:
        return render_template("index.html", error_decode="No file selected for extraction.", active_tab="decode")

    try:
        unique_name = f"inspect_{uuid.uuid4().hex[:8]}.png"
        inspect_path = os.path.join(UPLOAD_DIR, unique_name)
        img = Image.open(file.stream).convert("RGB")
        img.save(inspect_path, format="PNG")

        # 1. Extract raw binary payload from LSB
        extracted_payload = extract_data_from_image(inspect_path)

        # 2. Decrypt with AES-256-GCM
        decrypted_plaintext = decrypt_message(extracted_payload, password)

        decode_result = {
            "success": True,
            "message": decrypted_plaintext,
            "payload_size": len(extracted_payload),
            "auth_verified": True
        }
        return render_template("index.html", decode_result=decode_result, active_tab="decode")

    except Exception as e:
        return render_template("index.html", error_decode=str(e), active_tab="decode")


@app.route("/capacity", methods=["POST"])
def capacity():
    """API endpoint to calculate image capacity dynamically."""
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    file = request.files["image"]
    try:
        img = Image.open(file.stream).convert("RGB")
        cap = calculate_capacity(img)
        return jsonify(cap)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/download/<filename>")
def download(filename):
    """Download stego image."""
    safe_name = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, safe_name)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=safe_name)
    return "File not found", 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting PixelCrypt on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
