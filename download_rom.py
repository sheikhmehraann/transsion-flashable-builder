# -*- coding: utf-8 -*-
"""
Universal High-Speed ROM Downloader Engine
Supports: SourceForge, Needrom, Google Drive (Virus Bypass), Mega.nz, PixelDrain, GoFile, MediaFire, 1Fichier, Terabox, and Direct HTTP/HTTPS URLs.
"""
import sys, os, re, subprocess, urllib.request, json, requests, html

def is_valid_rom_file(dest_path, min_size_mb=10):
    if not os.path.isfile(dest_path):
        return False
    size = os.path.getsize(dest_path)
    if size < min_size_mb * 1024 * 1024:
        print(f"[WARN] Downloaded file size ({size / (1024*1024):.2f} MB) is smaller than minimum ROM threshold ({min_size_mb} MB).")
        try:
            with open(dest_path, 'rb') as f:
                head = f.read(512).lower()
                if b'<!doctype html' in head or b'<html' in head or b'{"error"' in head or b'quota' in head or b'access denied' in head:
                    print("[ERR] Downloaded content is an HTML/JSON error page, not a valid ROM archive!")
        except Exception:
            pass
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

    try:
        with open(dest_path, 'rb') as f:
            head = f.read(512).lower()
            if b'<!doctype html' in head or b'<html' in head or b'access denied' in head:
                print("[ERR] Downloaded file is an HTML web page, not a valid archive!")
                os.remove(dest_path)
                return False
    except Exception:
        pass
    return True

def download_mediafire(url, dest_path):
    if "mediafire.com" in url:
        print(f"[DOWNLOAD] MediaFire link detected: {url}")
        try:
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            resp = session.get(url, timeout=15)
            match = re.search(r'href=["\'](https?://download\d+\.mediafire\.com/[^"\']+)["\']', resp.text)
            if match:
                direct_url = match.group(1)
                print(f"[DOWNLOAD] Direct MediaFire download URL extracted: {direct_url}")
                return download_direct(direct_url, dest_path, session=session)
        except Exception as e:
            print(f"[WARN] MediaFire extraction error: {e}")
    return False

def download_pixeldrain(url, dest_path):
    match = re.search(r'pixeldrain\.com/u/([a-zA-Z0-9]+)', url)
    if match:
        file_id = match.group(1)
        api_url = f"https://pixeldrain.com/api/file/{file_id}"
        print(f"[DOWNLOAD] PixelDrain detected. Direct API link: {api_url}")
        return download_direct(api_url, dest_path)
    return False

def download_sourceforge(url, dest_path):
    if "sourceforge.net" in url:
        print(f"[DOWNLOAD] SourceForge link detected: {url}")
        match = re.search(r'sourceforge\.net/projects/([^/]+)/files/(.+?)(?:/download)?(?:\?.*)?$', url)
        if match:
            project, file_path = match.group(1), match.group(2)
            direct_url = f"https://downloads.sourceforge.net/project/{project}/{file_path}?use_mirror=fastly"
        else:
            direct_url = url if "use_mirror=" in url else f"{url}?use_mirror=fastly"

        print(f"[DOWNLOAD] Fastly SourceForge Mirror URL: {direct_url}")
        return download_direct(direct_url, dest_path)
    return False

