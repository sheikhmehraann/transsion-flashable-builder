# -*- coding: utf-8 -*-
"""
Hugging Face Permanent Unlimited Uploader for GitHub Actions / CLI
Uploads flashable ROM ZIPs to Hugging Face Datasets for 100% FREE permanent unlimited storage.
Direct Download Link Format: https://huggingface.co/datasets/<USER>/<REPO>/resolve/main/<FILENAME>.zip
"""
import sys, os, subprocess, json

def upload_to_huggingface(file_path, repo_id, token):
    if not os.path.isfile(file_path):
        print(f"[ERR] File not found: {file_path}")
        return None

    file_size_gb = os.path.getsize(file_path) / (1024**3)
    file_name = os.path.basename(file_path)

    print(f"[HF] Preparing Hugging Face permanent upload for {file_name} ({file_size_gb:.2f} GB)...")
    print(f"[HF] Target Repository: {repo_id}")

    try:
        print("[HF] Installing huggingface_hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "huggingface_hub"], check=True)
        from huggingface_hub import HfApi

        api = HfApi(token=token)

        print(f"[HF] Ensuring dataset repository '{repo_id}' exists...")
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
        except Exception as cre_err:
            print(f"[WARN] Create repo note: {cre_err}")

        print(f"[HF] Uploading {file_name} via LFS chunked stream to Hugging Face...")
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=file_name,
            repo_id=repo_id,
            repo_type="dataset"
        )

        direct_link = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_name}"

        print(f"\n" + "═"*68)
        print(f"  🚀 HUGGINGFACE PERMANENT UPLOAD SUCCESSFUL")
        print(f"  📦 File     : {file_name}")
        print(f"  💾 Size     : {file_size_gb:.2f} GB")
        print(f"  ♾️ Permanent : YES (100% Free, Unlimited, Never Expires)")
        print(f"  🔗 Link     : {direct_link}")
        print("═"*68 + "\n")

        # Generate GitHub Actions Step Summary
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            try:
                with open(summary_file, "a", encoding="utf-8") as sf:
                    sf.write(f"## ♾️ Permanent Unlimited Mirror on Hugging Face!\n\n")
                    sf.write(f"| Property | Value |\n")
                    sf.write(f"| :--- | :--- |\n")
                    sf.write(f"| **File Name** | `{file_name}` |\n")
                    sf.write(f"| **File Size** | `{file_size_gb:.2f} GB` |\n")
                    sf.write(f"| **Permanent Link** | [{direct_link}]({direct_link}) |\n\n")
                    sf.write(f"> 🔗 **Direct High-Speed Permanent Download:** [{direct_link}]({direct_link})\n\n")
            except Exception as se:
                print(f"[WARN] Step summary error: {se}")

        return direct_link

    except Exception as e:
        print(f"[ERR] Hugging Face upload failed: {e}")
        import traceback
        traceback.print_exc()

    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python hf_uploader.py <FILE_PATH> [HF_REPO] [HF_TOKEN]")
        sys.exit(1)

    filepath = os.path.abspath(sys.argv[1])
    repo_id = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else os.environ.get("HF_REPO")
    token = sys.argv[3].strip() if len(sys.argv) > 3 and sys.argv[3].strip() else os.environ.get("HF_TOKEN")

    if not repo_id or not token:
        print("[WARN] HF_REPO or HF_TOKEN not provided. Skipping Hugging Face upload.")
        sys.exit(0)

    link = upload_to_huggingface(filepath, repo_id, token)
    if not link:
        print("[WARN] Hugging Face permanent upload failed.")

if __name__ == "__main__":
    main()
