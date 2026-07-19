"""
Resize/compress item photos before GCS upload.
Skips brand assets (logo, favicon, default).
"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, "app", "static", "images")

MAX_WIDTH = 1200
MAX_HEIGHT = 800
QUALITY = 82

EXCLUDE_PREFIXES = ("logo", "favicon", "apple-touch", "android-chrome")
EXCLUDE_NAMES = {"default.jpg", "default.png", "og_image.png"}


def should_skip(filename: str) -> bool:
    lower = filename.lower()
    if lower in EXCLUDE_NAMES:
        return True
    return any(lower.startswith(p) for p in EXCLUDE_PREFIXES)


def optimize(filepath: str):
    try:
        with Image.open(filepath) as img:
            original_size = os.path.getsize(filepath)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
            # Always write JPEG for item thumbs
            out_path = os.path.splitext(filepath)[0] + ".jpg"
            img.save(out_path, "JPEG", quality=QUALITY, optimize=True)
            if out_path != filepath and os.path.isfile(filepath) and filepath.lower().endswith(".png"):
                # leave non-default pngs if somehow present; item pipeline uses jpg
                pass
            new_size = os.path.getsize(out_path)
            print(
                f"✅ {os.path.basename(out_path)}: "
                f"{original_size // 1024}KB -> {new_size // 1024}KB"
            )
    except Exception as e:
        print(f"❌ {os.path.basename(filepath)}: {e}")


def run():
    if not os.path.exists(IMAGES_DIR):
        print("❌ images directory not found")
        return

    targets = [
        os.path.join(IMAGES_DIR, f)
        for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and not should_skip(f)
    ]

    if not targets:
        print("No images to optimize")
        return

    print(f"🖼️  Optimizing {len(targets)} images...")
    for path in targets:
        optimize(path)
    print("🎉 Image optimization complete")


if __name__ == "__main__":
    run()
