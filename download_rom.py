# -*- coding: utf-8 -*-
"""
Smart ROM Downloader for GitHub Actions / CLI
Supports Google Drive, PixelDrain, GoFile, and direct HTTP/HTTPS URLs.
"""
import sys, os, re, subprocess, urllib.request, json

def download_pixeldrain(url, dest_path):
    # e.g. https://pixeldrain.com/u/abc12345 -> https://pixeldrain.com/api/file/abc12345
    match = re.search(r'pixeldrain\.com/u/([a-zA-Z0-9]+)', url)
    if match:
        file_id = match.group(1)
        api_url = f"https://pixeldrain.com/api/file/{file_id}"
        print(f"[DOWNLOAD] PixelDrain detected. Converting to direct API link: {api_url}")
        return download_direct(api_url, dest_path)
    return False

def download_gofile(url, dest_path):
    # e.g. https://gofile.io/d/abc123
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

def download_direct(url, dest_path):
    print(f"[DOWNLOAD] Downloading directly from: {url}")
    # Try aria2c first for high speed if installed
    try:
        res = subprocess.run(["aria2c", "-x", "16", "-s", "16", "-o", os.path.basename(dest_path), "-d", os.path.dirname(dest_path), url])
        if res.returncode == 0 and os.path.exists(dest_path):
            return True
    except FileNotFoundError:
        pass

    # Fallback to python urllib with progress
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
        print("Usage: python download_rom.py <ROM_URL> <DEST_PATH>")
        sys.exit(1)

    url = sys.argv[1].strip()
    dest = os.path.abspath(sys.argv[2].strip())
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    print(f"[DOWNLOAD] Starting download for: {url}")
    print(f"[DOWNLOAD] Output path: {dest}")

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
