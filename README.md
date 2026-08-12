<div align="center">

# ⚡ TRANSSION FLASHABLE BUILDER ⚡
### <i>Next-Generation Cloud & Local Automated Recovery ROM Engine</i>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&pause=1000&color=00F0FF&center=true&vCenter=true&width=750&lines=%E2%9A%A1+Automated+Recovery+ROM+Builder;%F0%9F%9A%80+ZSTD+Level+19+Ultra+Compression;%F0%9F%94%A5+Native+MIO-KITCHEN+4.2.0+Linux+Toolchain;%F0%9F%92%8E+Full+A%2FB+Dual-Slot+Flashing+via+lptools" alt="Typing SVG" />
</p>

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/sheikhmehraann/transsion-flashable-builder/build_rom.yml?branch=master&style=for-the-badge&logo=githubactions&logoColor=white&color=00F0FF)](https://github.com/sheikhmehraann/transsion-flashable-builder/actions)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-FFD43B?style=for-the-badge&logo=python&logoColor=black)](https://python.org)
[![Platform Support](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Windows-7B2CBF?style=for-the-badge&logo=ubuntu&logoColor=white)](https://github.com/sheikhmehraann/transsion-flashable-builder)
[![Compression Engine](https://img.shields.io/badge/ZSTD-Level%2019%20Ultra-FF007F?style=for-the-badge&logo=fastapi&logoColor=white)](https://github.com/facebook/zstd)
[![License](https://img.shields.io/badge/License-MIT-00E676?style=for-the-badge&logo=open-source-initiative&logoColor=black)](LICENSE)

<br/>

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">

</div>

---

## 📖 Table of Contents

- [✨ Overview](#-overview)
- [⚡ High-Performance Features](#-high-performance-features)
- [📊 Production Build Benchmarks](#-production-build-benchmarks)
- [🚀 How to Build via GitHub Actions](#-how-to-build-via-github-actions)
- [🛠️ Flashing Architecture Pipeline](#️-flashing-architecture-pipeline)
- [📁 Repository Directory Map](#-repository-directory-map)
- [💳 Credits & License](#-credits--license)

---

## ✨ Overview

**Transsion Flashable Builder** is an enterprise-grade, automated conversion pipeline designed for **Infinix, Tecno, and itel** MediaTek / Unisoc Android devices. It takes raw factory stock firmware dumps and intelligently reconstructs them into A/B dual-slot recovery flashable ZIP archives installable via custom recoveries (**TWRP**, **OrangeFox**, **SHRP**).

> [!IMPORTANT]
> 🚀 **Zero Local Resource Usage!** You do **not** need a high-end PC or gigabytes of storage space. Build full 8GB+ flashable ROM packages in the cloud via **GitHub Actions** on high-bandwidth Ubuntu runners with automated hosting on **GoFile**!

---

## ⚡ High-Performance Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ⚡ CLOUD & ENGINE HIGHLIGHTS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ► ☁️  Ubuntu Cloud Builder (`ubuntu-latest` GitHub Runner)                 │
│  ► 🧰  Native MIO-KITCHEN 4.2.0 Toolchain (20 Native 64-bit Linux ELFs)     │
│  ► 🌐  Multi-Source Smart Downloader (SourceForge, Needrom, Drive, Mega)    │
│  ► 🔥  Ultra ZSTD Level 19 Compression & Multi-Core 7z Packaging          │
│  ► 📤  Dynamic GoFile Server Resolution API Uploader                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

<details open>
<summary><b>1. ☁️ Ubuntu Cloud Builder Engine (ubuntu-latest)</b></summary>

- **Automated Execution**: Trigger builds via `workflow_dispatch` on GitHub Actions without downloading raw stock ROMs to your local storage.
- **MIO-KITCHEN 4.2.0 Linux Toolchain**: Embedded 20 64-bit Linux ELF binaries (`imgkit`, `lpmake`, `simg2img`, `zstd`, `extract.erofs`, `mkfs.erofs`, `cpio`, `busybox`, `brotli`, `magiskboot`, `e2fsdroid`) in `bin/linux/`.
</details>

<details open>
<summary><b>2. 🌐 Multi-Source Smart Downloader Engine (download_rom.py)</b></summary>

- **SourceForge Direct Engine**: Auto-resolves SourceForge download links to `https://downloads.sourceforge.net/project/...` with `User-Agent: curl/7.88.1` header bypass for maximum bandwidth streaming.
- **Universal Cloud Support**: Supports PixelDrain API, Needrom session-authenticated downloads, Google Drive (`gdown`), Mega.py, GoFile API, and direct streams via `aria2c`.
</details>

<details open>
<summary><b>3. ⚡ Maximum Ultra Compression (ZSTD Level 19 & 7z Multi-Thread)</b></summary>

- **ZSTD Level 19 Ultra (`-19 --ultra -T0`)**: Compresses dynamic partitions (`system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm`) with peak compression density and parallel CPU multi-threading (`-T0`).
- **Multi-Threaded 7z Fast Packaging (`7z a -tzip -mx=9 -mmt=on`)**: Packages the final flashable ZIP archive using multi-threaded 7-Zip engines for 10x faster execution.
</details>

<details open>
<summary><b>4. 📤 Dynamic GoFile Release Engine (gofile_uploader.py)</b></summary>

- Dynamic GoFile API server resolution (`https://api.gofile.io/servers`) auto-discovers active upload nodes (`store-eu-par-5`, `store-eu-par-7`, `store3`, `store1`).
- Automatic fallback loop ensures error-free uploads and renders an aesthetic **GitHub Action Step Summary** card with direct download links.
</details>

---

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">

---

## 📊 Production Build Benchmarks

<div align="center">

| Metric / Parameter | Production Specification |
| :--- | :--- |
| **📱 Target Device** | **Infinix GT 20 Pro** |
| **🏷️ Device Codename** | `X6871` |
| **📦 Firmware Version** | `X6871-15.1.2.145SP02(OP001PF001AZ)` |
| **🌏 Region Subfolder** | `Open` |
| **📥 Raw Stock Firmware** | SourceForge Direct Stream Mirror (`8.45 GB`) |
| **⚡ Output Flashable Package** | `X6871-15.1.2.145SP02(OP001PF001AZ)-recovery-ab.zip` (`7.74 GB`) |
| **⚙️ Build Execution Time** | `20 minutes 23 seconds` (`ubuntu-latest`) |
| **🚀 Direct Download Mirror** | **[Download Flashable ROM via GoFile](https://gofile.io/d/8iEMdcIK)** |

</div>

---

## 🚀 How to Build via GitHub Actions

> [!TIP]
> You can pass any ROM URL: SourceForge project links, Needrom URLs, Google Drive links, PixelDrain links, or direct HTTP/HTTPS file URLs!

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Developer / User
    participant GHA as ⚡ GitHub Actions Workflow
    participant SF as 🌐 SourceForge / Cloud Host
    participant Engine as 🛠️ MIO-KITCHEN Builder Engine
    participant GF as 📤 GoFile API

    User->>GHA: Trigger Workflow (rom_url, device, codename, fw_version, region)
    GHA->>SF: Download Raw Stock ROM Archive (8.45 GB)
    SF-->>GHA: Direct Stream Complete
    GHA->>Engine: Extract, Merge Super Partitions & Compress ZSTD Level 19
    Engine-->>GHA: Flashable ZIP Package Built (7.74 GB)
    GHA->>GF: Dynamic Multi-Server Upload
    GF-->>User: Output GoFile Direct Download URL on Summary Page!
```

1. Navigate to **[sheikhmehraann/transsion-flashable-builder Actions](https://github.com/sheikhmehraann/transsion-flashable-builder/actions)**.
2. Select **Build Flashable ROM & Upload to GoFile**.
3. Click **Run workflow** and input:
   - **`rom_url`**: SourceForge, Needrom, Google Drive, Mega, PixelDrain, or GoFile URL.
   - **`device_name`**: `Infinix GT 20 Pro`
   - **`codename`**: `X6871`
   - **`fw_version`**: `X6871-15.1.2.145SP02(OP001PF001AZ)`
   - **`region`**: `Open`
4. Click **Run workflow**. Upon completion, your GoFile download link will appear directly on the Job Summary page!

---

## 🛠️ Flashing Architecture Pipeline

The generated `update-binary` shell script performs these automated steps on the target device:

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

## 📁 Repository Directory Map

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

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">

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
