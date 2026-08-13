# -*- coding: utf-8 -*-
"""
High-Speed GoFile Uploader Engine for GitHub Actions & CLI
Uploads flashable ROM ZIPs to GoFile via dynamic server resolution API.
"""
import sys, os, urllib.request, json, subprocess

CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

def get_gofile_servers():
    servers_list = []
    try:
        req = urllib.request.Request("https://api.gofile.io/servers", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "ok":
                srvs = data.get("data", {}).get("servers", [])
                for s in srvs:
                    if s.get("name"):
                        servers_list.append(s["name"])
    except Exception as e:
        print(f"{YELLOW}[WARN] Failed to fetch GoFile active server list: {e}{RESET}")
    
    if not servers_list:
        servers_list = ["store-eu-par-7", "store-eu-par-5", "store9", "store8", "store3", "store1"]
    return servers_list

def upload_to_gofile(file_path, token=None):
    if not os.path.isfile(file_path):
        print(f"[ERR] File not found: {file_path}")
        return None

    file_size_gb = os.path.getsize(file_path) / (1024**3)
    file_name = os.path.basename(file_path)
    
    servers = get_gofile_servers()
    print(f"{CYAN}[GOFILE] Discovered active storage nodes: {', '.join(servers[:4])}{RESET}")
    print(f"{CYAN}[GOFILE] Streaming {file_name} ({file_size_gb:.2f} GB) to GoFile Cloud...{RESET}")

    for server_name in servers[:4]:
        upload_urls = [
            f"https://{server_name}.gofile.io/contents/uploadfile",
            f"https://{server_name}.gofile.io/uploadFile"
        ]

        for url in upload_urls:
            print(f"  ➜ Attempting connection to: {url}")
            cmd = ["curl", "-s", "-X", "POST", url, "-F", f"file=@{file_path}"]
            if token:
                cmd.extend(["-H", f"Authorization: Bearer {token}"])

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
                if proc.returncode == 0 and proc.stdout:
                    try:
                        res_data = json.loads(proc.stdout)
                        if res_data.get("status") == "ok":
                            download_page = res_data.get("data", {}).get("downloadPage")
                            if download_page:
                                print(f"\n{GREEN}" + "═"*66 + f"{RESET}")
                                print(f"{GREEN}  🚀 GOFILE UPLOAD SUCCESSFUL{RESET}")
                                print(f"  📦 File     : {BOLD}{file_name}{RESET}")
                                print(f"  💾 Size     : {BOLD}{file_size_gb:.2f} GB{RESET}")
                                print(f"  🔗 Download : {GREEN}{BOLD}{download_page}{RESET}")
                                print(f"{GREEN}" + "═"*66 + f"\n{RESET}")
                                
                                # Generate GitHub Actions Step Summary
                                summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
                                if summary_file:
                                    try:
                                        with open(summary_file, "a", encoding="utf-8") as sf:
                                            sf.write(f"# ⚡ Flashable ROM Published to GoFile!\n\n")
                                            sf.write(f"| Property | Value |\n")
                                            sf.write(f"| :--- | :--- |\n")
                                            sf.write(f"| **File Name** | `{file_name}` |\n")
                                            sf.write(f"| **File Size** | `{file_size_gb:.2f} GB` |\n")
                                            sf.write(f"| **Download Mirror** | [{download_page}]({download_page}) |\n\n")
                                            sf.write(f"### 📥 Direct GoFile Mirror\n\n")
                                            sf.write(f"> 🔗 **[Click Here to Download Flashable ROM]({download_page})**\n\n")
                                    except Exception as se:
                                        print(f"{YELLOW}[WARN] Failed to write step summary: {se}{RESET}")

                                return download_page
                    except json.JSONDecodeError:
                        print(f"{YELLOW}[WARN] Non-JSON response from {url}{RESET}")
                else:
                    print(f"{YELLOW}[WARN] Connection retry for {url}{RESET}")
            except Exception as e:
                print(f"{YELLOW}[WARN] Upload exception for {url}: {e}{RESET}")

    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python gofile_uploader.py <FILE_PATH> [GOFILE_TOKEN]")
        sys.exit(1)

    filepath = os.path.abspath(sys.argv[1])
    token = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].strip() else os.environ.get("GOFILE_TOKEN")

    link = upload_to_gofile(filepath, token)
    if not link:
        print(f"[ERR] GoFile upload failed across all endpoints.")
        sys.exit(1)

if __name__ == "__main__":
    main()
