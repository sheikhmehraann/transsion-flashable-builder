# -*- coding: utf-8 -*-
"""
Firmware To Flashable Builder — Mehraan Edition v4
Based on lptools individual partition flashing approach with lptools lifecycle management.
Scan firmware → Merge super → Unpack individual imgs → Build flashable ZIP.
"""
import os, sys, re, shutil, threading, subprocess, zipfile, tempfile
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox

def clean_old_temp_dirs():
    import glob
    temp_dir = tempfile.gettempdir()
    for pattern in ["rombuild_*", "mkota_*"]:
        for path in glob.glob(os.path.join(temp_dir, pattern)):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except:
                pass

clean_old_temp_dirs()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
BIN_DIR   = os.path.join(BASE_DIR, "bin")
IMGKIT    = os.path.join(BIN_DIR, "imgkit.exe")
ZSTD_EXE  = os.path.join(BIN_DIR, "zstd.exe")
ZSTD_ARM  = os.path.join(BIN_DIR, "zstd-arm64")

# ─── Partition classification ─────────────────────────────────────────────────
# Dynamic partitions that live INSIDE super (managed by lptools)
DYNAMIC_PARTITIONS = (
    "system", "vendor", "product",
    "system_dlkm", "system_ext", "vendor_dlkm", "odm_dlkm", "odm",
    "tr_carrier", "tr_company", "tr_mi", "tr_overlayfs",
    "tr_preload", "tr_product", "tr_region", "tr_theme",
    "tr_manifest", "tr_misc"
)
# Boot/system partitions: flashed RAW to /dev/block/by-name/ (both slots)
RAW_SYSTEM = (
    "boot", "dtbo", "init_boot",
    "vendor_boot", "vbmeta", "vbmeta_system", "vbmeta_vendor"
)
# Firmware: flashed RAW to /dev/block/by-name/ (both slots)
FIRMWARES = (
    "apusys", "cam_vpu1", "cam_vpu2", "cam_vpu3", "ccu",
    "connsys_bt", "dpm", "gpueb", "gz", "lk", "logo", "mcf_ota",
    "mcupm", "md1img", "mvpu_algo", "pi_img", "preloader_raw",
    "scp", "spmfw", "sspm", "tee", "tkv", "vcp"
)
# Always skip these stems
SKIP_STEMS = {
    "userdata", "super_empty", "vendor_boot-debug", "cache",
    "preloader", "preloader_emmc", "preloader_ufs",
    "tranfs", "efuse",
}
ALL_SUPER_STEMS = set(DYNAMIC_PARTITIONS)

# ─── Theme ────────────────────────────────────────────────────────────────────
BG      = "#0b0f19"
SB      = "#111827"
CARD    = "#1a2236"
CARD2   = "#1f2937"
BORDER  = "#2a3650"
ACCENT  = "#00d4aa"
ACCENT2 = "#05f2c3"
OK_C    = "#22c55e"
ERR_C   = "#ef4444"
WARN_C  = "#f59e0b"
TEXT    = "#f1f5f9"
MUTED   = "#64748b"
TERM_BG = "#060a12"
FONT    = "Segoe UI"
MONO    = "Cascadia Code"


def fmt_sz(path):
    try:
        s = os.path.getsize(path)
        if s >= 1024**3: return f"{s/1024**3:.2f} GB"
        if s >= 1024**2: return f"{s/1024**2:.1f} MB"
        return f"{s/1024:.0f} KB"
    except:
        return "?"


def stem_of(fname):
    return re.sub(r'\.(img|bin)$', '', fname, flags=re.IGNORECASE)


def is_flashable(fname):
    lo = fname.lower()
    return lo.endswith(".img") or lo == "logo.bin"


def detect_regions(base_dir):
    regions = []
    try:
        for entry in os.scandir(base_dir):
            if entry.is_dir() and os.path.exists(os.path.join(entry.path, "super.img")):
                regions.append((entry.name, entry.path))
    except:
        pass
    return sorted(regions, key=lambda x: x[0].lower())


def count_non_zero_bytes(path, limit=10 * 1024 * 1024):
    """Count non-zero bytes in a file up to a limit to quickly find real vs dummy stubs."""
    if not os.path.exists(path):
        return 0
    non_zero = 0
    try:
        with open(path, 'rb') as f:
            while non_zero < limit:
                chunk = f.read(1024 * 1024) # 1MB chunks
                if not chunk:
                    break
                non_zero += len(chunk) - chunk.count(b'\x00')
    except Exception:
        pass
    return min(non_zero, limit)



