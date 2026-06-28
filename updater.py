import threading
import os
import sys
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from version import APP_VERSION, GITHUB_REPO, CHANGELOG

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_version(v):
    return tuple(int(x) for x in v.lstrip("v").split("."))


def check_for_updates(callback):
    """Check GitHub Releases for a newer version. Runs in background thread.
    callback(new_version, changelog_text, download_url) called if update found.
    callback(None, None, None) if no update or error.
    """
    def _check():
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = Request(url, headers={"Accept": "application/vnd.github.v3+json"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            latest_tag = data.get("tag_name", "")
            latest_version = latest_tag.lstrip("v")

            if _parse_version(latest_version) > _parse_version(APP_VERSION):
                body = data.get("body", "")
                assets = data.get("assets", [])
                download_url = None
                for asset in assets:
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                if not download_url:
                    for asset in assets:
                        if asset["name"].endswith(".zip"):
                            download_url = asset["browser_download_url"]
                            break
                if not download_url:
                    download_url = data.get("html_url", "")
                callback(latest_version, body, download_url)
            else:
                callback(None, None, None)
        except (URLError, json.JSONDecodeError, KeyError, ValueError):
            callback(None, None, None)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()


def download_update(download_url, progress_callback=None):
    """Download the update .exe to a temp file. Returns the temp file path.
    progress_callback(bytes_downloaded, total_bytes) called periodically.
    Runs in calling thread — call from a background thread.
    """
    req = Request(download_url, headers={"Accept": "application/octet-stream"})
    with urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".exe", dir=tempfile.gettempdir())
        downloaded = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            tmp.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)
        tmp.close()
    return tmp.name


def apply_update(downloaded_exe_path):
    """Launch the updater script and exit the current app.
    The script waits for this process to exit, replaces the exe, and relaunches.
    """
    if getattr(sys, 'frozen', False):
        current_exe = sys.executable
    else:
        current_exe = os.path.abspath(sys.argv[0])

    script_content = f'''@echo off
echo Updating 5StarBookKeeping...
timeout /t 2 /nobreak >nul
copy /Y "{downloaded_exe_path}" "{current_exe}" >nul
if errorlevel 1 (
    echo Update failed. Please close the app and try again.
    pause
    exit /b 1
)
del "{downloaded_exe_path}" >nul 2>&1
start "" "{current_exe}"
del "%~f0" >nul 2>&1
'''

    script_path = os.path.join(tempfile.gettempdir(), "_5star_updater.bat")
    with open(script_path, "w") as f:
        f.write(script_content)

    os.startfile(script_path)
    sys.exit(0)


def get_changelog_text():
    """Return formatted changelog for all versions."""
    lines = []
    for version in sorted(CHANGELOG.keys(), key=_parse_version, reverse=True):
        lines.append(f"Version {version}")
        lines.append("-" * 40)
        for item in CHANGELOG[version]:
            lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines)
