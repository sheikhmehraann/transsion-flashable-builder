# -*- coding: utf-8 -*-
"""
Smart Multi-Host Uploader for GitHub Actions / CLI
Uploads flashable ROM ZIP to GoFile (dynamic server API) and GitHub Releases.
"""
import sys, os, urllib.request, json, subprocess

def get_best_gofile_server():
    try:
        req = urllib.request.Request("https://api.gofile.io/servers", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "ok":
                servers = data.get("data", {}).get("servers", [])
                if servers:
                    return servers[0]["name"]
    except Exception as e:
        print(f"[WARN] Failed to get GoFile server list: {e}")
    return "store1"

def upload_to_gofile(file_path, token=None):
    if not os.path.isfile(file_path):
        print(f"[ERR] File not found: {file_path}")
        return None

    file_size_gb = os.path.getsize(file_path) / (1024**3)
    server_name = get_best_gofile_server()
    print(f"[GOFILE] Selected GoFile server: {server_name}")
    print(f"[GOFILE] Uploading {os.path.basename(file_path)} ({file_size_gb:.2f} GB) to GoFile...")

    upload_urls = [
        f"https://{server_name}.gofile.io/contents/uploadfile",
        f"https://{server_name}.gofile.io/uploadFile",
        "https://api.gofile.io/contents/uploadfile",
        "https://store1.gofile.io/contents/uploadfile"
    ]

    for url in upload_urls:
        print(f"[GOFILE] Attempting upload to: {url}")
        cmd = ["curl", "-s", "-X", "POST", url, "-F", f"file=@{file_path}"]
        if token:
            cmd.extend(["-H", f"Authorization: Bearer {token}"])

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            if proc.returncode == 0 and proc.stdout:
                try:
                    res_data = json.loads(proc.stdout)
                    if res_data.get("status") == "ok":
                        download_page = res_data.get("data", {}).get("downloadPage")
                        if download_page:
                            print(f"\n" + "="*60)
                            print(f"  [GOFILE UPLOAD SUCCESS]")
                            print(f"  Download URL: {download_page}")
                            print("="*60 + "\n")
                            return download_page
                except json.JSONDecodeError:
                    print(f"[WARN] Non-JSON response from {url}: {proc.stdout[:200]}")
            else:
                print(f"[WARN] Curl exit code {proc.returncode} for {url}")
        except Exception as e:
            print(f"[WARN] Upload error for {url}: {e}")

    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python gofile_uploader.py <FILE_PATH> [GOFILE_TOKEN]")
        sys.exit(1)

    filepath = os.path.abspath(sys.argv[1])
    token = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].strip() else os.environ.get("GOFILE_TOKEN")

    link = upload_to_gofile(filepath, token)
    if not link:
        print("[WARN] GoFile upload failed, falling back to GitHub Actions summary.")
        sys.exit(1)

if __name__ == "__main__":
    main()
