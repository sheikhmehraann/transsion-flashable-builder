# -*- coding: utf-8 -*-
"""
Transsion Flashable ROM Builder — CLI / Headless Engine
Can be run on Windows/Linux or directly inside GitHub Actions workflows.
"""
import os, sys, argparse, glob, shutil, subprocess

# Reconfigure stdout/stderr for UTF-8 compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from transsion_flashable_builder import (
    BIN_DIR, IMGKIT, ZSTD_EXE, ZSTD_ARM, FIRMWARES, RAW_SYSTEM,
    detect_regions, stem_of, count_non_zero_bytes, fmt_sz
)
import zipfile, tempfile, concurrent.futures

class ConsoleLogger:
    def log(self, msg, tag="normal"):
        try:
            print(f"[{tag.upper()}] {msg}")
        except Exception:
            print(f"[{tag.upper()}] {msg.encode('ascii', 'replace').decode('ascii')}")

    def run_cmd(self, cmd, label):
        try:
            print(f"\n>>> {label}")
            print(f"    {' '.join(str(c) for c in cmd)}")
        except Exception:
            pass
        env = os.environ.copy()
        env["PATH"] = BIN_DIR + os.pathsep + env.get("PATH", "")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=BIN_DIR
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    try:
                        print(f"    {line}")
                    except Exception:
                        print(f"    {line.encode('ascii', 'replace').decode('ascii')}")
            proc.wait()
            ok = proc.returncode == 0
            print("    [OK] DONE" if ok else f"    [FAIL] FAILED (exit {proc.returncode})")
            return ok
        except Exception as e:
            print(f"    [EXC] EXCEPTION: {e}")
            return False

def copy_4k_padded(src, dst):
    with open(src, "rb") as f_in:
        data = f_in.read()
    remainder = len(data) % 4096
    if remainder != 0:
        data += b'\x00' * (4096 - remainder)
    with open(dst, "wb") as f_out:
        f_out.write(data)

