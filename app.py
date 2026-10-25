import os
import sys
import json
import base64
import io
import shutil
from ftplib import FTP

import py7zr
from PIL import Image
import webview

FTP_HOST = ""
FTP_USER = ""
FTP_PASS = ""


def resource_path(relative_path):
    """
    Resolve a path to a bundled READ-ONLY resource (index.html, lib/, app.ico)
    so it works both when running as a normal .py script AND when running as
    a frozen PyInstaller .exe (which unpacks files to a temp _MEIPASS dir).
    """
    try:
        base_path = sys._MEIPASS  # set by PyInstaller at runtime
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def app_dir():
    """
    Folder the .exe (or .py) itself lives in — used for things we WRITE,
    like downloaded files. _MEIPASS is a temp folder that gets deleted, so
    downloads must NOT go there.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


LOCAL_DIR = os.path.join(app_dir(), "downloads")
EXTRACT_DIR = os.path.join(LOCAL_DIR, ".extracted")
TEMP_DIR = os.path.join(LOCAL_DIR, ".tmp")  # holds a .7z only while it's being extracted

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
# Formats a browser can show as-is; anything else is converted to PNG.
BROWSER_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
THUMB_SIZE = (150, 150)


# ---------------------------------------------------------------------------
# Extracting images out of a .7z archive
# ---------------------------------------------------------------------------

def _collect_images(folder):
    images = []
    for dirpath, _, filenames in os.walk(folder):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in IMAGE_EXTS:
                images.append(os.path.join(dirpath, fn))
    return sorted(images)


def get_extracted_image_paths(archive_path):
    """Extract only the image files from the .7z archive into a per-archive
    folder (skipped if already extracted) and return their paths. If the
    archive has no images, or extraction fails, the empty folder is removed
    so it doesn't show up in the list or block a later re-download."""
    archive_name = os.path.splitext(os.path.basename(archive_path))[0]
    out_dir = os.path.join(EXTRACT_DIR, archive_name)

    if os.path.isdir(out_dir):
        images = _collect_images(out_dir)
        if images:
            return images

    os.makedirs(out_dir, exist_ok=True)
    try:
        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            image_names = [
                n for n in archive.getnames()
                if os.path.splitext(n)[1].lower() in IMAGE_EXTS
            ]
            if image_names:
                archive.extract(path=out_dir, targets=image_names)
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

    images = _collect_images(out_dir)
    if not images:
        shutil.rmtree(out_dir, ignore_errors=True)
    return images


def _safe_path(path):
    """Return the real path if it is inside EXTRACT_DIR, else None. Keeps the
    page from asking Python to read arbitrary files."""
    if not path:
        return None
    try:
        real = os.path.realpath(path)
        root = os.path.realpath(EXTRACT_DIR)
        if os.path.commonpath([real, root]) == root and real != root:
            return real
    except ValueError:  # e.g. different drives on Windows
        pass
    return None


def list_ftp_folders(ftp, path):
    """Return a sorted list of folder names at the given FTP path, using an
    already-connected FTP session."""
    ftp.cwd("/")
    if path and path != "/":
        ftp.cwd(path)
    names = []
    try:
        for name, facts in ftp.mlsd():
            if facts.get("type") == "dir":
                names.append(name)
    except Exception:
        names = ftp.nlst()
    return sorted(names)


def search_and_fetch(sn, status_cb=None):
    """Walk every work order / station folder on the FTP server looking for
    files whose name starts with sn and ends with .7z. Each match is
    downloaded to a temp file, its images are extracted, and the .7z is then
    deleted - only the extracted images are kept. If an archive was already
    extracted in a previous run, it is not downloaded again.
    status_cb(text), if given, is called with progress updates."""
    downloaded = []
    searched_paths = 0

    def report(text):
        if status_cb:
            try:
                status_cb(text)
            except Exception:
                pass

    with FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)

        work_orders = list_ftp_folders(ftp, "")
        for wo in work_orders:
            try:
                stations = list_ftp_folders(ftp, wo)
            except Exception:
                continue

            for station in stations:
                path = f"{wo}/{station}"
                searched_paths += 1
                report(f"Searching {path} ...")

                try:
                    ftp.cwd("/")
                    ftp.cwd(path)
                    files = ftp.nlst()
                except Exception:
                    continue

                matches = [f for f in files if f.startswith(sn) and f.endswith(".7z")]
                for match in matches:
                    archive_name = os.path.splitext(match)[0]
                    out_dir = os.path.join(EXTRACT_DIR, archive_name)

                    if os.path.isdir(out_dir) and _collect_images(out_dir):
                        # Already fetched & extracted previously.
                        downloaded.append((path, match, archive_name))
                        continue

                    os.makedirs(TEMP_DIR, exist_ok=True)
                    temp_path = os.path.join(TEMP_DIR, match)

                    report(f"Downloading {match} ...")
                    with open(temp_path, "wb") as f:
                        ftp.retrbinary(f"RETR {match}", f.write)

                    try:
                        report(f"Extracting {match} ...")
                        get_extracted_image_paths(temp_path)
                    finally:
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass

                    downloaded.append((path, match, archive_name))

    return downloaded, searched_paths


