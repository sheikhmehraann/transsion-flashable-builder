# Transsion Flashable Builder ⚡ (Ubuntu Cloud & Local Automation)

> Automated end-to-end cloud and local pipeline for converting Transsion (Infinix, Tecno, itel) MediaTek / Unisoc stock firmware dumps into custom recovery-flashable ZIPs with A/B slot support via native `lptools` and `imgkit`.

---

## 🚀 Key Architectural Features & Upgrades

### 1. Ubuntu Cloud Builder Pipeline (`ubuntu-latest`)
- **Automated Workflow**: Run directly on GitHub Actions without downloading multi-gigabyte firmware to your local PC.
- **Native MIO-KITCHEN 4.2.0 Linux Toolchain**: 20 native 64-bit Linux ELF binaries (`imgkit`, `lpmake`, `simg2img`, `zstd`, `extract.erofs`, `mkfs.erofs`, `cpio`, `busybox`, `brotli`, `magiskboot`, `e2fsdroid`) stored in `bin/linux/`.

### 2. Smart Multi-Source ROM Downloader Engine (`download_rom.py`)
- **SourceForge Direct Engine**: Automatic project mirror resolution (`https://downloads.sourceforge.net/project/...`) with `User-Agent: curl/7.88.1` header bypass for max-speed direct downloads.
- **Multi-Cloud Support**: PixelDrain API, Needrom session authenticated engine, Google Drive (`gdown`), Mega.py, GoFile API, and raw octet-streams via `aria2c` / `requests`.

### 3. Maximum Ultra Compression Engine
- **ZSTD Level 19 Ultra (`-19 --ultra -T0`)**: Compresses dynamic partitions (`system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm`) with maximum compression density. Multi-threaded execution (`-T0`) utilizes all available CPU cores.
- **Multi-Threaded 7z Fast Packaging (`7z a -tzip -mx=9 -mmt=on`)**: Packages the final flashable ZIP using multi-threaded 7-Zip engines for 10x faster execution.

### 4. Robust GoFile Release Engine (`gofile_uploader.py`)
- Dynamic GoFile API server resolution (`https://api.gofile.io/servers`) auto-discovers active upload nodes (`store-eu-par-5`, `store-eu-par-7`, `store3`, `store1`).
- Automatic fallback loop ensures error-free uploads and renders an aesthetic GitHub Step Summary card with direct download links.

---

## 📊 Validated Build Benchmark (Infinix GT 20 Pro X6871)

| Parameter | Value / Specification |
| :--- | :--- |
| **Device Name** | Infinix GT 20 Pro |
| **Codename** | `X6871` |
| **Firmware Version** | `X6871-15.1.2.145SP02(OP001PF001AZ)` |
| **Region** | `Open` |
| **Source ROM** | SourceForge Direct Download (`8.45 GB`) |
| **Built Flashable ROM** | `X6871-15.1.2.145SP02(OP001PF001AZ)-recovery-ab.zip` (`7.74 GB`) |
| **Workflow Run** | [View Run #31619163946 on GitHub Actions](https://github.com/sheikhmehraann/transsion-flashable-builder/actions/runs/31619163946) |
| **Live GoFile Link** | [https://gofile.io/d/4XQ9CTTu](https://gofile.io/d/4XQ9CTTu) |

---

## ⚡ How to Build via GitHub Actions

1. Go to **[sheikhmehraann/transsion-flashable-builder Actions](https://github.com/sheikhmehraann/transsion-flashable-builder/actions)**.
2. Select **Build Flashable ROM & Upload to GoFile**.
3. Click **Run workflow** and input:
   - **rom_url**: SourceForge, Needrom, Google Drive, Mega, PixelDrain, or GoFile URL.
   - **device_name**: `Infinix GT 20 Pro`
   - **codename**: `X6871`
   - **fw_version**: `X6871-15.1.2.145SP02(OP001PF001AZ)`
   - **region**: `Open`
4. Click **Run workflow**. Upon completion, your GoFile download link will appear directly on the Job Summary page!

---

## 🛠️ Flashing Architecture

The generated `update-binary` shell script performs these automated steps on the target device:

```
1. Flash raw firmware images (lk, tee, spmfw, logo, etc.) → raw writes to both Slot A and Slot B
2. Execute lptools clear-cow
3. Execute lptools destroy + create dynamic partitions
4. Execute lptools map dynamic partitions
5. Flash raw system images (boot, dtbo, vbmeta, init_boot) → raw writes to both Slot A and Slot B
6. Stream-decompress dynamic partitions (system, vendor, product, etc.) via arm64 zstd binary → active slot
7. Execute final unmap + map for clean device boot state
```

---

## 📁 Repository Structure

```
transsion-flashable-builder/
├── .github/workflows/
│   └── build_rom.yml                # GitHub Actions Cloud Builder Workflow
├── bin/
│   ├── linux/                        # Native 64-bit Linux ELF tools (MIO-KITCHEN 4.2.0)
│   │   ├── imgkit, lpmake, zstd, simg2img, brotli, busybox, cpio, extract.erofs...
│   └── windows/                      # Windows executable tools
│       ├── imgkit.exe, lpmake.exe, zstd.exe, simg2img.exe...
├── transsion_flashable_builder.py    # Local GUI Application (Tkinter)
├── build_cli.py                      # Headless CLI Engine
├── download_rom.py                   # Multi-source smart download engine
├── gofile_uploader.py                # GoFile dynamic server API uploader
├── README.md
├── LICENSE
└── requirements.txt
```

---

## 💳 Credits & License

- **Mehraan** — Core Author & Maintainer
- Built with MediaTek / Transsion `lptools` dynamic partition management approach.
- Uses Facebook [Zstandard (zstd)](https://github.com/facebook/zstd) for compression.
- Released under the [MIT License](LICENSE).
