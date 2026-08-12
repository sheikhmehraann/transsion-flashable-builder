# Transsion Flashable Builder

> Convert Transsion (Infinix / Tecno / itel) stock firmware dumps into recovery-flashable ZIPs with A/B slot support via lptools.

## GitHub Actions Cloud Builder ⚡ (Automated)

You can build flashable ROMs directly on GitHub servers without downloading huge firmware files to your PC!

1. Go to the **Actions** tab in your repository.
2. Select **Build Flashable ROM & Upload to GoFile**.
3. Click **Run workflow** and fill in:
   - **Stock ROM Download Link** (Google Drive, PixelDrain, GoFile, or direct link)
   - **Device Name** (e.g. `Infinix GT 20 Pro`)
   - **Codename** (e.g. `X6871`)
   - **Firmware Version** (e.g. `X6871-15.1.2.165SP05(OP001PF001AZ)`)
   - **Region Subfolder** (e.g. `India`)
4. Click **Run workflow** — GitHub Actions will:
   - Download & extract the stock ROM
   - Unpack & merge region `super.img` into base
   - Compress dynamic partitions with parallel `zstd`
   - Generate `update-binary` with custom MEHRAAN banner & slot logic
   - Build `<fw_version>-recovery-ab.zip`
   - Upload the ZIP directly to **GoFile** and post the download link in the summary!

---

## Local Features

- **Super Partition Merge** — Unpacks base + region `super.img` using `imgkit`, intelligently merges region overlays (especially `tr_*` Transsion layers) into the base
- **Smart Region Detection** — Auto-detects region subfolders containing their own `super.img` for multi-region firmware builds
- **Non-Zero Data Comparison** — Skips empty region partition stubs by comparing actual non-zero byte content, preventing base partitions from being overwritten with empty data
- **A/B Slot Support** — Generated install scripts flash firmware and system partitions to both A/B slots for full compatibility
- **lptools Dynamic Partitions** — Uses `lptools` lifecycle management (clear-cow → destroy → create → map → flash → unmap/map) for proper dynamic partition handling
- **Parallel Zstd Compression** — Compresses dynamic partition images with `zstd` using multi-threaded parallel processing for maximum speed
- **4K Sector Alignment** — Firmware images are padded to 4096-byte alignment for block device compatibility
- **Recovery Flashable Output** — Produces a ZIP installable via TWRP, OrangeFox, or any custom recovery
- **Modern Dark UI** — Clean Tkinter interface with terminal output, scan results, and progress tracking

## Requirements

- **Python 3.8+** (uses `tkinter`, included with standard Python on Windows)
- **Windows** (the bundled binary tools are Windows executables)
- The following tools must be present in the `bin/` directory:
  - `imgkit.exe` — Super partition unpacker
  - `zstd.exe` — Zstandard compressor (Windows)
  - `zstd-arm64` — Zstandard decompressor (ARM64, bundled into the flashable ZIP)

## Usage

1. **Launch the tool:**
   ```bash
   python transsion_flashable_builder.py
   ```

2. **Select Firmware Source** — Browse to the root folder of your extracted firmware dump (must contain `super.img` + partition images)

3. **Select Region** — If region subfolders with their own `super.img` are detected, pick the target region

4. **Fill in Metadata** — Enter device name, codename, and firmware version

5. **Choose Output Folder** — Where the final `.zip` will be saved

6. **Click BUILD** — The tool will:
   - Unpack both base and region super images
   - Merge region partitions into base
   - Collect firmware + system + dynamic partition images
   - Compress dynamic partitions with zstd (parallel)
   - Generate the `update-binary` install script
   - Package everything into a flashable ZIP

## Flashing Pipeline

The generated `update-binary` script performs these steps on the device:

```
1. Flash firmware partitions → raw to both A/B slots
2. lptools clear-cow
3. lptools destroy + create dynamic partitions
4. lptools map dynamic partitions
5. Flash system partitions (boot, dtbo, vbmeta) → raw to both slots
6. Flash dynamic partitions (system, vendor, product, etc.) → zstd decompress to active slot
7. Final unmap + map for clean state
```

## Project Structure

```
transsion-flashable-builder/
├── transsion_flashable_builder.py   # Main application
├── bin/                              # Required binary tools
│   ├── imgkit.exe                    # Super partition unpacker
│   ├── zstd.exe                      # Zstandard compressor (Windows)
│   ├── zstd-arm64                    # Zstandard decompressor (ARM64)
│   ├── lpmake.exe                    # Logical partition maker
│   ├── simg2img.exe                  # Sparse image converter
│   ├── brotli.exe                    # Brotli compressor
│   └── ...                           # Supporting libraries
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

## Supported Partition Types

| Type | Partitions | Flash Method |
|------|-----------|-------------|
| **Dynamic** (super) | system, vendor, product, system_ext, system_dlkm, vendor_dlkm, odm, odm_dlkm, tr_* | zstd → lptools mapper |
| **System** (raw) | boot, dtbo, init_boot, vendor_boot, vbmeta, vbmeta_system, vbmeta_vendor | raw → both A/B slots |
| **Firmware** (raw) | lk, tee, scp, gz, md1img, spmfw, sspm, preloader_raw, logo, and more | raw → both A/B slots |

## Credits

- **Mehraan** — Tool author and maintainer
- Built with lptools dynamic partition management approach
- Uses [Zstandard](https://github.com/facebook/zstd) for compression

## License

MIT License — see [LICENSE](LICENSE) for details.