# ══════════════════════════════════════════════════════════════════════════════
#  TERMINAL WIDGET
# ══════════════════════════════════════════════════════════════════════════════
class Terminal(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=TERM_BG,
                         highlightthickness=1, highlightbackground=BORDER)
        self.txt = scrolledtext.ScrolledText(
            self, bg=TERM_BG, fg="#a6e22e",
            font=(MONO, 9), bd=0, padx=10, pady=8,
            state="disabled", wrap="word", selectbackground=BORDER
        )
        self.txt.pack(fill="both", expand=True)
        for tag, color in [("head", ACCENT), ("info", "#60a5fa"), ("ok", OK_C),
                           ("warn", WARN_C), ("err", ERR_C), ("dim", "#3d4f6b"),
                           ("normal", "#a6e22e")]:
            kw = {"foreground": color}
            if tag == "head": kw["font"] = (MONO, 9, "bold")
            self.txt.tag_config(tag, **kw)

    def log(self, msg, tag="normal"):
        self.txt.config(state="normal")
        self.txt.insert("end", msg + "\n", tag)
        self.txt.see("end")
        self.txt.config(state="disabled")

    def clear(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.config(state="disabled")

    def run_cmd(self, cmd, label):
        self.after(0, lambda: self.log(f"\n>>> {label}", "head"))
        self.after(0, lambda: self.log(f"    {' '.join(str(c) for c in cmd)}", "dim"))
        env = os.environ.copy()
        env["PATH"] = BIN_DIR + os.pathsep + env.get("PATH", "")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=BIN_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            for line in proc.stdout:
                line = line.rstrip()
                if not line: continue
                ll = line.lower()
                t = ("err"  if any(x in ll for x in ("error","failed","fatal"))
                     else "warn" if "warn" in ll
                     else "ok"   if any(x in ll for x in ("done","complete","written","success"))
                     else "info" if line.startswith("[")
                     else "normal")
                self.after(0, lambda l=line, tg=t: self.log(f"    {l}", tg))
            proc.wait()
            ok = proc.returncode == 0
            self.after(0, lambda: self.log(
                "    ✓ DONE" if ok else f"    ✗ FAILED (exit {proc.returncode})",
                "ok" if ok else "err"))
            return ok
        except FileNotFoundError:
            self.after(0, lambda: self.log(f"    ✗ NOT FOUND: {cmd[0]}", "err"))
            return False
        except Exception as e:
            self.after(0, lambda: self.log(f"    ✗ EXCEPTION: {e}", "err"))
            return False


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN BUILD PAGE
# ══════════════════════════════════════════════════════════════════════════════
class BuildPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app     = app
        self.running = False

        self.base_dir_v  = tk.StringVar()
        self.out_dir_v   = tk.StringVar()
        self.device_v    = tk.StringVar(value="")
        self.codename_v  = tk.StringVar(value="")
        self.fw_ver_v    = tk.StringVar(value="")
        self.zstd_lvl_v  = tk.StringVar(value="3")
        self.region_v    = tk.StringVar(value="")

        self._regions     = []
        self._base_super  = None
        self._region_path = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 4))
        tk.Label(hdr, text="Firmware To Flashable Builder",
                 font=(FONT, 20, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(hdr, text=" v4 — lptools + Individual Partition",
                 font=(FONT, 9), bg=BG, fg=MUTED).pack(side="left", padx=(6, 0))

        row1 = tk.Frame(self, bg=BG)
        row1.grid(row=1, column=0, sticky="ew", padx=24, pady=(6, 4))
        row1.columnconfigure(0, weight=3)
        row1.columnconfigure(1, weight=2)

        lc, li = self._card(row1, "FIRMWARE SOURCE")
        lc.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._row(li, "ROM Folder:", self.base_dir_v, self._browse_base, is_dir=True)
        tk.Label(li, text="    Root folder with super.img + all partition images",
                 font=(FONT, 7), bg=CARD, fg=MUTED).pack(anchor="w", padx=16)
        tk.Frame(li, bg=BORDER, height=1).pack(fill="x", padx=16, pady=8)

        rf = tk.Frame(li, bg=CARD)
        rf.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(rf, text="Region:", font=(FONT, 9), bg=CARD, fg=TEXT,
                 width=14, anchor="w").pack(side="left")
        self.region_combo = ttk.Combobox(rf, textvariable=self.region_v,
                                          font=(FONT, 9), state="readonly", width=20)
        self.region_combo.pack(side="left", ipady=3, padx=(0, 6))
        self.region_combo.bind("<<ComboboxSelected>>", self._on_region_change)
        tk.Label(li, text="    Auto-detected from subfolders containing super.img",
                 font=(FONT, 7), bg=CARD, fg=MUTED).pack(anchor="w", padx=16)
        self.detect_lbl = tk.Label(li, text="", font=(FONT, 8), bg=CARD, fg=OK_C,
                                    wraplength=420, justify="left")
        self.detect_lbl.pack(anchor="w", padx=16, pady=(6, 8))

        rc, ri = self._card(row1, "ROM METADATA")
        rc.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        for lbl, var, hint in [
            ("Device Name:", self.device_v,  "Infinix GT 20 Pro"),
            ("Codename:",    self.codename_v, "X6871"),
            ("FW Version:",  self.fw_ver_v,   "H652C-OP-250710"),
        ]:
            r = tk.Frame(ri, bg=CARD)
            r.pack(fill="x", padx=16, pady=(8, 0))
            tk.Label(r, text=lbl, font=(FONT, 9), bg=CARD, fg=TEXT,
                     width=14, anchor="w").pack(side="left")
            ef = tk.Frame(r, bg=BORDER, padx=1, pady=1)
            ef.pack(side="left", fill="x", expand=True)
            tk.Entry(ef, textvariable=var, font=(MONO, 8), bg=CARD2, fg=TEXT,
                     insertbackground=ACCENT, bd=0, relief="flat"
                     ).pack(fill="x", ipady=5, padx=3)
            tk.Label(ri, text=f"    {hint}", font=(FONT, 7), bg=CARD, fg=MUTED
                     ).pack(anchor="w", padx=16)
        tk.Frame(ri, bg=BORDER, height=1).pack(fill="x", padx=16, pady=8)
        zf = tk.Frame(ri, bg=CARD)
        zf.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(zf, text="Zstd Level:", font=(FONT, 9, "bold"), bg=CARD, fg=MUTED).pack(side="left")
        for lvl in ["3", "9", "15", "19"]:
            tk.Radiobutton(
                zf, text=f"Lv{lvl}", variable=self.zstd_lvl_v, value=lvl,
                font=(FONT, 8), bg=CARD, fg=TEXT, selectcolor=BG,
                activebackground=CARD, activeforeground=ACCENT, cursor="hand2"
            ).pack(side="left", padx=6)

        row2 = tk.Frame(self, bg=BG)
        row2.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 4))
        row2.columnconfigure(0, weight=3)
        row2.columnconfigure(1, weight=2)

        oc, oi = self._card(row2, "OUTPUT")
        oc.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._row(oi, "Output Folder:", self.out_dir_v, self._browse_out, is_dir=True)
        tk.Label(oi, text="    Where the final flashable .zip gets saved",
                 font=(FONT, 7), bg=CARD, fg=MUTED).pack(anchor="w", padx=16)
        tk.Frame(oi, bg=BG, height=6).pack()

        sc, si = self._card(row2, "SCAN RESULTS")
        sc.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.scan_text = tk.Text(si, bg=CARD, fg=TEXT, font=(MONO, 8),
                                  bd=0, padx=8, pady=6, height=5,
                                  state="disabled", wrap="word", highlightthickness=0)
        self.scan_text.pack(fill="both", expand=True, padx=10, pady=(4, 8))
        for t, c in [("g", OK_C), ("y", WARN_C), ("r", ERR_C), ("d", MUTED), ("w", TEXT)]:
            self.scan_text.tag_config(t, foreground=c)

        th = tk.Frame(self, bg=BG)
        th.grid(row=3, column=0, sticky="ew", padx=24, pady=(6, 2))
        tk.Label(th, text="TERMINAL", font=(FONT, 8, "bold"),
                 bg=BG, fg=MUTED).pack(side="left")
        tk.Button(th, text="Clear", font=(FONT, 8), bg=SB, fg=MUTED,
                  bd=0, padx=10, pady=3, cursor="hand2",
                  command=lambda: self.term.clear()).pack(side="right")

        self.term = Terminal(self)
        self.term.grid(row=4, column=0, sticky="nsew", padx=24)

        foot = tk.Frame(self, bg=BG)
        foot.grid(row=5, column=0, sticky="ew", padx=24, pady=12)
        self.status_lbl = tk.Label(foot, text="Ready", font=(FONT, 9), bg=BG, fg=MUTED)
        self.status_lbl.pack(side="left")
        self.run_btn = tk.Button(
            foot, text="  ⚡  BUILD FLASHABLE ROM  ",
            font=(FONT, 11, "bold"), bg=ACCENT, fg=BG,
            bd=0, padx=24, pady=11, cursor="hand2",
            activebackground=ACCENT2, activeforeground=BG,
            command=self._start_build
        )
        self.run_btn.bind("<Enter>", lambda e: self.run_btn.config(bg=ACCENT2))
        self.run_btn.bind("<Leave>", lambda e: self.run_btn.config(bg=ACCENT))
        self.run_btn.pack(side="right")

        self.term.log("Firmware To Flashable Builder — Mehraan Edition v4", "head")
        self.term.log("Based on lptools individual partition method", "info")
        self.term.log(f"imgkit   : {'OK' if os.path.exists(IMGKIT) else 'MISSING'}", "ok" if os.path.exists(IMGKIT) else "err")
        self.term.log(f"zstd     : {'OK' if os.path.exists(ZSTD_EXE) else 'MISSING'}", "ok" if os.path.exists(ZSTD_EXE) else "err")
        self.term.log(f"zstd-arm : {'OK' if os.path.exists(ZSTD_ARM) else 'MISSING'}", "ok" if os.path.exists(ZSTD_ARM) else "err")
        self.term.log("", "dim")
        self.term.log("Select a firmware folder to start.", "dim")

    # ── UI helpers ────────────────────────────────────────────────────────────
    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True)
        if title:
            tk.Label(inner, text=title, font=(FONT, 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=16, pady=(10, 0))
            tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(6, 0))
        return outer, inner

    def _row(self, parent, label, var, browse_cmd, is_dir=False):
        r = tk.Frame(parent, bg=CARD)
        r.pack(fill="x", padx=16, pady=(8, 0))
        tk.Label(r, text=label, font=(FONT, 9), bg=CARD, fg=TEXT,
                 width=14, anchor="w").pack(side="left")
        ef = tk.Frame(r, bg=BORDER, padx=1, pady=1)
        ef.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Entry(ef, textvariable=var, font=(MONO, 8), bg=CARD2, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat"
                 ).pack(fill="x", ipady=6, padx=3)
        tk.Button(r, text="Browse", font=(FONT, 8), bg=SB, fg=ACCENT,
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=browse_cmd).pack(side="left")

    def _browse_base(self):
        p = filedialog.askdirectory(title="Select Base Firmware Folder")
        if not p: return
        self.base_dir_v.set(p)
        self._scan(p)

    def _browse_out(self):
        p = filedialog.askdirectory(title="Select Output Folder")
        if p: self.out_dir_v.set(p)

    def _scan(self, base):
        sup = os.path.join(base, "super.img")
        self._base_super = sup if os.path.exists(sup) else None
        regions = detect_regions(base)
        self._regions = regions
        names = [r[0] for r in regions]
        self.region_combo.config(values=names)
        if names:
            self.region_combo.set(names[0])
            self._region_path = regions[0][1]
        else:
            self._region_path = None
        lines = []
        if self._base_super:
            lines.append(f"Base super.img found ({fmt_sz(self._base_super)})")
        else:
            lines.append("No super.img in root!")
        if names:
            lines.append(f"Regions: {', '.join(names)}")
        else:
            lines.append("No region subfolders found")
        self.detect_lbl.config(text="\n".join(lines), fg=OK_C if self._base_super else ERR_C)
        self._populate_scan(base)
        self.term.log(f"\nScanned: {base}", "head")
        self.term.log(f"Base super.img : {'FOUND ' + fmt_sz(self._base_super) if self._base_super else 'MISSING'}", "ok" if self._base_super else "err")
        self.term.log(f"Regions        : {names if names else 'None'}", "info")

    def _on_region_change(self, event=None):
        sel = self.region_v.get()
        for name, path in self._regions:
            if name == sel:
                self._region_path = path
                self._populate_scan(self.base_dir_v.get())
                break

    def _populate_scan(self, base):
        self.scan_text.config(state="normal")
        self.scan_text.delete("1.0", "end")
        def ins(txt, tag="w"):
            self.scan_text.insert("end", txt + "\n", tag)
        try:
            root_files = sorted(f for f in os.listdir(base) if is_flashable(f))
            root_non_super = [f for f in root_files if "super" not in f.lower() or f.lower() == "super_empty.img"]
            ins(f"[ROOT]  {len(root_non_super)} partition images", "g")
        except:
            ins("[ROOT]  (read error)", "r")
        rp = self._region_path
        if rp:
            ins(f"[{os.path.basename(rp).upper()}]", "y")
            try:
                for f in sorted(os.listdir(rp)):
                    fp = os.path.join(rp, f)
                    if f.lower() == "super.img":
                        ins(f"  super.img  {fmt_sz(fp)}  <- merge source", "y")
                    elif is_flashable(f):
                        ins(f"  {f}  {fmt_sz(fp)}  <- overrides root", "g")
                    else:
                        ins(f"  {f}  (skip)", "d")
            except:
                ins("  (read error)", "r")
        self.scan_text.config(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════════════════════
    def _set_status(self, text, color=MUTED):
        self.status_lbl.config(text=text, fg=color)
        self.app.set_status(text)

    @staticmethod
    def _copy_4k_padded(src, dst):
        """Copy file and pad to 4096-byte alignment with zeroes (4K sector alignment)."""
        with open(src, "rb") as f_in:
            data = f_in.read()
        remainder = len(data) % 4096
        if remainder != 0:
            data += b'\x00' * (4096 - remainder)
        with open(dst, "wb") as f_out:
            f_out.write(data)

    def _start_build(self):
        if self.running: return
        base     = self.base_dir_v.get().strip()
        out      = self.out_dir_v.get().strip()
        device   = self.device_v.get().strip()
        codename = self.codename_v.get().strip()
        fw_ver   = self.fw_ver_v.get().strip()
        level    = self.zstd_lvl_v.get().strip()
        region   = self.region_v.get().strip()

        errs = []
        if not base or not os.path.isdir(base):
            errs.append("Firmware folder not set.")
        if not self._base_super or not os.path.exists(self._base_super):
            errs.append("No super.img found in firmware folder.")
        if not self._region_path:
            errs.append("No region selected.")
        elif not os.path.exists(os.path.join(self._region_path, "super.img")):
            errs.append(f"Region folder '{region}' has no super.img.")
        if not out:
            errs.append("Output folder not set.")
        if not device: errs.append("Device name empty.")
        if not codename: errs.append("Codename empty.")
        if not fw_ver: errs.append("Firmware version empty.")
        if not os.path.exists(IMGKIT): errs.append("imgkit.exe missing from bin/")
        if not os.path.exists(ZSTD_EXE): errs.append("zstd.exe missing from bin/")
        if not os.path.exists(ZSTD_ARM): errs.append("zstd-arm64 missing from bin/")

        if errs:
            self.term.clear()
            for e in errs: self.term.log(f"X {e}", "err")
            return

        os.makedirs(out, exist_ok=True)
        self.running = True
        self.run_btn.config(state="disabled", text="  Building...  ", bg=CARD2, fg=MUTED)
        self._set_status("Building...", WARN_C)
        self.term.clear()
        threading.Thread(
            target=self._build_thread,
            args=(base, self._base_super, self._region_path, out,
                  device, codename, fw_ver, level, region),
            daemon=True
        ).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD THREAD — v4 lptools approach (4K sector alignment)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_thread(self, base_dir, base_super, region_dir, out_dir,
                      device, codename, fw_ver, level, region_name):
        temp_root    = tempfile.mkdtemp(prefix="rombuild_")
        base_parts   = os.path.join(temp_root, "base_unpack")
        region_parts = os.path.join(temp_root, "region_unpack")


        try:
            for d in (base_parts, region_parts):
                os.makedirs(d, exist_ok=True)

            region_super = os.path.join(region_dir, "super.img")

            self.after(0, lambda: self.term.log(
                f"Device   : {device}\n"
                f"Codename : {codename}\n"
                f"Version  : {fw_ver}\n"
                f"Region   : {region_name}\n"
                f"Base     : {base_dir}\n"
                f"Region   : {region_dir}\n"
                f"Output   : {out_dir}\n"
                f"Zstd Lvl : {level}", "info"))

            # ═══════════════════════════════════════════════════════════════
            #  STEP 1/5: UNPACK BASE SUPER
            # ═══════════════════════════════════════════════════════════════
            ok = self.term.run_cmd(
                [IMGKIT, "unpack", "-i", base_super, "-o", base_parts, "-l", "2"],
                "STEP 1/5 -- Unpack base super.img"
            )
            if not ok: raise RuntimeError("Base super.img unpack failed.")

            # ═══════════════════════════════════════════════════════════════
            #  STEP 2/5: UNPACK REGION SUPER
            # ═══════════════════════════════════════════════════════════════
            ok = self.term.run_cmd(
                [IMGKIT, "unpack", "-i", region_super, "-o", region_parts, "-l", "2"],
                "STEP 2/5 -- Unpack region super.img"
            )
            if not ok: raise RuntimeError("Region super.img unpack failed.")

            # ═══════════════════════════════════════════════════════════════
            #  STEP 3/5: MERGE REGION -> BASE
            # ═══════════════════════════════════════════════════════════════
            self.after(0, lambda: self.term.log(
                "\n>>> STEP 3/5 -- Merge region partitions into base", "head"))

            bp = sorted(f for f in os.listdir(base_parts) if f.endswith(".img"))
            rp = sorted(f for f in os.listdir(region_parts) if f.endswith(".img"))

            self.after(0, lambda: self.term.log(
                f"    Base partitions   : {len(bp)}", "info"))
            self.after(0, lambda: self.term.log(
                f"    Region partitions : {len(rp)}", "info"))

            replaced_count = 0
            added_count = 0
            skipped_count = 0
            for pf in rp:
                src = os.path.join(region_parts, pf)
                dst = os.path.join(base_parts, pf)
                r_sz = os.path.getsize(src)
                st = stem_of(pf).lower()

                if os.path.exists(dst):
                    # tr_* partitions are Transsion region overlay layers
                    # They MUST always use the region version (consumer build)
                    # Base tr_mi contains factory testing apps (Aging, WiFi ADB,
                    # QT, MMI1, MMI2, etc.) that must NOT appear in consumer ROMs
                    if st.startswith("tr_"):
                        b_sz = os.path.getsize(dst)
                        shutil.copy2(src, dst)
                        replaced_count += 1
                        diff = r_sz - b_sz
                        diff_str = f" (diff {diff:+,})" if diff != 0 else " (same size)"
                        self.after(0, lambda p=pf, s=r_sz, d=diff_str:
                            self.term.log(f"    [REGION]   {p}  ({s/1024**2:.1f} MB){d}  <- region overlay (always)", "ok"))
                    else:
                        # For non-tr partitions (system, vendor, product, etc.)
                        # compare actual non-zero data to skip empty region stubs
                        b_nz = count_non_zero_bytes(dst)
                        r_nz = count_non_zero_bytes(src)

                        if r_nz > b_nz:
                            b_sz = os.path.getsize(dst)
                            shutil.copy2(src, dst)
                            replaced_count += 1
                            diff = r_sz - b_sz
                            diff_str = f" (diff {diff:+,})" if diff != 0 else " (same size)"
                            self.after(0, lambda p=pf, s=r_sz, d=diff_str:
                                self.term.log(f"    [REPLACED] {p}  ({s/1024**2:.1f} MB){d}  <- region has more data", "ok"))
                        else:
                            skipped_count += 1
                            self.after(0, lambda p=pf, r_n=r_nz, b_n=b_nz:
                                self.term.log(f"    [KEEP BASE] {p}  (region empty: {r_n:,} vs {b_n:,} nz bytes)", "dim"))
                else:
                    # Region-only partition (not in base super)
                    shutil.copy2(src, dst)
                    added_count += 1
                    self.after(0, lambda p=pf, s=r_sz:
                        self.term.log(f"    [ADDED]    {p}  ({s/1024**2:.1f} MB)  (region only)", "warn"))

            self.after(0, lambda: self.term.log(
                f"    Merged: {replaced_count} replaced, {added_count} added, {skipped_count} kept base", "info"))

            # Free region_unpack
            try: shutil.rmtree(region_parts, ignore_errors=True)
            except: pass

            # ═══════════════════════════════════════════════════════════════
            #  STEP 4/5: COLLECT ALL PARTITION IMAGES
            # ═══════════════════════════════════════════════════════════════
            self.after(0, lambda: self.term.log(
                "\n>>> STEP 4/5 -- Collect all partition images", "head"))

            # Gather merged super sub-partitions + sizes for lptools
            super_imgs = sorted(f for f in os.listdir(base_parts) if f.endswith(".img"))
            super_stems = set()
            # {stem: size_bytes} for lptools create
            partition_sizes = {}

            self.after(0, lambda: self.term.log(
                f"    [SUPER] {len(super_imgs)} partitions from merged super:", "info"))

            for pf in super_imgs:
                st = stem_of(pf).lower()
                super_stems.add(st)
                img_path = os.path.join(base_parts, pf)
                sz = os.path.getsize(img_path)
                partition_sizes[st] = sz
                self.after(0, lambda f=pf, s=sz:
                    self.term.log(f"    -> {f}  ({s/1024**2:.1f} MB)", "dim"))

            # ═══════════════════════════════════════════════════════════════
            #  STEP 5/5: BUILD THE FLASHABLE ZIP
            # ═══════════════════════════════════════════════════════════════
            self.after(0, lambda: self.term.log(
                "\n>>> STEP 5/5 -- Build flashable ZIP", "head"))
            self.after(0, lambda: self._set_status("Compressing & packaging...", WARN_C))

            # Collect firmware images (non-super raw partitions)
            fw_dir = base_dir  # firmware files are in the base ROM folder
            fw_files = []
            for fw_name in FIRMWARES:
                for ext in (".img", ".bin"):
                    fpath = os.path.join(fw_dir, fw_name + ext)
                    if os.path.isfile(fpath):
                        fw_files.append((os.path.basename(fpath), fpath))
                        break
            # Also check region dir for firmware overrides
            if region_dir:
                for fw_name in FIRMWARES:
                    for ext in (".img", ".bin"):
                        rfpath = os.path.join(region_dir, fw_name + ext)
                        if os.path.isfile(rfpath):
                            # Replace base firmware with region version
                            fw_files = [(os.path.basename(rfpath), rfpath) if stem_of(n).lower() == fw_name else (n, p) for n, p in fw_files]
                            # If not already in list, add it
                            if not any(stem_of(n).lower() == fw_name for n, p in fw_files):
                                fw_files.append((os.path.basename(rfpath), rfpath))
                            break

            # Collect raw system images
            raw_sys_files = []
            for sys_name in RAW_SYSTEM:
                fpath = os.path.join(fw_dir, sys_name + ".img")
                if os.path.isfile(fpath):
                    raw_sys_files.append((sys_name + ".img", fpath))

            total_count = len(fw_files) + len(raw_sys_files) + len(super_imgs)
            self.after(0, lambda: self.term.log(
                f"    Total images: {total_count} (FW:{len(fw_files)} SYS:{len(raw_sys_files)} DYN:{len(super_imgs)})", "info"))

            # Build staging directory (flat ZIP structure)
            build_dir = os.path.join(temp_root, "build_staging")
            os.makedirs(build_dir, exist_ok=True)

            # META-INF
            script_folder = os.path.join(build_dir, "META-INF", "com", "google", "android")
            os.makedirs(script_folder, exist_ok=True)
            meta_inf = os.path.join(build_dir, "META-INF")
            shutil.copy2(ZSTD_ARM, os.path.join(meta_inf, "zstd"))

            # Copy firmware -> firmware/ (raw, 4K padded sector-aligned)
            firmware_out = os.path.join(build_dir, "firmware")
            os.makedirs(firmware_out, exist_ok=True)
            for fname, src_path in fw_files:
                # Rename logo.bin -> logo.img for consistency
                out_name = fname
                if fname.lower() == "logo.bin":
                    out_name = "logo.img"
                dst_path = os.path.join(firmware_out, out_name)
                # Pad ALL firmware to 4096-byte (4K) alignment
                # Block devices require sector-aligned writes
                self._copy_4k_padded(src_path, dst_path)
                pad_sz = os.path.getsize(dst_path)
                orig_sz = os.path.getsize(src_path)
                pad_info = f" (padded +{pad_sz - orig_sz})" if pad_sz != orig_sz else ""
                self.after(0, lambda f=out_name, p=pad_info:
                    self.term.log(f"    [FW RAW]  firmware/{f}{p}", "dim"))

            # Copy raw system images -> root (raw, sector-aligned: boot, dtbo, vbmeta...)
            # These are already 4K aligned (boot=64MB, dtbo=8MB, vbmeta=4K/12K)
            for fname, src_path in raw_sys_files:
                shutil.copy2(src_path, os.path.join(build_dir, fname))
                self.after(0, lambda f=fname:
                    self.term.log(f"    [SYS RAW] {f}", "dim"))

            # Compress dynamic partitions with zstd in parallel (Full PC Potential)
            import concurrent.futures
            self.after(0, lambda: self.term.log("\n>>> Parallel Zstd Compression Started", "info"))

            def compress_task(pf):
                src = os.path.join(base_parts, pf)
                dst = os.path.join(build_dir, pf + ".zst")
                sz = os.path.getsize(src)
                self.after(0, lambda f=pf, s=sz:
                    self.term.log(f"    [ZSTD-START] {f} ({s/1024**2:.1f} MB)...", "dim"))

                env = os.environ.copy()
                env["PATH"] = BIN_DIR + os.pathsep + env.get("PATH", "")
                # Use T2 to limit cpu load per process and balance resources
                cmd = [ZSTD_EXE, f"-{level}", "-T2", src, "-o", dst]

                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env, cwd=BIN_DIR,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                proc.wait()

                if proc.returncode != 0:
                    self.after(0, lambda p=pf: self.term.log(f"    ✗ ZSTD FAILED for {p}", "err"))
                    return False, pf

                zst_sz = os.path.getsize(dst) if os.path.exists(dst) else 0
                ratio = (zst_sz / sz * 100) if sz > 0 else 0
                self.after(0, lambda p=pf, z=zst_sz, r=ratio:
                    self.term.log(f"    -> [ZSTD-OK]    {p}.zst ({z/1024**2:.1f} MB, ratio {r:.0f}%)", "ok"))
                return True, pf

            max_workers = min(4, os.cpu_count() or 2)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(compress_task, pf) for pf in super_imgs]
                for future in concurrent.futures.as_completed(futures):
                    ok, pf = future.result()
                    if not ok:
                        raise RuntimeError(f"Zstd compression failed for {pf}")
            try: shutil.rmtree(base_parts, ignore_errors=True)
            except: pass

            # Generate update-binary (lptools + Mehraan branding)
            self.after(0, lambda: self.term.log(
                "\n    Generating update-binary (lptools method)...", "info"))

            # Build partition list for dynamic partitions
            dynamic_list = []
            for pf in super_imgs:
                st = stem_of(pf)
                sz = partition_sizes.get(st.lower(), 0)
                dynamic_list.append((st, sz, pf))

            script = self._generate_update_binary(
                device, codename, fw_ver,
                fw_files, raw_sys_files, dynamic_list
            )
            script_path = os.path.join(script_folder, "update-binary")
            with open(script_path, "w", newline="\n", encoding="utf-8") as f:
                f.write(script)

            # Create updater-script (required by some recoveries)
            updater_path = os.path.join(script_folder, "updater-script")
            with open(updater_path, "w", newline="\n", encoding="utf-8") as uf:
                uf.write("# Dummy file; update-binary is the actual script\n")

            # Package final ZIP
            self.after(0, lambda: self._set_status("Packaging ZIP...", WARN_C))
            cleaned_fw = re.sub(r'[^a-zA-Z0-9_\-]', '_', fw_ver)
            zip_name = f"{cleaned_fw}-recovery-ab.zip"
            zip_path = os.path.join(out_dir, zip_name)

            if os.path.isfile(zip_path):
                os.remove(zip_path)

            self.after(0, lambda: self.term.log(
                f"\n    Packaging: {zip_name}", "info"))

            with zipfile.ZipFile(zip_path, 'w', allowZip64=True) as z:
                for root_d, _, files in os.walk(build_dir):
                    for fname in files:
                        full = os.path.join(root_d, fname)
                        rel  = os.path.relpath(full, build_dir).replace(os.sep, '/')
                        if fname.endswith('.zst'):
                            z.write(full, rel, compress_type=zipfile.ZIP_STORED)
                        else:
                            z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                        self.after(0, lambda r=rel:
                            self.term.log(f"    + {r}", "dim"))

            zip_size = os.path.getsize(zip_path)

            self.after(0, lambda: self.term.log(
                f"\n{'='*56}\n"
                f"  BUILD COMPLETE!\n\n"
                f"  File     : {zip_path}\n"
                f"  Size     : {zip_size/1024**3:.2f} GB\n"
                f"  Device   : {device} ({codename})\n"
                f"  Version  : {fw_ver}\n"
                f"  Region   : {region_name}\n"
                f"  Images   : {total_count} partitions\n\n"
                f"  HOW TO FLASH:\n"
                f"  1. Copy {zip_name} to phone storage\n"
                f"  2. Boot into TWRP / OrangeFox recovery\n"
                f"  3. Install -> select the ZIP -> Swipe to flash\n"
                f"  4. Format Data -> Reboot system\n"
                f"{'='*56}", "ok"))

            self.after(0, lambda: self._set_status(
                f"Done!  {zip_name}  ({zip_size/1024**3:.2f} GB)", OK_C))
            self.after(0, lambda: messagebox.showinfo(
                "Build Complete",
                f"Flashable ZIP created by Firmware To Flashable Builder!\n\n{zip_path}\n\nSize: {zip_size/1024**3:.2f} GB"))

        except Exception as ex:
            import traceback
            self.after(0, lambda: self.term.log(f"\nX FAILED: {ex}", "err"))
            self.after(0, lambda: self.term.log(traceback.format_exc(), "dim"))
            self.after(0, lambda: self._set_status("Build failed.", ERR_C))
        finally:
            try: shutil.rmtree(temp_root, ignore_errors=True)
            except: pass
            self.running = False
            self.after(0, lambda: self.run_btn.config(
                state="normal", text="  ⚡  BUILD FLASHABLE ROM  ", bg=ACCENT, fg=BG))

    # ══════════════════════════════════════════════════════════════════════════
    #  UPDATE-BINARY — lptools lifecycle + Mehraan branding
    # ══════════════════════════════════════════════════════════════════════════
    def _generate_update_binary(self, device, codename, fw_ver,
                                fw_files, raw_sys_files, dynamic_list):
        """
        Generate shell script that:
        1. Flashes firmware raw to both A/B slots
        2. Uses lptools to clear-cow, destroy, recreate, and map dynamic partitions
        3. Flashes boot/dtbo/vbmeta raw to both slots
        4. Flashes dynamic partitions via zstd to active slot mapper devices
        5. Final unmap+map for clean state
        """

        fw_count = len(fw_files)
        sys_count = len(raw_sys_files)
        dyn_count = len(dynamic_list)

        # Build list of dynamic partition names for the batch operations
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
            lptools unmap "$partition$slot"
            lptools remove "$partition$slot"
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
            lptools unmap "$partition$slot"
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

        # -- Banner (Mehraan -- compact for recovery) --
        script += 'ui_print " "\n'
        script += 'ui_print "========================================="\n'
        script += 'ui_print " "\n'
        script += 'ui_print "          M E H R A A N"\n'
        script += 'ui_print " "\n'
        script += 'ui_print "     Flashing Script By Mehraan"\n'
        script += 'ui_print " "\n'
        script += 'ui_print "========================================="\n'
        script += f'ui_print "  Device   : {device}"\n'
        script += f'ui_print "  Codename : {codename}"\n'
        script += f'ui_print "  Version  : {fw_ver}"\n'
        script += 'ui_print "========================================="\n'
        script += 'ui_print " "\n\n'
        # ── Preflight ──
        script += 'checkDevice\n\n'
        script += 'unmountPartitions\n\n'
        script += 'ui_print " "\n'
        script += 'SLOT=$(getprop ro.boot.slot_suffix)\n'
        script += 'ui_print "Checking boot slot... ${SLOT}"\n\n'

        # Clear COW
        script += '# Remap\n'
        script += 'lptools clear-cow || true\n\n'

        # ── [1] Firmware (raw, both slots) ──
        if fw_files:
            script += 'ui_print " "\n'
            script += 'ui_print "Patching firmware to both slot..."\n'
            for fname, _ in fw_files:
                out_name = fname
                if fname.lower() == "logo.bin":
                    out_name = "logo.img"
                st = stem_of(out_name)
                script += f'flash_firmware_both_slots "firmware/{out_name}" "{st}"\n'
            script += '\n'

        # Clear existing partitions
        script += '# Clear existing partitions\n'
        script += 'process_partitions_for_slots "clear" \\\n'
        for i, name in enumerate(dyn_names):
            suffix = ' \\' if i < len(dyn_names) - 1 else ''
            script += f'        "{name}"{suffix}\n'
        script += '\n'

        # Create new partitions
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

        # Map all partitions on the active slot
        script += '# Map dynamic partitions for active slot\n'
        script += 'process_partitions_for_slot "map" "$SLOT" \\\n'
        for i, name in enumerate(dyn_names):
            suffix = ' \\' if i < len(dyn_names) - 1 else ''
            script += f'        "{name}"{suffix}\n'
        script += '\n'


        # ── [3] Flash system partitions (raw, both slots) ──
        if raw_sys_files:
            # Sort system partitions to match Rama's exact sequence
            sys_order = ["boot", "init_boot", "dtbo", "vendor_boot", "vbmeta", "vbmeta_system", "vbmeta_vendor"]
            sorted_sys = list(raw_sys_files)
            sorted_sys.sort(key=lambda x: sys_order.index(stem_of(x[0]).lower()) if stem_of(x[0]).lower() in sys_order else 99)
            
            script += 'ui_print " "\n'
            script += 'ui_print "Patching system..."\n'
            for fname, _ in sorted_sys:
                st = stem_of(fname)
                script += f'flash_firmware_both_slots "{fname}" "{st}"\n'

        # ── [4] Flash dynamic partitions (zstd, active slot via mapper) ──
        script += '\n'
        for name, size, pf in dynamic_list:
            script += f'flash_partition_zstd "{pf}.zst" "/dev/block/mapper/{name}$SLOT"\n'

        # ── [5] Final unmap+map for clean state ──
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