def download_gofile(url, dest_path):
    match = re.search(r'gofile\.io/d/([a-zA-Z0-9]+)', url)
    if match:
        content_id = match.group(1)
        print(f"[DOWNLOAD] GoFile link detected: {content_id}")
        try:
            req = urllib.request.Request(
                f"https://api.gofile.io/contents/{content_id}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("status") == "ok" and "children" in data.get("data", {}):
                    children = data["data"]["children"]
                    first_file = next(iter(children.values()))
                    direct_link = first_file["link"]
                    print(f"[DOWNLOAD] Direct GoFile link found: {direct_link}")
                    return download_direct(direct_link, dest_path)
        except Exception as e:
            print(f"[WARN] GoFile API extraction failed: {e}")
    return False

def download_gdrive(url, dest_path):
    if "drive.google.com" not in url and "drive.usercontent.google.com" not in url and not (len(url.strip()) >= 25 and '/' not in url.strip()):
        return False

    print(f"[DOWNLOAD] Google Drive link detected: {url}")
    file_id = None
    match = re.search(r'(?:file/d/|id=|d/)([a-zA-Z0-9_-]{25,})', url)
    if match:
        file_id = match.group(1)
    elif len(url.strip()) >= 25 and '/' not in url.strip():
        file_id = url.strip()

    # Strategy 1: gdown library
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "gdown"], check=True)
        import gdown
        print(f"[GDRIVE] Strategy 1: Attempting download via gdown (ID: {file_id or 'URL'})...")
        if file_id:
            gdown.download(id=file_id, output=dest_path, quiet=False, use_cookies=True)
        else:
            gdown.download(url=url, output=dest_path, quiet=False, use_cookies=True)

        if is_valid_rom_file(dest_path):
            print("[GDRIVE] Strategy 1 (gdown) Succeeded!")
            return True
    except Exception as e:
        print(f"[GDRIVE] Strategy 1 (gdown) failed: {e}")

    # Strategy 2: Direct Virus Warning Form Bypass Engine
    if file_id:
        print(f"[GDRIVE] Strategy 2: Form-based Virus Warning Bypass Engine for ID: {file_id}...")
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            })
            base_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            resp = session.get(base_url, timeout=15)

            action_match = re.search(r'action=["\']([^"\']+)["\']', resp.text)
            if action_match:
                action_url = action_match.group(1)
                inputs = dict(re.findall(r'name=["\']([^"\']+)["\']\s+value=["\']([^"\']*)["\']', resp.text))
                print(f"[GDRIVE] Extracted virus warning form parameters: {inputs}")

                stream_resp = session.get(action_url, params=inputs, stream=True, timeout=30)
                if stream_resp.status_code == 200:
                    content_type = stream_resp.headers.get("Content-Type", "").lower()
                    if "text/html" in content_type:
                        if "quota exceeded" in stream_resp.text.lower() or "too many users" in stream_resp.text.lower():
                            print("[ERR] CRITICAL: Google Drive quota limit exceeded for this file!")
                            return False

                    total_len = stream_resp.headers.get("Content-Length")
                    print(f"[GDRIVE] Streaming download (Length: {total_len or 'Unknown'})...")
                    with open(dest_path, "wb") as f:
                        dl = 0
                        for chunk in stream_resp.iter_content(chunk_size=2 * 1024 * 1024):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                if total_len:
                                    done = int(50 * dl / int(total_len))
                                    print(f"\r  [{'=' * done}{' ' * (50-done)}] {dl/(1024*1024):.1f}/{int(total_len)/(1024*1024):.1f} MB", end="", flush=True)
                                else:
                                    print(f"\r  Downloaded {dl/(1024*1024):.1f} MB", end="", flush=True)
                        print()

                    if is_valid_rom_file(dest_path):
                        print("[GDRIVE] Strategy 2 (Form Bypass) Succeeded!")
                        return True
        except Exception as e:
            print(f"[GDRIVE] Strategy 2 (Form Bypass) failed: {e}")

    if os.path.exists(dest_path):
        os.remove(dest_path)
    return False

def download_mega(url, dest_path):
    if "mega.nz" in url or "mega.co.nz" in url:
        print("[DOWNLOAD] Mega link detected. Installing mega.py...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "mega.py"], check=True)
            from mega import Mega
            mega = Mega()
            m = mega.login()
            print("[DOWNLOAD] Downloading from Mega...")
            m.download_url(url, os.path.dirname(dest_path), os.path.basename(dest_path))
            return is_valid_rom_file(dest_path)
        except Exception as e:
            print(f"[ERR] Mega download failed: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False
    return False

def download_needrom(url, dest_path, user=None, password=None, cookie=None):
    if "needrom.com" not in url:
        return False

    print(f"[DOWNLOAD] Needrom link detected: {url}")
    user = user or os.environ.get("NEEDROM_USER")
    password = password or os.environ.get("NEEDROM_PASS")
    cookie = cookie or os.environ.get("NEEDROM_COOKIE")

    if "/server/download.php" in url or "name=" in url:
        print("[DOWNLOAD] Direct Needrom server download link detected.")
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        return download_direct(url, dest_path, headers=headers)

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.needrom.com/"
        })
        
        if cookie:
            print("[DOWNLOAD] Using Needrom session cookie")
            session.headers.update({"Cookie": cookie})
        elif user and password:
            print(f"[DOWNLOAD] Logging into Needrom as {user}...")
            login_url = "https://www.needrom.com/wp-login.php"
            login_data = {
                "log": user,
                "pwd": password,
                "wp-submit": "Log In",
                "redirect_to": url,
                "testcookie": "1"
            }
            session.post(login_url, data=login_data, allow_redirects=True, timeout=15)

        resp = session.get(url, timeout=15)
        matches = re.findall(r'href=["\'](https?://[^"\']*(?:server/download|mega\.nz|drive\.google\.com|pixeldrain\.com|gofile\.io)[^"\']*)["\']', resp.text, re.IGNORECASE)

        if matches:
            real_url = matches[0]
            print(f"[DOWNLOAD] Extracted target link from Needrom page: {real_url}")
            if "mega.nz" in real_url or "mega.co.nz" in real_url:
                return download_mega(real_url, dest_path)
            elif "drive.google.com" in real_url:
                return download_gdrive(real_url, dest_path)
            elif "pixeldrain.com" in real_url:
                return download_pixeldrain(real_url, dest_path)
            elif "gofile.io" in real_url:
                return download_gofile(real_url, dest_path)
            else:
                return download_direct(real_url, dest_path, session=session)
        else:
            return download_direct(url, dest_path, session=session)
    except Exception as e:
        print(f"[ERR] Needrom page download handler failed: {e}")
        return download_direct(url, dest_path)

