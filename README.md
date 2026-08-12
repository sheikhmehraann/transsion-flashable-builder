<div align="center">

# ⚡ TRANSSION FLASHABLE BUILDER ⚡
### *Next-Gen Automated Recovery Flashable ROM Engine for Transsion Devices*

[![Build Status](https://img.shields.io/github/actions/workflow/status/sheikhmehraann/transsion-flashable-builder/build_rom.yml?branch=master&style=for-the-badge&logo=githubactions&logoColor=white&color=00F0FF)](https://github.com/sheikhmehraann/transsion-flashable-builder/actions)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-FFD43B?style=for-the-badge&logo=python&logoColor=black)](https://python.org)
[![Platform Support](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Windows-7B2CBF?style=for-the-badge&logo=ubuntu&logoColor=white)](https://github.com/sheikhmehraann/transsion-flashable-builder)
[![Compression](https://img.shields.io/badge/ZSTD-Level%2019%20Ultra-FF007F?style=for-the-badge&logo=fastapi&logoColor=white)](https://github.com/facebook/zstd)
[![License](https://img.shields.io/badge/License-MIT-00E676?style=for-the-badge&logo=open-source-initiative&logoColor=black)](LICENSE)

---

```
  ████████╗██████╗  █████╗ ███╗   ██╗███████╗███████╗██╗ ██████╗ ███╗   ██╗
  ╚══██╔══╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔════╝██║██╔═══██╗████╗  ██║
     ██║   ██████╔╝███████║██╔██╗ ██║███████╗███████╗██║██║   ██║██╔██╗ ██║
     ██║   ██╔══██╗██╔══██║██║╚██╗██║╚════██║╚════██║██║██║   ██║██║╚██╗██║
     ██║   ██║  ██║██║  ██║██║ ╚████║███████║███████║██║╚██████╔╝██║ ╚████║
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
               ⚡ CLOUD & LOCAL RECOVERY FLASHABLE BUILDER ⚡
```

<p align="center">
  <b>Automated end-to-end cloud and local pipeline converting stock firmware dumps (Infinix / Tecno / itel) into recovery-flashable ZIP packages with full A/B dual-slot flashing via <code>lptools</code>.</b>
</p>

</div>

---

> [!IMPORTANT]
> **No Local High-End Hardware Required!** You can build full 8GB+ recovery flashable packages directly in the cloud using **GitHub Actions** on high-speed Ubuntu runners with automatic **GoFile** hosting delivery!

---

## 🔥 Key Architectural Features

<details open>
<summary><b>1. ☁️ Ubuntu Cloud Builder Engine (ubuntu-latest)</b></summary>

- **Fully Automated Workflow**: Trigger builds via `workflow_dispatch` directly on GitHub without downloading multi-gigabyte files locally.
- **Native MIO-KITCHEN 4.2.0 Linux Toolchain**: Deploys 20 native 64-bit Linux ELF tools (`imgkit`, `lpmake`, `simg2img`, `zstd`, `extract.erofs`, `mkfs.erofs`, `cpio`, `busybox`, `brotli`, `magiskboot`, `e2fsdroid`) located in `bin/linux/`.
</details>

<details open>
<summary><b>2. 🌐 Smart Multi-Source Downloader Engine (download_rom.py)</b></summary>

- **SourceForge Direct Engine**: Auto-resolves SourceForge project links to `https://downloads.sourceforge.net/project/...` with `User-Agent: curl/7.88.1` header bypass for max-speed streaming.
- **Universal Cloud Support**: Supports PixelDrain API, Needrom session-authenticated downloads, Google Drive (`gdown`), Mega.py, GoFile API, and raw streams via `aria2c`.
</details>

<details open>
<summary><b>3. ⚡ Maximum Ultra Compression (ZSTD 19 + 7z Multi-Thread)</b></summary>

- **ZSTD Level 19 Ultra (`-19 --ultra -T0`)**: Compresses dynamic partitions (`system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm`) at peak compression density using multi-core parallel processing (`-T0`).
- **Multi-Threaded 7z Fast Packaging (`7z a -tzip -mx=9 -mmt=on`)**: Packages the flashable ZIP using multi-threaded 7-Zip engines for 10x faster execution.
</details>

<details open>
<summary><b>4. 📤 Dynamic GoFile Release Engine (gofile_uploader.py)</b></summary>

- Dynamic GoFile API server resolution (`https://api.gofile.io/servers`) auto-discovers active upload nodes (`store-eu-par-5`, `store-eu-par-7`, `store3`, `store1`).
- Renders an aesthetic **GitHub Action Step Summary** card with direct download URLs upon completion.
</details>

---

## 📊 Validated Build Benchmarks

<div align="center">

| Metric | Target Specification |
| :--- | :--- |
| **📱 Device Name** | **Infinix GT 20 Pro** |
| **🏷️ Codename** | `X6871` |
| **📦 Firmware Version** | `X6871-15.1.2.145SP02(OP001PF001AZ)` |
| **🌏 Region** | `Open` |
| **📥 Source ROM** | SourceForge Direct Mirror (`8.45 GB`) |
| **⚡ Built Flashable ROM** | `X6871-15.1.2.145SP02(OP001PF001AZ)-recovery-ab.zip` (`7.74 GB`) |
| **⚙️ Build Execution Time** | `20 minutes 23 seconds` (`ubuntu-latest`) |
| **🚀 Direct Download** | **[Download via GoFile](https://gofile.io/d/4XQ9CTTu)** |

</div>

---

## 🚀 How to Build via GitHub Actions

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Open GitHub Actions tab in repository                                │
│ 2. Select "Build Flashable ROM & Upload to GoFile"                      │
│ 3. Click "Run workflow" and fill in device metadata & ROM URL           │
│ 4. Click "Run workflow" → Wait 15-20 mins for GoFile download link!     │
└─────────────────────────────────────────────────────────────────────────┘
```

> [!TIP]
> You can pass any ROM URL: SourceForge download links, Needrom URLs, Google Drive links, PixelDrain links, or direct HTTP/HTTPS file URLs!

---

## 🛠️ On-Device Flashing Pipeline

The generated `update-binary` shell script executes these steps automatically during custom recovery installation (TWRP / OrangeFox):

```
 ┌────────────────────────────────────────────────────────┐
 │ 1. Flash raw firmware images → Both Slot A & Slot B    │
 │ 2. Execute lptools clear-cow                           │
 │ 3. Execute lptools destroy + create dynamic partitions │
 │ 4. Execute lptools map dynamic partitions              │
 │ 5. Flash raw system images → Both Slot A & Slot B      │
 │ 6. Stream-decompress Zstd dynamic images → Active Slot │
 │ 7. Final unmap + map for clean boot state              │
 └────────────────────────────────────────────────────────┘
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

<div align="center">

### 💳 Credits & License

Designed with ❤️ by **Mehraan**
<br>
Built with MediaTek / Transsion `lptools` dynamic partition management approach.
<br>
Uses Facebook [Zstandard (zstd)](https://github.com/facebook/zstd) for ultra-compression.
<br><br>
Released under the [MIT License](LICENSE).

</div>