def generate_update_binary(device, codename, fw_ver, fw_files, raw_sys_files, dynamic_list):
    dyn_names = [name for name, _, _ in dynamic_list]

    script = r'''#!/sbin/sh

OUTFD=/proc/self/fd/$2
ZIPFILE="$3"

ui_print() {
    printf 'ui_print %s\nui_print\n' "$1" >>"$OUTFD"
}

flash_partition() {
    src="$1"
    dest="$2"
    msg="$3"

    if [ "$#" -lt 3 ]; then
        partition_name=$(echo "$dest" | cut -d '/' -f 5)
        ui_print "- Flashing partition $partition_name"
    elif [ -n "$msg" ]; then
        ui_print "$msg"
    fi

    unzip -p "$ZIPFILE" "$src" >"$dest" || {
        ui_print "Error: Failed to flash $src to $dest"
        exit 1
    }
}

flash_partition_zstd() {
    src="$1"
    dest="$2"
    partition_name=$(echo "$dest" | cut -d '/' -f 5)

    ui_print "- Flashing partition $partition_name"
    unzip -p "$ZIPFILE" "$src" | /tmp/META-INF/zstd -c -d >"$dest" || {
        ui_print "Error: Failed to flash compressed $src to $dest"
        exit 1
    }
}

flash_firmware_both_slots() {
    img_file="$1"
    base_name="$2"

    flash_partition "$img_file" "/dev/block/by-name/${base_name}_a" "- Flashing partition ${base_name} to both slots"
    flash_partition "$img_file" "/dev/block/by-name/${base_name}_b" ""
}

getVolumeKey() {
    ui_print "- Listening to volume keys. Press [+] for 'Yes' and [-] for 'No'"
    while true; do
        keyInfo=$(getevent -qlc 1 | grep KEY_VOLUME)
        [ -z "$keyInfo" ] && continue
        isUpKey=$(printf '%s\n' "$keyInfo" | grep KEY_VOLUMEUP)
        if [ -n "$isUpKey" ]; then
            return 0
        else
            return 1
        fi
    done
}

'''

    script += f'''checkDevice() {{
    myDevice=$(getprop ro.product.device)
    [ -z "$myDevice" ] && myDevice=$(getprop ro.build.product)
    [ -z "$myDevice" ] && myDevice=$(getprop ro.product.name)
    romDevice="{codename}"
    if [ -z "$(echo "$myDevice" | grep -i "$romDevice")" ]; then
        ui_print "- Device code verification failed. Please double-check if this package matches your device model."
        ui_print "- Flashing the wrong package may cause bricking, and you will bear the consequences. Do you want to continue flashing?"
        if ! getVolumeKey; then
            ui_print "- You chose to abort flashing."
            exit 1
        else
            ui_print "- You chose to continue flashing."
        fi
    fi
}}

'''

    script += r'''checkExit() {
    status=$?
    if [ "$status" -ne 0 ]; then
        ui_print "Error: Exit status $status detected. There may be an issue with your super partition. Flash the stock super.img first, then retry. Exiting..."
        exit 1
    fi
}

unmountPartitions() {
    umount /system /system_root /vendor /product /system_ext /vendor_dlkm /odm_dlkm /odm \
           /tr_carrier /tr_company /tr_mi /tr_preload /tr_product /tr_region /tr_theme \
           /tr_manifest /tr_misc 2>/dev/null
}

manage_logical_partition() {
    operation="$1"
    partition="$2"
    size="$3"
    slot="$4"

    case "$operation" in
        clear)
            lptools unmap "$partition$slot" 2>/dev/null || true
            lptools remove "$partition$slot" 2>/dev/null || true
            ;;
        create)
            lptools create "$partition$slot" "$size" || checkExit
            ;;
        create_optional)
            lptools create "$partition$slot" "$size" || true
            ;;
        map)
            lptools map "$partition$slot" || checkExit
            ;;
        unmap_map)
            lptools unmap "$partition$slot" 2>/dev/null || true
            lptools map "$partition$slot" || checkExit
            ;;
    esac
}

create_partitions_for_slot() {
    target_slot="$1"
    other_slot="$2"
    shift 2

    for spec in "$@"; do
        partition="${spec%%:*}"
        size="${spec#*:}"
        manage_logical_partition "create" "$partition" "$size" "$target_slot"
        manage_logical_partition "create_optional" "$partition" "0" "$other_slot"
    done
}

process_partitions_for_slots() {
    operation="$1"
    shift

    for partition in "$@"; do
        manage_logical_partition "$operation" "$partition" "" "_a"
        manage_logical_partition "$operation" "$partition" "" "_b"
    done
}

process_partitions_for_slot() {
    operation="$1"
    slot="$2"
    shift 2

    for partition in "$@"; do
        manage_logical_partition "$operation" "$partition" "" "$slot"
    done
}

unzip -o "$ZIPFILE" META-INF/zstd -d /tmp
chmod 0755 /tmp/META-INF/zstd

'''

    script += 'ui_print " "\n'
    script += 'ui_print "============================================"\n'
    script += 'ui_print "  ███   ███  ████████  ██   ██  ██████    ███████   ███   ██ "\n'
    script += 'ui_print "  ████ ████  ██        ██   ██  ██   ██   ██   ██   ████  ██ "\n'
    script += 'ui_print "  ██ ███ ██  ███████   ███████  ██████    ███████   ██ ██ ██ "\n'
    script += 'ui_print "  ██  █  ██  ██        ██   ██  ██   ██   ██   ██   ██  ████ "\n'
    script += 'ui_print "  ██     ██  ████████  ██   ██  ██    ██  ██   ██   ██   ███ "\n'
    script += 'ui_print " "\n'
    script += 'ui_print "       Transsion Flashable ROM Builder"\n'
    script += 'ui_print "             Powered by Mehraan"\n'
    script += 'ui_print "============================================"\n'
    script += f'ui_print "  Device   : {device} ({codename})"\n'
    script += f'ui_print "  Version  : {fw_ver}"\n'
    script += 'ui_print "============================================"\n'
    script += 'ui_print " "\n\n'

    script += 'checkDevice\n\n'
    script += 'unmountPartitions\n\n'
    script += 'ui_print " "\n'
    script += 'SLOT=$(getprop ro.boot.slot_suffix)\n'
    script += 'ui_print "Checking boot slot... ${SLOT}"\n\n'

    script += '# Remap\n'
    script += 'lptools clear-cow || true\n\n'

    if fw_files:
        script += 'ui_print " "\n'
        script += 'ui_print "Patching firmware to both slot..."\n'
        for fname, _ in fw_files:
            out_name = fname if fname.lower() != "logo.bin" else "logo.img"
            st = stem_of(out_name)
            script += f'flash_firmware_both_slots "firmware/{out_name}" "{st}"\n'
        script += '\n'

    script += '# Clear existing partitions\n'
    script += 'process_partitions_for_slots "clear" \\\n'
    for i, name in enumerate(dyn_names):
        suffix = ' \\' if i < len(dyn_names) - 1 else ''
        script += f'        "{name}"{suffix}\n'
    script += '\n'

    script += '# Create new partitions\n'
    script += 'case "$SLOT" in\n'
    script += '    "_a") OTHER_SLOT="_b" ;;\n'
    script += '    "_b") OTHER_SLOT="_a" ;;\n'
    script += '    *) ui_print "- Unknown boot slot: $SLOT"; exit 1 ;;\n'
    script += 'esac\n\n'

    script += 'create_partitions_for_slot "$SLOT" "$OTHER_SLOT" \\\n'
    for i, (name, size, _) in enumerate(dynamic_list):
        suffix = ' \\' if i < len(dynamic_list) - 1 else ''
        script += f'        "{name}:{size}"{suffix}\n'
    script += '\n'

    script += '# Map dynamic partitions for active slot\n'
    script += 'process_partitions_for_slot "map" "$SLOT" \\\n'
    for i, name in enumerate(dyn_names):
        suffix = ' \\' if i < len(dyn_names) - 1 else ''
        script += f'        "{name}"{suffix}\n'
    script += '\n'

    if raw_sys_files:
        sys_order = ["boot", "init_boot", "dtbo", "vendor_boot", "vbmeta", "vbmeta_system", "vbmeta_vendor"]
        sorted_sys = list(raw_sys_files)
        sorted_sys.sort(key=lambda x: sys_order.index(stem_of(x[0]).lower()) if stem_of(x[0]).lower() in sys_order else 99)
        
        script += 'ui_print " "\n'
        script += 'ui_print "Patching system..."\n'
        for fname, _ in sorted_sys:
            st = stem_of(fname)
            script += f'flash_firmware_both_slots "{fname}" "{st}"\n'

    script += '\n'
    for name, size, pf in dynamic_list:
        script += f'flash_partition_zstd "{pf}.zst" "/dev/block/mapper/{name}$SLOT"\n'

    script += '\n# Final unmapping and mapping to ensure proper mounting\n'
    script += 'process_partitions_for_slot "unmap_map" "$SLOT" \\\n'
    for i, name in enumerate(dyn_names):
        suffix = ' \\' if i < len(dyn_names) - 1 else ''
        script += f'        "{name}"{suffix}\n'

    script += '\nui_print " "\n'
    script += 'ui_print "============================================="\n'
    script += 'ui_print "                                             "\n'
    script += 'ui_print "         INSTALLATION COMPLETE!              "\n'
    script += 'ui_print "                                             "\n'
    script += 'ui_print "  1. Format Data (Wipe > Format Data > yes)  "\n'
    script += 'ui_print "  2. Reboot to System                        "\n'
    script += 'ui_print "                                             "\n'
    script += 'ui_print "         Powered by Mehraan                  "\n'
    script += 'ui_print "============================================="\n'
    script += 'ui_print " "\n\n'
    script += 'exit 0\n'

    return script

