# -*- coding: utf-8 -*-
"""
Version: 1.0.2
Author: Chamindu Gayanuka (Updated by Dula Yasi)
Copyright: MIT License
Contributors: Chamindu Gayanuka, Yasitha Dulaj
Description: Python custom tkinter based subtitles translator.
Supports Batch Translation & UTF-8 Conversion
Updated: User can set output folder path for translated files.
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

# Optional: charset detection
try:
    from charset_normalizer import from_path
except Exception:
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
# Retry decorator
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
# Text cleaning
# -------------------------------------------------
def clean_text(text):
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# -------------------------------------------------
# Scrollable ComboBox
# -------------------------------------------------
class ScrollableComboBox(ctk.CTkFrame):
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
        w, h = 1300, 700
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.title("SRT Translator & UTF-8 Converter")

        # Icon (ICO for Windows)
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print("Failed to load .ico icon:", e)

        self.mode = tk.StringVar(value="translate")
        self.selected_files = []
        self.translated_subs_list = []

        # NEW: store output folder path, default empty (use input folder if not set)
        self.output_folder = tk.StringVar(value="")

        self._menu_ui()
        self._translate_ui()  # initial UI

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
    # TRANSLATE UI
    # -------------------------------------------------
    def _translate_ui(self):
        ctk.CTkLabel(self, text="SRT Subtitle Translator",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=30)

        # File selection
        ff = ctk.CTkFrame(self)
        ff.pack(pady=12, padx=70, fill="x")
        self.file_lbl = ctk.CTkLabel(ff, text="No files selected",
                                     font=ctk.CTkFont(size=12), text_color="gray")
        self.file_lbl.pack(side="left", padx=15, fill="x", expand=True)
        ctk.CTkButton(ff, text="Browse .srt Files", width=180,
                      command=self._browse).pack(side="right", padx=15)

        # Languages selection
        lf = ctk.CTkFrame(self)
        lf.pack(pady=10, padx=70, fill="x")
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

        # Translate button
        self.tr_btn = ctk.CTkButton(self, text="Translate SRT (Fast)",
                                    height=52, font=ctk.CTkFont(size=15, weight="bold"),
                                    state="disabled", command=self._start)
        self.tr_btn.pack(pady=28)

        # Progress
        self.prog = ctk.CTkProgressBar(self, width=900)
        self.prog.pack(pady=14); self.prog.set(0)
        self.stat = ctk.CTkLabel(self, text="Ready", text_color="lightgray",
                                 font=ctk.CTkFont(size=12))
        self.stat.pack(pady=6)

        # NEW: Output folder selection
        of = ctk.CTkFrame(self)
        of.pack(pady=10, padx=70, fill="x")
        self.output_lbl = ctk.CTkLabel(of,
                                       text="Browse custom save location [Default is input folder]",
                                       font=ctk.CTkFont(size=12),
                                       text_color="gray")
        self.output_lbl.pack(side="left", padx=10, fill="x", expand=True)
        ctk.CTkButton(of, text="Browse", width=120, command=self._browse_output_folder).pack(side="right", padx=10)


        # Save button
        self.save_btn = ctk.CTkButton(self, text="Save All Translated SRTs",
                                      height=46, state="disabled", command=self._save_all)
        self.save_btn.pack(pady=18)

    # NEW: browse output folder
    def _browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            self.output_lbl.configure(text=f"Output Folder: {folder}", text_color="#00ff00")

    # -------------------------------------------------
    # UTF-8 UI
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
        self.prog = ctk.CTkProgressBar(self, width=900)
        self.prog.pack(pady=14);
        self.prog.set(0)

    # -------------------------------------------------
    # Browse & translation logic
    # -------------------------------------------------
    def _browse(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT Files", "*.srt")])
        if files:
            self.selected_files = list(files)
            names = [os.path.basename(f) for f in self.selected_files]
            self.file_lbl.configure(text=f"{len(names)} files selected: {', '.join(names[:5])}" + ("..." if len(names) > 5 else ""))
            self.tr_btn.configure(state="normal")
            self.save_btn.configure(state="disabled")
            self.prog.set(0)
            self.stat.configure(text="Ready to translate")
            self.translated_subs_list = []

    def _start(self):
        if not self.selected_files: return
        self.tr_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.stat.configure(text="Translating...", text_color="yellow")
        self.prog.set(0)
        Thread(target=self._translate_batch, daemon=True).start()

    @retry(max_attempts=3)
    def _safe_translate(self, text, src, dst):
        return GoogleTranslator(source=src, target=dst).translate(text)

    def _translate_batch(self):
        total_files = len(self.selected_files)
        for idx, path in enumerate(self.selected_files):
            try:
                subs = pysrt.open(path, encoding="utf-8")
            except Exception as e:
                self.after(0, lambda msg=str(e): messagebox.showerror("Load Error", f"Failed to load {path}:\n{msg}"))
                continue

            idxs = [i for i, s in enumerate(subs) if s.text.strip()]
            total = len(idxs)
            if not total: continue

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
                        progress = (idx + done / total) / total_files
                        self.after(0, lambda p=progress: self.prog.set(p))
                        self.after(0, lambda d=done, t=total, f=idx+1, tf=total_files:
                                   self.stat.configure(text=f"Translating file {f}/{tf}: {d}/{t} lines", text_color="cyan"))
                    except Exception as e:
                        self.after(0, lambda err=str(e): self.stat.configure(
                            text=f"Batch error: {err}", text_color="red"))

            translated_subs = [
                pysrt.SubRipItem(index=s.index, start=s.start, end=s.end,
                                 text=out[i] if out[i] and out[i] != s.text.strip() else s.text)
                for i, s in enumerate(subs)
            ]
            self.translated_subs_list.append((path, translated_subs))

        self.after(0, self._done_batch)

    def _done_batch(self):
        self.stat.configure(text="Translation Complete!", text_color="#00ff00")
        self.save_btn.configure(state="normal")
        self.tr_btn.configure(state="normal")

    # -------------------------------------------------
    # Save all to output folder
    # -------------------------------------------------
    def _save_all(self):
        if not self.translated_subs_list:
            messagebox.showinfo("Info", "No translated files to save.")
            return

        # Determine output folder
        folder = self.output_folder.get() or os.path.dirname(self.selected_files[0])

        for original_path, translated_subs in self.translated_subs_list:
            name, ext = os.path.splitext(os.path.basename(original_path))
            # Get selected target language correctly
            selected_language = self.dst.get()
            language_code = LANGUAGES[selected_language]
            save_path = os.path.join(folder, f"{name}.{language_code}{ext}")
            try:
                pysrt.SubRipFile(translated_subs).save(save_path, encoding="utf-8")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save {save_path}:\n{e}")

        self.stat.configure(text=f"All translated SRTs saved!", text_color="#00ff00")
        messagebox.showinfo("Done", f"All translated SRT files saved to:\n{folder}")

# -------------------------------------------------
    # UTF-8 Converter Logic
    # -------------------------------------------------
    def _browse_utf8(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT Files", "*.srt")])
        if files:
            self.selected_files = files[:20]  # Limit 20 files
            names = [os.path.basename(f) for f in self.selected_files]
            self.files_lbl.configure(text=f"{len(names)} files selected: {', '.join(names)}")
            self.convert_btn.configure(state="normal")
            self.prog.set(0)
            self.stat.configure(text="Ready")

    def _convert_utf8(self):
        if not self.selected_files: return
        self.convert_btn.configure(state="disabled")
        Thread(target=self._utf8_thread, daemon=True).start()

    def _utf8_thread(self):
        total = len(self.selected_files)
        done = 0
        for f in self.selected_files:
            try:
                encoding = "utf-8"
                if _USE_CHARDET:
                    encoding = chardet.detect(open(f, "rb").read())["encoding"] or "utf-8"
                else:
                    res = from_path(f)
                    encoding = res.best().encoding if res.best() else "utf-8"

                text = open(f, "r", encoding=encoding, errors="ignore").read()
                open(f, "w", encoding="utf-8").write(text)
            except Exception as e:
                print(f"UTF-8 conversion failed for {f}: {e}")
            done += 1
            progress = done / total
            self.after(0, lambda p=progress: self.prog.set(p))
            self.after(0, lambda d=done, t=total: self.stat.configure(
                text=f"Converting... {d}/{t}", text_color="cyan"))
        self.after(0, lambda: self.stat.configure(text="UTF-8 Conversion Complete!", text_color="#00ff00"))
        self.after(0, lambda: self.convert_btn.configure(state="normal"))

# -------------------------------------------------
# Run App
# -------------------------------------------------
if __name__ == "__main__":
    app = SRTTranslatorApp()
    app.mainloop()
