"""
Steganalysis & Quantitative Image Fidelity Metrics
=================================================
Calculates Mean Squared Error (MSE), Peak Signal-to-Noise Ratio (PSNR),
and generates comparative RGB color histograms to prove visual imperceptibility.
"""

import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib_cache"))
import math
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def calculate_fidelity_metrics(original_img_path: str, stego_img_path: str) -> dict:
    """
    Computes MSE and PSNR (Peak Signal-to-Noise Ratio) in decibels (dB).
    PSNR > 50 dB indicates visual distortion is completely imperceptible to human eyes.
    """
    img1 = Image.open(original_img_path).convert("RGB")
    img2 = Image.open(stego_img_path).convert("RGB")

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    if arr1.shape != arr2.shape:
        raise ValueError("Images must have identical dimensions for fidelity analysis.")

    # Mean Squared Error (MSE)
    mse = np.mean((arr1 - arr2) ** 2)

    if mse == 0:
        psnr = 100.0  # Perfect identical match
    else:
        max_pixel = 255.0
        psnr = 10 * math.log10((max_pixel ** 2) / mse)

    # Count modified pixels
    diff = np.abs(arr1 - arr2)
    modified_pixels = int(np.sum(np.any(diff > 0, axis=-1)))
    total_pixels = arr1.shape[0] * arr1.shape[1]

    return {
        "mse": round(float(mse), 6),
        "psnr_db": round(float(psnr), 2),
        "total_pixels": total_pixels,
        "modified_pixels": modified_pixels,
        "modified_percent": round((modified_pixels / total_pixels) * 100, 3),
        "imperceptible": psnr >= 50.0
    }


def generate_comparison_plot(original_img_path: str, stego_img_path: str, output_plot_path: str):
    """
    Generates a 3-panel comparative analysis plot:
    1. Original vs. Stego visual side-by-side
    2. 50x Amplified Pixel Difference Heatmap
    3. RGB Channel Histogram overlay proving statistical preservation
    """
    img1 = Image.open(original_img_path).convert("RGB")
    img2 = Image.open(stego_img_path).convert("RGB")

    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)

    # Amplified difference (multiplied by 50 to make 1-bit shifts visible to camera)
    diff = np.abs(arr1 - arr2) * 50.0
    diff = np.clip(diff, 0, 255).astype(np.uint8)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Original
    axes[0, 0].imshow(img1)
    axes[0, 0].set_title("Original Carrier Image", fontsize=12, fontweight="bold")
    axes[0, 0].axis("off")

    # 2. Stego Image
    axes[0, 1].imshow(img2)
    axes[0, 1].set_title("Stego-Image (With Hidden Encrypted Data)", fontsize=12, fontweight="bold")
    axes[0, 1].axis("off")

    # 3. Amplified Difference Map
    axes[1, 0].imshow(diff)
    axes[1, 0].set_title("Amplified Difference Map (50x Contrast)", fontsize=12, fontweight="bold")
    axes[1, 0].axis("off")

    # 4. RGB Histograms
    colors = ("red", "green", "blue")
    for i, col in enumerate(colors):
        hist_orig, _ = np.histogram(arr1[:, :, i], bins=64, range=(0, 256))
        hist_stego, _ = np.histogram(arr2[:, :, i], bins=64, range=(0, 256))
        axes[1, 1].plot(hist_orig, color=col, linestyle="--", alpha=0.5, label=f"Orig {col.upper()}")
        axes[1, 1].plot(hist_stego, color=col, linestyle="-", alpha=0.8, label=f"Stego {col.upper()}")

    axes[1, 1].set_title("RGB Color Histogram Overlap (Statistically Preserved)", fontsize=12, fontweight="bold")
    axes[1, 1].set_xlabel("Pixel Intensity Range (0-255)")
    axes[1, 1].set_ylabel("Pixel Frequency")
    axes[1, 1].legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_plot_path)), exist_ok=True)
    plt.savefig(output_plot_path, dpi=200, bbox_inches="tight")
    plt.close()
    return output_plot_path
