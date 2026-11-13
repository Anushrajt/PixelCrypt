"""
Steganography Engine - LSB (Least Significant Bit) Pixel Matrix Encoder
======================================================================
Hides and extracts arbitrary binary payloads into lossless RGB image matrices.
Features:
- Magic Marker signature (b"CSTG") for instantaneous carrier verification
- 32-bit Big-Endian payload length prefix
- 1-bit-per-channel LSB modulation (R, G, B) preserving visual imperceptibility
- Capacity calculation based on image width, height, and color channels
- Strict lossless PNG preservation
"""

import os
import struct
import numpy as np
from PIL import Image

MAGIC_MARKER = b"CSTG"  # 4 bytes
HEADER_SIZE = len(MAGIC_MARKER) + 4  # 8 bytes (64 bits)


def calculate_capacity(img: Image.Image) -> dict:
    """
    Calculates the maximum hidden data capacity of an image in bits, bytes, and KB.
    """
    img = img.convert("RGB")
    width, height = img.size
    total_channels = width * height * 3
    usable_bytes = (total_channels // 8) - HEADER_SIZE
    
    return {
        "width": width,
        "height": height,
        "total_pixels": width * height,
        "usable_bytes": max(0, usable_bytes),
        "usable_kb": round(max(0, usable_bytes) / 1024, 2)
    }


def encode_data_into_image(image_input, binary_payload: bytes, output_path: str) -> dict:
    """
    Embeds a binary payload into the Least Significant Bits of an image.
    Saves the resulting stego-image as a lossless PNG to output_path.
    """
    if isinstance(image_input, str):
        img = Image.open(image_input).convert("RGB")
    else:
        img = image_input.convert("RGB")

    width, height = img.size
    cap = calculate_capacity(img)

    full_payload = MAGIC_MARKER + struct.pack(">I", len(binary_payload)) + binary_payload
    required_bits = len(full_payload) * 8

    if required_bits > (width * height * 3):
        raise ValueError(
            f"Payload too large for this image! Required: {len(full_payload)} bytes, "
            f"Image Maximum Capacity: {cap['usable_bytes'] + HEADER_SIZE} bytes."
        )

    # Convert binary payload to an array of individual bits (0 or 1)
    bits = np.unpackbits(np.frombuffer(full_payload, dtype=np.uint8))

    # Convert image to numpy array of shape (height, width, 3)
    img_array = np.array(img, dtype=np.uint8)
    flat_channels = img_array.flatten()

    # Embed bits into Least Significant Bit: clear LSB (val & 254) and set with bit (val | bit)
    flat_channels[:len(bits)] = (flat_channels[:len(bits)] & np.uint8(254)) | bits

    # Reshape back to image array
    stego_array = flat_channels.reshape((height, width, 3))
    stego_image = Image.fromarray(stego_array, mode="RGB")

    # Ensure output directory exists and save as PNG (Lossless)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    stego_image.save(output_path, format="PNG")

    return {
        "output_path": output_path,
        "embedded_bytes": len(binary_payload),
        "total_payload_bytes": len(full_payload),
        "capacity_used_percent": round((len(full_payload) / (cap['usable_bytes'] + HEADER_SIZE)) * 100, 2),
        "width": width,
        "height": height
    }


def extract_data_from_image(image_input) -> bytes:
    """
    Extracts binary payload from the LSBs of a stego-image.
    Returns bytes or raises ValueError if no valid stego signature is found.
    """
    if isinstance(image_input, str):
        img = Image.open(image_input).convert("RGB")
    else:
        img = image_input.convert("RGB")

    img_array = np.array(img, dtype=np.uint8)
    flat_channels = img_array.flatten()

    # Extract header (64 bits = 8 bytes)
    header_bits = flat_channels[:HEADER_SIZE * 8] & 1
    header_bytes = np.packbits(header_bits).tobytes()

    magic = header_bytes[:4]
    if magic != MAGIC_MARKER:
        raise ValueError("No steganographic payload detected! This image does not contain a Crypto-Stego signature.")

    payload_length = struct.unpack(">I", header_bytes[4:8])[0]
    total_bits_needed = (HEADER_SIZE + payload_length) * 8

    if total_bits_needed > len(flat_channels):
        raise ValueError("Corrupt steganographic header: declared payload length exceeds image size.")

    # Extract all payload bits
    payload_bits = flat_channels[HEADER_SIZE * 8:total_bits_needed] & 1
    extracted_payload = np.packbits(payload_bits).tobytes()

    return extracted_payload


if __name__ == "__main__":
    # Self-test using a generated test image
    test_img = Image.new("RGB", (400, 300), color=(120, 180, 240))
    test_file = "test_carrier.png"
    out_file = "test_stego.png"
    test_img.save(test_file)

    secret = b"CONFIDENTIAL_AGENT_CIPHER_PAYLOAD_12345"
    print(f"[*] Embedding {len(secret)} bytes...")
    encode_data_into_image(test_file, secret, out_file)

    print("[*] Extracting hidden data...")
    extracted = extract_data_from_image(out_file)
    print(f"[+] Extracted: {extracted.decode('utf-8')}")

    assert secret == extracted, "Extraction failed!"
    print("[*] LSB Steganography Engine PASSED perfectly!")

    # Cleanup
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(out_file): os.remove(out_file)
