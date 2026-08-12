# -*- coding: utf-8 -*-
"""
Smart ROM Downloader for GitHub Actions / CLI
Supports Needrom, Mega.nz, Google Drive, PixelDrain, GoFile, and direct HTTP/HTTPS URLs.
"""
import sys, os, re, subprocess, urllib.request, json

def download_pixeldrain(url, dest_path):
    match = re.search(r'pixeldrain\.com/u/([a-zA-Z0-9]+)', url)
    if match:
        file_id = match.group(1)
        api_url = f"https://pixeldrain.com/api/file/{file_id}"
        print(f"[DOWNLOAD] PixelDrain detected. Converting to direct API link: {api_url}")
        return download_direct(api_url, dest_path)
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
            with urllib.request.urlopen(req) as resp:
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
    if "drive.google.com" in url or "drive.usercontent.google.com" in url:
        print("[DOWNLOAD] Google Drive link detected. Using gdown...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "gdown"], check=True)
            cmd = [sys.executable, "-m", "gdown", url, "-O", dest_path, "--fuzzy"]
            res = subprocess.run(cmd)
            return res.returncode == 0
        except Exception as e:
            print(f"[ERR] gdown failed: {e}")
            return False
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
            return os.path.exists(dest_path)
        except Exception as e:
            print(f"[ERR] Mega download failed: {e}")
            return False
    return False

def download_needrom(url, dest_path, user=None, password=None, cookie=None):
    if "needrom.com" not in url:
        return False
    print(f"[DOWNLOAD] Needrom link detected: {url}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        user = user or os.environ.get("NEEDROM_USER")
        password = password or os.environ.get("NEEDROM_PASS")
        cookie = cookie or os.environ.get("NEEDROM_COOKIE")

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
            session.post(login_url, data=login_data, allow_redirects=True)

        resp = session.get(url)
        # Look for mirrors or file links (Mega, Google Drive, Needrom direct download links)
        matches = re.findall(r'href=["\'](https?://[^"\']*(?:mega\.nz|drive\.google\.com|pixeldrain\.com|gofile\.io|needrom\.com/download/file[^"\']*))["\']', resp.text, re.IGNORECASE)

        if matches:
            real_url = matches[0]
            print(f"[DOWNLOAD] Found target download link inside Needrom page: {real_url}")
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
        print(f"[ERR] Needrom download handler failed: {e}")
        return False

def download_direct(url, dest_path, session=None):
    print(f"[DOWNLOAD] Downloading directly from: {url}")
    try:
        if session:
            resp = session.get(url, stream=True)
            if resp.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                return True
    except Exception as e:
        print(f"[WARN] Session direct download failed: {e}")

    try:
        res = subprocess.run(["aria2c", "-x", "16", "-s", "16", "-o", os.path.basename(dest_path), "-d", os.path.dirname(dest_path), url])
        if res.returncode == 0 and os.path.exists(dest_path):
            return True
    except FileNotFoundError:
        pass

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
            total_length = response.getheader('content-length')
            if total_length:
                total_length = int(total_length)
                dl = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    dl += len(chunk)
                    out_file.write(chunk)
                    done = int(50 * dl / total_length)
                    print(f"\r  [{'=' * done}{' ' * (50-done)}] {dl/(1024*1024):.1f}/{total_length/(1024*1024):.1f} MB", end='', flush=True)
                print()
            else:
                out_file.write(response.read())
        return True
    except Exception as e:
        print(f"[ERR] Direct download failed: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python download_rom.py <ROM_URL> <DEST_PATH> [NEEDROM_USER] [NEEDROM_PASS]")
        sys.exit(1)

    url = sys.argv[1].strip()
    dest = os.path.abspath(sys.argv[2].strip())
    user = sys.argv[3].strip() if len(sys.argv) > 3 else None
    password = sys.argv[4].strip() if len(sys.argv) > 4 else None

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"[DOWNLOAD] Starting download for: {url}")

    if download_needrom(url, dest, user, password):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_mega(url, dest):
        print("[DOWNLOAD] SUCCESS!")
        sys.exit(0)

    if download_pixeldrain(url, dest):
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

    print("[ERR] All download methods failed.")
    sys.exit(1)

if __name__ == "__main__":
    main()
