# -*- coding: utf-8 -*-
"""
GoFile Uploader for GitHub Actions / CLI
Uploads flashable ROM ZIP to GoFile and prints the download link.
"""
import sys, os, urllib.request, json

def upload_to_gofile(file_path, token=None):
    if not os.path.isfile(file_path):
        print(f"[ERR] File not found: {file_path}")
        return None

    file_size_gb = os.path.getsize(file_path) / (1024**3)
    print(f"[GOFILE] Uploading {os.path.basename(file_path)} ({file_size_gb:.2f} GB) to GoFile...")

    url = "https://upload.gofile.io/uploadfile"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        # Use curl if available for streaming large multipart uploads (RAM friendly)
        import subprocess
        cmd = ["curl", "-X", "POST", url, "-F", f"file=@{file_path}"]
        if token:
            cmd.extend(["-H", f"Authorization: Bearer {token}"])
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            res_data = json.loads(proc.stdout)
            if res_data.get("status") == "ok":
                download_page = res_data["data"]["downloadPage"]
                print(f"\n" + "="*60)
                print(f"  [GOFILE UPLOAD SUCCESS]")
                print(f"  Download URL: {download_page}")
                print("="*60 + "\n")
                
                # Append to GitHub Actions summary if present
                summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
                if summary_file:
                    with open(summary_file, "a", encoding="utf-8") as sf:
                        sf.write(f"### 🚀 Flashable ROM Ready!\n")
                        sf.write(f"- **File:** `{os.path.basename(file_path)}` ({file_size_gb:.2f} GB)\n")
                        sf.write(f"- **Download Link:** [{download_page}]({download_page})\n")
                return download_page
            else:
                print(f"[ERR] GoFile response status not OK: {res_data}")
        else:
            print(f"[ERR] Curl upload failed: {proc.stderr}")
    except Exception as e:
        print(f"[ERR] Upload failed: {e}")

    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python gofile_uploader.py <FILE_PATH> [GOFILE_TOKEN]")
        sys.exit(1)

    filepath = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GOFILE_TOKEN")

    link = upload_to_gofile(filepath, token)
    if not link:
        sys.exit(1)

if __name__ == "__main__":
    main()
