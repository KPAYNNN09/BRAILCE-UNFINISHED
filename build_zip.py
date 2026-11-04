import os
import zipfile

zip_filename = "brailce_update.zip"

exclude_dirs = {
    ".git", ".pytest_cache", "__pycache__", "venv", ".vscode", ".idea", ".gemini",
    "frames_360p", "sub_scans", "video_frames", "BRAILCE TYPING AND AI ONLY"
}
exclude_exts = {".pyc", ".pyo", ".zip", ".mp4"}
exclude_files = {
    "yolov8_braille.pt", "scotto_details.json", "video_page.html", "ytInitialData.json"
}

print(f"Creating {zip_filename}...")
with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in exclude_exts or f.startswith("scratch") or f in exclude_files:
                continue
            full_path = os.path.join(root, f)
            arcname = os.path.relpath(full_path, ".")
            zipf.write(full_path, arcname)

size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
print(f"Created {zip_filename} ({size_mb:.2f} MB)")

