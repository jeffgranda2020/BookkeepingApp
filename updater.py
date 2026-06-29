import threading
import os
import sys
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from version import APP_VERSION, GITHUB_REPO, CHANGELOG

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
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

    pid = os.getpid()
    app_dir = os.path.dirname(current_exe)
    script_content = f'''@echo off
echo Updating 5StarBookKeeping...
echo Waiting for app to close...
:waitloop
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)
timeout /t 1 /nobreak >nul
REM Verify downloaded file is valid (at least 1MB)
for %%A in ("{downloaded_exe_path}") do set filesize=%%~zA
if %filesize% LSS 1000000 (
    echo Update file appears corrupt. Aborting to protect your data.
    del "{downloaded_exe_path}" >nul 2>&1
    pause
    exit /b 1
)
REM Backup current exe before replacing
if exist "{current_exe}" copy /Y "{current_exe}" "{current_exe}.bak" >nul 2>&1
set retries=0
:copyloop
copy /Y "{downloaded_exe_path}" "{current_exe}" >nul 2>&1
if errorlevel 1 (
    set /a retries+=1
    if %retries% GEQ 10 (
        echo Update failed. Restoring previous version...
        if exist "{current_exe}.bak" copy /Y "{current_exe}.bak" "{current_exe}" >nul 2>&1
        pause
        exit /b 1
    )
    timeout /t 2 /nobreak >nul
    goto copyloop
)
REM Clean up
del "{downloaded_exe_path}" >nul 2>&1
del "{current_exe}.bak" >nul 2>&1
echo Update complete. Your data (bookkeeping.db) is untouched.
echo Starting updated app...
timeout /t 3 /nobreak >nul
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