def download_direct(url, dest_path, session=None, headers=None):
    if "drive.google.com" in url or "drive.usercontent.google.com" in url:
        print("[WARN] Skipping direct curl/aria2 download for Google Drive URL.")
        return False

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    
    # Resolve 302 redirects first to obtain final direct CDN domain
    target_url = url
    try:
        req_headers = {"User-Agent": ua}
        if headers:
            req_headers.update(headers)
        r = requests.head(url, headers=req_headers, allow_redirects=True, timeout=10)
        if r.url:
            target_url = r.url
            print(f"[DOWNLOAD] Resolved direct CDN endpoint: {target_url}")
    except Exception:
        pass

    print(f"[DOWNLOAD] Streaming download from: {target_url}")

    # Try aria2c first for 16-thread multi-connection gigabit speed
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        cmd = [
            "aria2c",
            "-x", "16",
            "-s", "16",
            "-k", "1M",
            "--file-allocation=none",
            "--summary-interval=5",
            "--console-log-level=notice",
            f"--user-agent={ua}",
            "-o", os.path.basename(dest_path),
            "-d", os.path.dirname(dest_path)
        ]
        if headers and "Cookie" in headers:
            cmd.extend(["--header", f"Cookie: {headers['Cookie']}"])
        cmd.append(target_url)

        res = subprocess.run(cmd)
        if res.returncode == 0 and is_valid_rom_file(dest_path):
            return True
        if os.path.exists(dest_path):
            os.remove(dest_path)
    except FileNotFoundError:
        pass

    # Try curl if aria2c unavailable
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        cmd = ["curl", "-L", "-A", ua, "-o", dest_path]
        if headers and "Cookie" in headers:
            cmd.extend(["-H", f"Cookie: {headers['Cookie']}"])
        cmd.append(target_url)
        res = subprocess.run(cmd)
        if res.returncode == 0 and is_valid_rom_file(dest_path):
            return True
        if os.path.exists(dest_path):
            os.remove(dest_path)
    except Exception:
        pass

    # Fallback to Python requests with stream retry
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        req_headers = {"User-Agent": ua}
        if headers:
            req_headers.update(headers)
        
        req_session = session if session else requests.Session()
        resp = req_session.get(target_url, headers=req_headers, allow_redirects=True, stream=True, timeout=30)
        if resp.status_code in (200, 206):
            total_len = int(resp.headers.get('content-length', 0))
            dl = 0
            with open(dest_path, 'wb') as out_file:
                for chunk in resp.iter_content(chunk_size=4 * 1024 * 1024):
                    if chunk:
                        out_file.write(chunk)
                        dl += len(chunk)
                        if total_len > 0:
                            done = int(50 * dl / total_len)
                            print(f"\r  [{'=' * done}{' ' * (50-done)}] {dl/(1024*1024):.1f}/{total_len/(1024*1024):.1f} MB", end='', flush=True)
            print()
            return is_valid_rom_file(dest_path)
    except Exception as e:
        print(f"[ERR] Requests download fallback error: {e}")

    if os.path.exists(dest_path) and not is_valid_rom_file(dest_path):
        os.remove(dest_path)
    return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python download_rom.py <ROM_URL> <DEST_PATH> [NEEDROM_USER] [NEEDROM_PASS] [NEEDROM_COOKIE]")
        sys.exit(1)

    url = sys.argv[1].strip()
    dest = os.path.abspath(sys.argv[2].strip())
    user = sys.argv[3].strip() if len(sys.argv) > 3 and sys.argv[3].strip() else None
    password = sys.argv[4].strip() if len(sys.argv) > 4 and sys.argv[4].strip() else None
    cookie = sys.argv[5].strip() if len(sys.argv) > 5 and sys.argv[5].strip() else None

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"[DOWNLOAD] Initializing high-speed downloader engine for: {url}")

    if download_needrom(url, dest, user, password, cookie):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_mega(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_pixeldrain(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_mediafire(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_sourceforge(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_gofile(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_gdrive(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_direct(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    print("[ERR] All download strategies failed or file validation failed.")
    sys.exit(1)

if __name__ == "__main__":
    main()