# ══════════════════════════════════════════════════════════════════════════════
#  APP SHELL
# ══════════════════════════════════════════════════════════════════════════════
class ROMBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Firmware To Flashable Builder -- Mehraan Edition v4")
        self.geometry("1200x850")
        self.minsize(1000, 700)
        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
                         fieldbackground=CARD2, background=CARD2,
                         foreground=TEXT, selectbackground=BORDER,
                         selectforeground=ACCENT, arrowcolor=ACCENT)
        style.map("TCombobox",
                  fieldbackground=[("readonly", CARD2)],
                  foreground=[("readonly", TEXT)])

        self._build_shell()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sb = tk.Frame(self, bg=SB, width=230)
        sb.grid(row=0, column=0, sticky="nsew", rowspan=2)
        sb.grid_propagate(False)

        tk.Label(sb, text="FW TO", font=(FONT, 26, "bold"), bg=SB, fg=ACCENT).pack(pady=(28, 0))
        tk.Label(sb, text="FLASHABLE", font=(FONT, 9, "bold"), bg=SB, fg=MUTED).pack()
        tk.Label(sb, text="Mehraan Edition v4", font=(FONT, 8), bg=SB, fg=MUTED).pack(pady=(2, 0))
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=18, pady=18)

        nav = tk.Frame(sb, bg=CARD)
        nav.pack(fill="x", padx=8)
        tk.Frame(nav, bg=ACCENT, width=4).pack(side="left", fill="y")
        inner = tk.Frame(nav, bg=CARD)
        inner.pack(side="left", fill="x", expand=True, padx=12, pady=12)
        tk.Label(inner, text="Flashable Builder", font=(FONT, 11, "bold"),
                 bg=CARD, fg=ACCENT).pack(anchor="w")
        tk.Label(inner, text="lptools Dynamic Partition",
                 font=(FONT, 8), bg=CARD, fg=MUTED).pack(anchor="w")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=18, pady=16)
        tk.Label(sb, text="PIPELINE", font=(FONT, 8, "bold"), bg=SB, fg=MUTED).pack(anchor="w", padx=18)
        steps = [
            "1. Browse ROM folder",
            "2. Unpack both supers",
            "3. Merge region -> base",
            "4. Collect all images",
            "5. Compress + build ZIP",
        ]
        for s in steps:
            tk.Label(sb, text=f"  {s}", font=(MONO, 7), bg=SB, fg=MUTED,
                     anchor="w").pack(anchor="w", padx=18, pady=1)

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=18, pady=12)
        tk.Label(sb, text="METHOD", font=(FONT, 8, "bold"), bg=SB, fg=MUTED).pack(anchor="w", padx=18)
        method_steps = [
            "FW -> raw both slots",
            "lptools clear-cow",
            "lptools destroy+create",
            "lptools map partitions",
            "SYS -> raw both slots",
            "DYN -> zstd active slot",
            "Final unmap+map",
        ]
        for s in method_steps:
            tk.Label(sb, text=f"  {s}", font=(MONO, 7), bg=SB, fg=MUTED,
                     anchor="w").pack(anchor="w", padx=18, pady=1)

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=18, pady=12)
        tk.Label(sb, text="TOOLS", font=(FONT, 8, "bold"), bg=SB, fg=MUTED).pack(anchor="w", padx=18)
        for tool in ["imgkit.exe", "zstd.exe", "zstd-arm64"]:
            row = tk.Frame(sb, bg=SB)
            row.pack(fill="x", padx=18, pady=2)
            found = os.path.exists(os.path.join(BIN_DIR, tool))
            tk.Label(row, text=tool, font=(MONO, 8), bg=SB, fg=TEXT,
                     width=13, anchor="w").pack(side="left")
            tk.Label(row, text="OK" if found else "MISS", font=(MONO, 8, "bold"),
                     bg=SB, fg=OK_C if found else ERR_C).pack(side="left")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=18, side="bottom", pady=(0, 8))
        tk.Label(sb, text="v4.0 | lptools Method",
                 font=(FONT, 7), bg=SB, fg=MUTED).pack(side="bottom", pady=(0, 4))

        main = tk.Frame(self, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        self.page = BuildPage(main, self)
        self.page.grid(row=0, column=0, sticky="nsew")

        sbar = tk.Frame(self, bg=SB, height=26)
        sbar.grid(row=1, column=1, sticky="ew")
        self._status_var = tk.StringVar(value="  Ready")
        tk.Label(sbar, textvariable=self._status_var, font=(FONT, 8),
                 bg=SB, fg=MUTED, anchor="w", padx=14).pack(fill="both", expand=True)

    def set_status(self, text):
        self._status_var.set(f"  {text}")


if __name__ == "__main__":
    app = ROMBuilder()
    app.mainloop()