class Api:
    """Exposed to the page as window.pywebview.api.<method>(...)."""

    def __init__(self):
        self._window = None  # set after the window is created, below

    def _status(self, text):
        if self._window:
            try:
                self._window.evaluate_js(
                    f"window.updateFetchStatus && window.updateFetchStatus({json.dumps(text)})"
                )
            except Exception:
                pass

    def fetch_by_sn(self, sn):
        sn = (sn or "").strip()
        if not sn:
            return {"ok": False, "error": "Enter a serial number."}

        try:
            downloaded, searched_paths = search_and_fetch(sn, status_cb=self._status)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        if not downloaded:
            return {
                "ok": False,
                "error": f"No files found for SN {sn} "
                         f"(searched {searched_paths} station folder(s)).",
            }

        return {
            "ok": True,
            "files": [f"{path}/{match}" for path, match, _ in downloaded],
            "archives": [name for _, _, name in downloaded],
            "folder": EXTRACT_DIR,
        }

    # ---- Downloaded-images browsing -------------------------------------

    def list_downloads(self):
        """Extracted archive folders (that contain images), newest first."""
        if not os.path.isdir(EXTRACT_DIR):
            return []
        entries = []
        for name in os.listdir(EXTRACT_DIR):
            full = os.path.join(EXTRACT_DIR, name)
            if os.path.isdir(full) and not name.startswith("."):
                if _collect_images(full):
                    entries.append((os.path.getmtime(full), name))
        entries.sort(reverse=True)
        return [name for _, name in entries]

    def get_images(self, archive_name):
        """Image list for one extracted archive: [{path, name}, ...]."""
        if not archive_name or os.path.basename(archive_name) != archive_name:
            return []
        folder = _safe_path(os.path.join(EXTRACT_DIR, archive_name))
        if not folder or not os.path.isdir(folder):
            return []
        return [
            {"path": p, "name": os.path.basename(p)}
            for p in _collect_images(folder)
        ]

    def get_thumbnail(self, path):
        """Small JPEG thumbnail as a data: URL (or None on failure)."""
        real = _safe_path(path)
        if not real:
            return None
        try:
            with Image.open(real) as im:
                im.thumbnail(THUMB_SIZE, Image.LANCZOS)
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None

    def get_image(self, path):
        """Full-size image as a data: URL (or None on failure). Formats a
        browser can't display (BMP, TIFF) are converted to PNG."""
        real = _safe_path(path)
        if not real:
            return None
        ext = os.path.splitext(real)[1].lower()
        try:
            if ext in BROWSER_MIME:
                with open(real, "rb") as f:
                    data = f.read()
                mime = BROWSER_MIME[ext]
            else:
                with Image.open(real) as im:
                    if im.mode not in ("RGB", "RGBA", "L"):
                        im = im.convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, format="PNG")
                data = buf.getvalue()
                mime = "image/png"
            return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
        except Exception:
            return None

    def open_downloads_folder(self):
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        try:
            os.startfile(EXTRACT_DIR)  # Windows only
        except AttributeError:
            return {"ok": False, "error": f"Extracted images folder: {EXTRACT_DIR}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}


def main():
    index_path = resource_path("index.html")
    icon_path = resource_path("app.ico")

    api = Api()

    window = webview.create_window(
        "Audio Test Log Analyzer",
        index_path,
        width=1440,
        height=900,
        min_size=(1000, 700),
        js_api=api,
    )
    api._window = window

    # `icon=` sets the window/taskbar icon while the app is running.
    # Requires pywebview 4.1+ — if your installed version doesn't
    # support this kwarg, this line will raise TypeError; drop the
    # icon= argument below and rely on the .exe's own icon instead
    # (set via --icon in build.bat), which Windows will still show
    # in the taskbar.
    webview.start(icon=icon_path)


if __name__ == "__main__":
    main()