def build_rom_cli(base_dir, out_dir, device, codename, fw_ver, region_name=None, level="3"):
    logger = ConsoleLogger()
    base_super = os.path.join(base_dir, "super.img")
    if not os.path.exists(base_super):
        # Search recursively for super.img in extracted subdirectories
        found_supers = glob.glob(os.path.join(base_dir, "**", "super.img"), recursive=True)
        if found_supers:
            found_supers.sort(key=lambda p: len(p.split(os.sep)))
            base_super = found_supers[0]
            base_dir = os.path.dirname(base_super)
            print(f"[AUTO-RESOLVE] Resolved stock ROM folder with super.img: {base_dir}")
        else:
            raise FileNotFoundError(f"Base super.img missing from {base_dir} (no subfolder contained super.img)")

    regions = detect_regions(base_dir)
    region_dir = None
    if region_name:
        for r_name, r_path in regions:
            if r_name.lower() == region_name.lower():
                region_dir = r_path
                region_name = r_name
                break
    if not region_dir and regions:
        region_name, region_dir = regions[0]

    if not region_dir:
        raise FileNotFoundError("No valid region subfolder containing super.img found!")

    os.makedirs(out_dir, exist_ok=True)
    temp_root = tempfile.mkdtemp(prefix="rombuild_")
    base_parts = os.path.join(temp_root, "base_unpack")
    region_parts = os.path.join(temp_root, "region_unpack")

    try:
        os.makedirs(base_parts, exist_ok=True)
        os.makedirs(region_parts, exist_ok=True)
        region_super = os.path.join(region_dir, "super.img")

        logger.log(f"Device: {device} ({codename}) | Version: {fw_ver} | Region: {region_name}", "head")

        ok = logger.run_cmd([IMGKIT, "unpack", "-i", base_super, "-o", base_parts, "-l", "2"], "Unpacking Base super.img")
        if not ok: raise RuntimeError("Base super.img unpack failed.")

        ok = logger.run_cmd([IMGKIT, "unpack", "-i", region_super, "-o", region_parts, "-l", "2"], "Unpacking Region super.img")
        if not ok: raise RuntimeError("Region super.img unpack failed.")

        bp = sorted(f for f in os.listdir(base_parts) if f.endswith(".img"))
        rp = sorted(f for f in os.listdir(region_parts) if f.endswith(".img"))

        replaced_count = 0
        added_count = 0
        skipped_count = 0

        for pf in rp:
            src = os.path.join(region_parts, pf)
            dst = os.path.join(base_parts, pf)
            st = stem_of(pf).lower()

            if os.path.exists(dst):
                if st.startswith("tr_"):
                    shutil.copy2(src, dst)
                    replaced_count += 1
                else:
                    b_nz = count_non_zero_bytes(dst)
                    r_nz = count_non_zero_bytes(src)
                    if r_nz > b_nz:
                        shutil.copy2(src, dst)
                        replaced_count += 1
                    else:
                        skipped_count += 1
            else:
                shutil.copy2(src, dst)
                added_count += 1

        print(f"[MERGE] Replaced: {replaced_count}, Added: {added_count}, Skipped: {skipped_count}")
        shutil.rmtree(region_parts, ignore_errors=True)

        super_imgs = sorted(f for f in os.listdir(base_parts) if f.endswith(".img"))
        partition_sizes = {stem_of(pf).lower(): os.path.getsize(os.path.join(base_parts, pf)) for pf in super_imgs}

        fw_files = []
        for fw_name in FIRMWARES:
            for ext in (".img", ".bin"):
                fpath = os.path.join(base_dir, fw_name + ext)
                if os.path.isfile(fpath):
                    fw_files.append((os.path.basename(fpath), fpath))
                    break

        if region_dir:
            for fw_name in FIRMWARES:
                for ext in (".img", ".bin"):
                    rfpath = os.path.join(region_dir, fw_name + ext)
                    if os.path.isfile(rfpath):
                        fw_files = [(os.path.basename(rfpath), rfpath) if stem_of(n).lower() == fw_name else (n, p) for n, p in fw_files]
                        if not any(stem_of(n).lower() == fw_name for n, p in fw_files):
                            fw_files.append((os.path.basename(rfpath), rfpath))
                        break

        raw_sys_files = []
        for sys_name in RAW_SYSTEM:
            fpath = os.path.join(base_dir, sys_name + ".img")
            if os.path.isfile(fpath):
                raw_sys_files.append((sys_name + ".img", fpath))

        build_dir = os.path.join(temp_root, "build_staging")
        os.makedirs(build_dir, exist_ok=True)

        script_folder = os.path.join(build_dir, "META-INF", "com", "google", "android")
        os.makedirs(script_folder, exist_ok=True)
        meta_inf = os.path.join(build_dir, "META-INF")
        shutil.copy2(ZSTD_ARM, os.path.join(meta_inf, "zstd"))

        firmware_out = os.path.join(build_dir, "firmware")
        os.makedirs(firmware_out, exist_ok=True)
        for fname, src_path in fw_files:
            out_name = fname if fname.lower() != "logo.bin" else "logo.img"
            copy_4k_padded(src_path, os.path.join(firmware_out, out_name))

        for fname, src_path in raw_sys_files:
            shutil.copy2(src_path, os.path.join(build_dir, fname))

        print("[ZSTD] Compressing dynamic partitions...")
        def compress_task(pf):
            src = os.path.join(base_parts, pf)
            dst = os.path.join(build_dir, pf + ".zst")
            env = os.environ.copy()
            env["PATH"] = BIN_DIR + os.pathsep + env.get("PATH", "")
            cmd = [ZSTD_EXE, f"-{level}", "-T2", src, "-o", dst]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=BIN_DIR)
            proc.wait()
            return proc.returncode == 0, pf

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
            futures = [executor.submit(compress_task, pf) for pf in super_imgs]
            for future in concurrent.futures.as_completed(futures):
                ok, pf = future.result()
                if not ok: raise RuntimeError(f"Zstd compression failed for {pf}")

        shutil.rmtree(base_parts, ignore_errors=True)

        dynamic_list = [(stem_of(pf), partition_sizes.get(stem_of(pf).lower(), 0), pf) for pf in super_imgs]
        script = generate_update_binary(device, codename, fw_ver, fw_files, raw_sys_files, dynamic_list)

        with open(os.path.join(script_folder, "update-binary"), "w", newline="\n", encoding="utf-8") as f:
            f.write(script)
        with open(os.path.join(script_folder, "updater-script"), "w", newline="\n", encoding="utf-8") as uf:
            uf.write("# Dummy file\n")

        cleaned_fw = import_re_sub = os.path.basename(fw_ver).replace('/', '_')
        zip_name = f"{cleaned_fw}-recovery-ab.zip"
        zip_path = os.path.join(out_dir, zip_name)
        if os.path.isfile(zip_path):
            os.remove(zip_path)

        print(f"[ZIP] Creating final ZIP: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', allowZip64=True) as z:
            for root_d, _, files in os.walk(build_dir):
                for fname in files:
                    full = os.path.join(root_d, fname)
                    rel = os.path.relpath(full, build_dir).replace(os.sep, '/')
                    if fname.endswith('.zst'):
                        z.write(full, rel, compress_type=zipfile.ZIP_STORED)
                    else:
                        z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

        print(f"[SUCCESS] Flashable ROM Created Successfully: {zip_path}")
        return zip_path
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="Transsion Flashable ROM Builder CLI")
    parser.add_argument("--base-dir", required=True, help="Path to extracted stock ROM directory")
    parser.add_argument("--out-dir", required=True, help="Directory to save final recovery zip")
    parser.add_argument("--device", required=True, help="Device name (e.g. Infinix GT 20 Pro)")
    parser.add_argument("--codename", required=True, help="Device codename (e.g. X6871)")
    parser.add_argument("--fw-ver", required=True, help="Firmware version string")
    parser.add_argument("--region", help="Target region folder name (e.g. India)")
    parser.add_argument("--zstd-lvl", default="3", help="Zstd compression level (default 3)")

    args = parser.parse_args()
    build_rom_cli(
        base_dir=args.base_dir,
        out_dir=args.out_dir,
        device=args.device,
        codename=args.codename,
        fw_ver=args.fw_ver,
        region_name=args.region,
        level=args.zstd_lvl
    )

if __name__ == "__main__":
    main()
