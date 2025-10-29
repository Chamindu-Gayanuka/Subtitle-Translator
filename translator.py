# -*- coding: utf-8 -*-
"""
SRT Translator & UTF-8 Converter – Dual Mode App (CJK REMOVED FROM TARGET)
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pysrt, os
from deep_translator import GoogleTranslator
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import re
import time
from functools import wraps

# -------------------------------------------------
# NEW: Encoding detection
# -------------------------------------------------
try:
    from charset_normalizer import from_path   # faster & more accurate
except Exception:                              # pragma: no cover
    import chardet
    _USE_CHARDET = True
else:
    _USE_CHARDET = False

# -------------------------------------------------
# Settings
# -------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

LANGUAGES = {
    "English": "en", "Sinhala": "si", "Arabic": "ar", "Dutch": "nl",
    "French": "fr", "German": "de", "Italian": "it", "Polish": "pl",
    "Romanian": "ro", "Greek": "el", "Hungarian": "hu", "Swedish": "sv",
    "Danish": "da", "Finnish": "fi", "Norwegian": "no", "Czech": "cs",
    "Croatian": "hr", "Ukrainian": "uk", "Indonesian": "id", "Malay": "ms",
    "Filipino": "tl", "Japanese": "ja", "Korean": "ko", "Turkish": "tr",
    "Russian": "ru", "Chinese": "zh", "Vietnamese": "vi", "Thai": "th"
}
SRC_LANGS = ["Auto"] + sorted(LANGUAGES.keys())
CJK_NAMES = {"Chinese", "Japanese", "Korean", "Thai", "Vietnamese"}
DEST_LANGS = sorted([lang for lang in LANGUAGES.keys() if lang not in CJK_NAMES])
CJK_LANGUAGES = {"Chinese", "Japanese", "Korean", "Thai", "Vietnamese"}

# -------------------------------------------------
# Retry Decorator
# -------------------------------------------------
def retry(max_attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

# -------------------------------------------------
# Text Cleaning
# -------------------------------------------------
def clean_text(text):
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# -------------------------------------------------
# Scrollable ComboBox (unchanged)
# -------------------------------------------------
class ScrollableComboBox(ctk.CTkFrame):
    # ... (exact same code as before) ...
    # (omitted for brevity – copy-paste from your original script)
    def __init__(self, master, values, default="", width=300, **kwargs):
        super().__init__(master, **kwargs)
        self.values = values
        self.var = ctk.StringVar(value=default)
        self.display = ctk.CTkLabel(self, text=default, width=width, height=40,
                                    corner_radius=10, fg_color="#2f2f2f", text_color="white",
                                    font=ctk.CTkFont(size=12), anchor="center", justify="center")
        self.display.pack(pady=(0, 4))
        self.display.bind("<Button-1>", lambda e: self._toggle())
        self.drop = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
        self.listbox = tk.Listbox(self.drop, height=8, selectmode="browse", activestyle="none",
                                  background="#2b2b2b", foreground="white",
                                  selectbackground="#1f6aa5", font=("Segoe UI", 11),
                                  highlightthickness=0, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True, padx=3, pady=3)
        sb = ctk.CTkScrollbar(self.drop, command=self.listbox.yview, width=16)
        sb.pack(side="right", fill="y", padx=(0, 3), pady=3)
        self.listbox.configure(yscrollcommand=sb.set)
        for v in values:
            self.listbox.insert(tk.END, v)
        self.listbox.bind("<<ListboxSelect>>", self._select)
        self.listbox.bind("<Escape>", lambda e: self._hide())
        self.listbox.bind("<FocusOut>", lambda e: self._hide())
        self.listbox.bind("<MouseWheel>", self._wheel)
        self.listbox.bind("<Button-4>", self._wheel)
        self.listbox.bind("<Button-5>", self._wheel)
        self.shown = False
    def _toggle(self):
        if self.shown: self._hide()
        else: self._show()
    def _show(self):
        if self.shown: return
        self.drop.pack(fill="x", pady=(0, 4))
        self.shown = True
        self.listbox.focus_set()
        try:
            idx = self.values.index(self.var.get())
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
        except Exception: pass
    def _hide(self):
        if not self.shown: return
        self.drop.pack_forget()
        self.shown = False
    def _select(self, _=None):
        sel = self.listbox.curselection()
        if sel:
            val = self.values[sel[0]]
            self.var.set(val)
            self.display.configure(text=val)
            self._hide()
    def _wheel(self, ev):
        if ev.delta:
            self.listbox.yview_scroll(-1 * (ev.delta // 120), "units")
        elif ev.num == 4: self.listbox.yview_scroll(-1, "units")
        elif ev.num == 5: self.listbox.yview_scroll(1, "units")
        return "break"
    def get(self): return self.var.get()
    def set(self, v):
        if v in self.values:
            self.var.set(v)
            self.display.configure(text=v)

# -------------------------------------------------
# Main App
# -------------------------------------------------
class SRTTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        w, h = 880, 780
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.title("SRT Translator & UTF-8 Converter")
        self.mode = tk.StringVar(value="translate")
        self.subs = None
        self.translated_subs = None
        self.selected_files = []
        self._menu_ui()
        self._translate_ui()

    # -------------------------------------------------
    # UI helpers
    # -------------------------------------------------
    def _menu_ui(self):
        mf = ctk.CTkFrame(self)
        mf.pack(pady=10)
        ctk.CTkButton(mf, text="Translate SRT", width=180,
                      command=self._show_translate).grid(row=0, column=0, padx=10)
        ctk.CTkButton(mf, text="Convert to UTF-8", width=180,
                      command=self._show_utf8).grid(row=0, column=1, padx=10)

    def _clear_main(self):
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w not in [self.children.get('!ctkframe')]:
                w.destroy()
        for w in self.winfo_children():
            if isinstance(w, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkProgressBar)):
                w.destroy()

    def _show_translate(self):
        self._clear_main()
        self.mode.set("translate")
        self._translate_ui()

    def _show_utf8(self):
        self._clear_main()
        self.mode.set("utf8")
        self._utf8_ui()

    # -------------------------------------------------
    # TRANSLATE UI (unchanged)
    # -------------------------------------------------
    def _translate_ui(self):
        ctk.CTkLabel(self, text="SRT Subtitle Translator",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=30)
        ff = ctk.CTkFrame(self)
        ff.pack(pady=12, padx=70, fill="x")
        self.file_lbl = ctk.CTkLabel(ff, text="No file selected",
                                     font=ctk.CTkFont(size=12), text_color="gray")
        self.file_lbl.pack(side="left", padx=15, fill="x", expand=True)
        ctk.CTkButton(ff, text="Browse .srt", width=130,
                      command=self._browse).pack(side="right", padx=15)

        lf = ctk.CTkFrame(self)
        lf.pack(pady=30, padx=70, fill="x")
        lf.grid_columnconfigure(0, weight=1, uniform="a")
        lf.grid_columnconfigure(1, weight=1, uniform="a")
        ctk.CTkLabel(lf, text="Source Language:",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, pady=(0, 8), sticky="s")
        ctk.CTkLabel(lf, text="Target Language:",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=1, pady=(0, 8), sticky="s")
        self.src = ScrollableComboBox(lf, SRC_LANGS, "Auto")
        self.src.grid(row=1, column=0, sticky="ew", padx=(20, 10))
        self.dst = ScrollableComboBox(lf, DEST_LANGS, "Sinhala")
        self.dst.grid(row=1, column=1, sticky="ew", padx=(10, 20))

        self.tr_btn = ctk.CTkButton(self, text="Translate SRT (Fast)",
                                    height=52, font=ctk.CTkFont(size=15, weight="bold"),
                                    state="disabled", command=self._start)
        self.tr_btn.pack(pady=28)
        self.prog = ctk.CTkProgressBar(self, width=700)
        self.prog.pack(pady=14); self.prog.set(0)
        self.stat = ctk.CTkLabel(self, text="Ready", text_color="lightgray",
                                 font=ctk.CTkFont(size=12))
        self.stat.pack(pady=6)
        self.save_btn = ctk.CTkButton(self, text="Save Translated SRT",
                                      height=46, state="disabled", command=self._save)
        self.save_btn.pack(pady=18)

    # -------------------------------------------------
    # UTF-8 UI (unchanged)
    # -------------------------------------------------
    def _utf8_ui(self):
        ctk.CTkLabel(self, text="SRT UTF-8 Converter",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=30)
        ff = ctk.CTkFrame(self)
        ff.pack(pady=12, padx=70, fill="x")
        self.files_lbl = ctk.CTkLabel(ff, text="No files selected",
                                      font=ctk.CTkFont(size=12), text_color="gray")
        self.files_lbl.pack(side="left", padx=15, fill="x", expand=True)
        ctk.CTkButton(ff, text="Select up to 20 .srt files", width=180,
                      command=self._browse_utf8).pack(side="right", padx=15)

        self.convert_btn = ctk.CTkButton(self, text="Convert to UTF-8",
                                         height=52, font=ctk.CTkFont(size=15, weight="bold"),
                                         state="disabled", command=self._convert_utf8)
        self.convert_btn.pack(pady=30)
        self.stat = ctk.CTkLabel(self, text="Ready", text_color="lightgray",
                                 font=ctk.CTkFont(size=12))
        self.stat.pack(pady=6)
        self.prog = ctk.CTkProgressBar(self, width=700)
        self.prog.pack(pady=14); self.prog.set(0)

    # -------------------------------------------------
    # TRANSLATION LOGIC (unchanged)
    # -------------------------------------------------
    def _browse(self):
        p = filedialog.askopenfilename(filetypes=[("SRT Files", "*.srt")])
        if p: self._load(p)

    def _load(self, path):
        try:
            self.subs = pysrt.open(path, encoding="utf-8")
            name = os.path.basename(path)
            cnt = len([s for s in self.subs if s.text.strip()])
            self.file_lbl.configure(text=f"Loaded: {name} ({cnt} lines)")
            self.tr_btn.configure(state="normal")
            self.save_btn.configure(state="disabled")
            self.stat.configure(text="Ready to translate")
            self.prog.set(0)
        except Exception as e:
            messagebox.showerror("Error", f"Load failed:\n{e}")

    def _start(self):
        if not self.subs: return
        self.tr_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.stat.configure(text="Preparing...", text_color="yellow")
        self.prog.set(0)
        Thread(target=self._translate, daemon=True).start()

    @retry(max_attempts=3)
    def _safe_translate(self, text, src, dst):
        return GoogleTranslator(source=src, target=dst).translate(text)

    def _translate(self):
        subs = self.subs
        idxs = [i for i, s in enumerate(subs) if s.text.strip()]
        total = len(idxs)
        if not total:
            self.after(0, lambda: messagebox.showinfo("Empty", "No text to translate."))
            self.after(0, self._enable)
            return

        dst_lang = self.dst.get()
        is_cjk = dst_lang in CJK_LANGUAGES
        BATCH = 5 if is_cjk else 15
        batches = [idxs[i:i + BATCH] for i in range(0, len(idxs), BATCH)]
        out = [""] * len(subs)
        done = 0
        src = "auto" if self.src.get() == "Auto" else LANGUAGES[self.src.get()]
        dst = LANGUAGES[dst_lang]

        def batch_job(idxs_batch):
            txts = [clean_text(subs[i].text) for i in idxs_batch]
            delimiter = f"\n---SUB_{hash(tuple(txts)) & 0xFFFFFF:06x}---\n"
            combined = delimiter.join(txts)
            try:
                tr = self._safe_translate(combined, src, dst)
                if not tr:
                    raise Exception("Translation returned empty")
                parts = tr.split(delimiter)
                if len(parts) != len(txts):
                    return [(i, f"[SPLIT ERROR: {len(parts)}/{len(txts)} parts]") for i in idxs_batch]
                return [(idxs_batch[j], parts[j].strip() or txts[j]) for j in range(len(txts))]
            except Exception as e:
                return [(i, f"[ERROR: {str(e)[:50]}]") for i in idxs_batch]

        max_workers = 3 if is_cjk else 5
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(batch_job, b) for b in batches]
            for fut in futures:
                try:
                    results = fut.result(timeout=60)
                    for i, txt in results:
                        out[i] = txt
                    done += len(results)
                    progress = done / total
                    self.after(0, lambda p=progress: self.prog.set(p))
                    self.after(0, lambda d=done, t=total: self.stat.configure(
                        text=f"Translating... {d}/{t}", text_color="cyan"))
                except Exception as e:
                    self.after(0, lambda err=str(e): self.stat.configure(
                        text=f"Batch error: {err}", text_color="red"))

        self.translated_subs = [
            pysrt.SubRipItem(index=s.index, start=s.start, end=s.end,
                             text=out[i] if out[i] and out[i] != s.text.strip() else s.text)
            for i, s in enumerate(subs)
        ]
        self.after(0, self._done)

    def _done(self):
        self.stat.configure(text="Translation Complete!", text_color="#00ff00")
        self.save_btn.configure(state="normal")
        self.tr_btn.configure(state="normal")

    def _enable(self):
        self.tr_btn.configure(state="normal")
        self.save_btn.configure(state="disabled")

    def _save(self):
        if not self.translated_subs: return
        p = filedialog.asksaveasfilename(defaultextension=".srt",
                                         filetypes=[("SRT Files", "*.srt")])
        if p:
            try:
                pysrt.SubRipFile(self.translated_subs).save(p, encoding="utf-8")
                messagebox.showinfo("Success", f"Saved:\n{os.path.basename(p)}")
                self.stat.configure(text=f"Saved: {os.path.basename(p)}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed:\n{e}")

    # -------------------------------------------------
    # UTF-8 CONVERTER LOGIC – **FIXED**
    # -------------------------------------------------
    def _browse_utf8(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT Files", "*.srt")])
        if not files: return
        if len(files) > 20:
            messagebox.showwarning("Limit", "You can select up to 20 files only.")
            return
        self.selected_files = files
        self.files_lbl.configure(text=f"{len(files)} file(s) selected")
        self.convert_btn.configure(state="normal")
        self.prog.set(0)
        self.stat.configure(text="Ready")

    def _convert_utf8(self):
        if not self.selected_files: return
        Thread(target=self._run_convert_utf8, daemon=True).start()

    def _run_convert_utf8(self):
        files = self.selected_files
        total = len(files)
        done = 0

        save_dir = filedialog.askdirectory(title="Select Folder to Save Converted Files")
        if not save_dir:
            self.after(0, self._enable_utf8)
            return

        for path in files:
            try:
                name = os.path.basename(path)
                out_path = os.path.join(save_dir, name)

                # ----- 1. Detect original encoding -----
                if _USE_CHARDET:
                    with open(path, "rb") as f:
                        raw = f.read()
                    enc = chardet.detect(raw)['encoding'] or 'latin-1'
                else:
                    result = from_path(path)
                    enc = result.best().encoding if result.best() else 'utf-8'

                # ----- 2. Read with detected encoding -----
                with open(path, "r", encoding=enc, errors='replace') as f:
                    content = f.read()

                # ----- 3. Write as UTF-8 (preserve BOM if original had it) -----
                bom = '\ufeff' if content.startswith('\ufeff') else ''
                with open(out_path, "w", encoding="utf-8-sig", newline='') as f:
                    f.write(bom + content)

                done += 1
                self.after(0, lambda p=done/total: self.prog.set(p))
                self.after(0, lambda d=done: self.stat.configure(
                    text=f"Converted {d}/{total} – {name}", text_color="cyan"))
            except Exception as e:
                self.after(0, lambda err=str(e), p=path: messagebox.showerror(
                    "Error", f"Failed: {os.path.basename(p)}\n{err}"))

        self.after(0, lambda: self.stat.configure(
            text="UTF-8 Conversion Complete!", text_color="#00ff00"))
        self.after(0, lambda d=save_dir: messagebox.showinfo(
            "Done", f"All files saved in:\n{d}"))
        self.after(0, self._enable_utf8)

    def _enable_utf8(self):
        self.convert_btn.configure(state="normal")

# -------------------------------------------------
if __name__ == "__main__":
    SRTTranslatorApp().mainloop()