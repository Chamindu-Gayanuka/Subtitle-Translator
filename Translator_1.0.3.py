# -*- coding: utf-8 -*-
"""
Version: 1.0.3
Author: Chamindu Gayanuka (Updated by Dula Yasi)
Copyright: MIT License
Contributors: Chamindu Gayanuka, Yasitha Dulaj
Description: Python custom tkinter based subtitles translator.
Supports Batch Translation & UTF-8 Conversion
Updated: Add English Subtitle Extractor from Video Files
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pysrt
import os
import re
import time
import json
import subprocess
import threading
import queue
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
import sys

# Charset detection
try:
    from charset_normalizer import from_path
    _USE_NORMALIZER = True
except Exception:
    import chardet
    _USE_NORMALIZER = False

# -------------------------------------------------
# Resource Path for PyInstaller (Icon + FFmpeg)
# -------------------------------------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Paths for bundled files
ICON_PATH = resource_path("icon.ico")
FFMPEG_PATH = resource_path("ffmpeg.exe")
FFPROBE_PATH = resource_path("ffprobe.exe")
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

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
    "Russian": "ru", "Chinese (Simplified)": "zh-CN", "Chinese (Traditional)": "zh-TW",
    "Vietnamese": "vi", "Thai": "th", "Portuguese": "pt", "Spanish": "es",
    "Hindi": "hi", "Bengali": "bn"
}

SRC_LANGS = ["Auto"] + sorted(LANGUAGES.keys())
ALL_DEST_LANGS = sorted(LANGUAGES.keys())
CJK_LANGUAGES = {"Chinese (Simplified)", "Chinese (Traditional)", "Japanese", "Korean", "Thai", "Vietnamese"}

# -------------------------------------------------
# Helpers
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
                                    font=ctk.CTkFont(size=12), anchor="center")
        self.display.pack(pady=(0, 4))
        self.display.bind("<Button-1>", lambda e: self._toggle())
        self.drop = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
        self.listbox = tk.Listbox(self.drop, height=10, selectmode="browse", activestyle="none",
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
        except: pass

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

    def get(self): return self.var.get()
    def set(self, v):
        if v in self.values:
            self.var.set(v)
            self.display.configure(text=v)

# -------------------------------------------------
# FFmpeg Helpers (No Console Window)
# -------------------------------------------------
def run_ffprobe(file_path):
    cmd = [FFPROBE_PATH, "-v", "error", "-select_streams", "s",
           "-show_entries", "stream=index:stream_tags=language,title", "-of", "json", file_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, creationflags=CREATE_NO_WINDOW)
        return json.loads(result.stdout) if result.returncode == 0 else None
    except Exception:
        return None

def is_english_stream(stream):
    tags = stream.get("tags", {}) or {}
    lang = (tags.get("language") or "").lower()
    title = (tags.get("title") or "").lower()
    return lang in {"en", "eng", "en-gb", "en-us"} or "english" in title or "eng" in title

def find_english_subtitle_streams(file_path):
    data = run_ffprobe(file_path)
    if not data: return []
    return [s for s in data.get("streams", []) if is_english_stream(s)]

def extract_subtitle_stream(file_path, stream_index, out_path):
    cmd = [FFMPEG_PATH, "-y", "-i", file_path, "-map", f"0:{stream_index}", "-c:s", "srt", out_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, creationflags=CREATE_NO_WINDOW)
        return result.returncode == 0, result.stderr
    except Exception:
        return False, "ffmpeg error"

# -------------------------------------------------
# Main Application
# -------------------------------------------------
class SRTTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        w, h = 1300, 700
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.title("Subtitles Translator - Translate • UTF-8 • Extract English Subs")

        # Title bar icon - fixed for .exe
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except:
                pass  # Ignore if fails

        self.selected_files = []
        self.translated_subs_list = []
        self.output_folder = tk.StringVar(value="")
        self.cjk_enabled = tk.BooleanVar(value=False)

        self.video_files = []
        self.extractor_output_dir = ""
        self.extractor_queue = queue.Queue()
        self.utf8_queue = queue.Queue()

        self._menu_ui()
        self._translate_ui()
        self.after(100, self._process_queues)

    def _menu_ui(self):
        mf = ctk.CTkFrame(self)
        mf.pack(pady=15)
        ctk.CTkButton(mf, text="Translate SRT", width=200, height=40,
                      font=ctk.CTkFont(size=13, weight="bold"), command=self._show_translate).grid(row=0, column=0, padx=12)
        ctk.CTkButton(mf, text="Convert to UTF-8", width=200, height=40,
                      font=ctk.CTkFont(size=13, weight="bold"), command=self._show_utf8).grid(row=0, column=1, padx=12)
        ctk.CTkButton(mf, text="Extract English Subs", width=200, height=40,
                      font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1a8754",
                      command=self._show_extractor).grid(row=0, column=2, padx=12)

    def _clear_main(self):
        for widget in self.winfo_children():
            if widget.winfo_class() == 'TFrame' and widget != self.winfo_children()[0]:
                widget.destroy()
            elif widget.winfo_class() != 'TFrame':
                widget.destroy()

    def _show_translate(self):
        self._clear_main()
        self._menu_ui()
        self._translate_ui()

    def _show_utf8(self):
        self._clear_main()
        self._menu_ui()
        self._utf8_ui()

    def _show_extractor(self):
        self._clear_main()
        self._menu_ui()
        self._extractor_ui()

    # =============================================
    # 1. TRANSLATE UI + FAST & RELIABLE BATCH
    # =============================================
    def _translate_ui(self):
        ctk.CTkLabel(self, text="SRT Subtitle Translator", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        ff = ctk.CTkFrame(self)
        ff.pack(pady=10, padx=80, fill="x")
        self.file_lbl = ctk.CTkLabel(ff, text="No files selected", text_color="gray")
        self.file_lbl.pack(side="left", padx=20, fill="x", expand=True)
        ctk.CTkButton(ff, text="Browse .srt Files", command=self._browse).pack(side="right", padx=20)

        lf = ctk.CTkFrame(self)
        lf.pack(pady=10, padx=80, fill="x")
        lf.grid_columnconfigure(0, weight=1); lf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(lf, text="Source Language:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, pady=(0,8), sticky="w", padx=20)
        ctk.CTkLabel(lf, text="Target Language:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=1, pady=(0,8), sticky="w", padx=20)

        self.src = ScrollableComboBox(lf, SRC_LANGS, "Auto", width=380)
        self.src.grid(row=1, column=0, sticky="ew", padx=(20,10), pady=(0,10))

        self.dest_langs = [l for l in ALL_DEST_LANGS if l not in CJK_LANGUAGES]
        self.dst = ScrollableComboBox(lf, self.dest_langs, "Sinhala", width=380)
        self.dst.grid(row=1, column=1, sticky="ew", padx=(10,20), pady=(0,10))

        cjk_frame = ctk.CTkFrame(self)
        cjk_frame.pack(pady=8)
        self.cjk_check = ctk.CTkCheckBox(cjk_frame, text="Enable CJK Target Languages (Chinese, Japanese, Korean, Thai, Vietnamese)",
                                         variable=self.cjk_enabled, command=self._toggle_cjk)
        self.cjk_check.pack()

        self.tr_btn = ctk.CTkButton(self, text="Start Translation", height=50, font=ctk.CTkFont(size=15, weight="bold"), state="disabled", command=self._start)
        self.tr_btn.pack(pady=20)

        self.prog = ctk.CTkProgressBar(self, width=950)
        self.prog.pack(pady=10); self.prog.set(0)
        self.stat = ctk.CTkLabel(self, text="Ready", text_color="#00ff00")
        self.stat.pack(pady=5)

        of = ctk.CTkFrame(self)
        of.pack(pady=10, padx=80, fill="x")
        self.output_lbl = ctk.CTkLabel(of, text="Output: Same folder as input", text_color="gray")
        self.output_lbl.pack(side="left", padx=20, fill="x", expand=True)
        ctk.CTkButton(of, text="Choose Output Folder", command=self._browse_output_folder).pack(side="right", padx=20)

        self.save_btn = ctk.CTkButton(self, text="Save All Translated Files", height=50, state="disabled", command=self._save_all)
        self.save_btn.pack(pady=20)

    def _toggle_cjk(self):
        current = self.dst.get()
        new_langs = ALL_DEST_LANGS if self.cjk_enabled.get() else [l for l in ALL_DEST_LANGS if l not in CJK_LANGUAGES]
        self.dst.destroy()
        default = current if current in new_langs else new_langs[0]
        self.dst = ScrollableComboBox(self.winfo_children()[3], new_langs, default, width=380)
        self.dst.grid(row=1, column=1, sticky="ew", padx=(10,20), pady=(0,10))

    def _browse(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT Files", "*.srt")])
        if files:
            self.selected_files = list(files)
            self.file_lbl.configure(text=f"{len(files)} files selected")
            self.tr_btn.configure(state="normal")
            self.save_btn.configure(state="disabled")
            self.translated_subs_list = []

    def _browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            self.output_lbl.configure(text=f"Output: {folder}", text_color="#00ff00")

    def _start(self):
        if not self.selected_files: return
        self.tr_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.stat.configure(text="Translating...", text_color="yellow")
        self.prog.set(0)
        Thread(target=self._translate_batch, daemon=True).start()

    def _translate_batch(self):
        total_files = len(self.selected_files)
        src_code = "auto" if self.src.get() == "Auto" else LANGUAGES[self.src.get()]
        dst_lang = self.dst.get()
        dst_code = LANGUAGES[dst_lang]
        is_cjk = dst_lang in CJK_LANGUAGES
        BATCH_SIZE = 5 if is_cjk else 15
        MAX_WORKERS = 3 if is_cjk else 5

        for idx, path in enumerate(self.selected_files):
            try:
                subs = pysrt.open(path, encoding="utf-8")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Cannot open {path}\n{e}"))
                continue

            idxs = [i for i, s in enumerate(subs) if s.text.strip()]
            total = len(idxs)
            if not total: continue

            batches = [idxs[i:i + BATCH_SIZE] for i in range(0, len(idxs), BATCH_SIZE)]
            out = [""] * len(subs)
            done = 0

            def batch_job(batch_idxs):
                texts = [clean_text(subs[i].text) for i in batch_idxs]
                if not texts: return []
                unique_id = hash(tuple(texts)) & 0xFFFFFFFFFFFFFFFF
                delimiter = f"\n\n||---UNIQUE_SUB_SPLIT_{unique_id}---||\n\n"
                combined = delimiter.join(texts)
                try:
                    translated = GoogleTranslator(source=src_code, target=dst_code).translate(combined)
                    if not translated:
                        raise Exception("Empty response")
                    parts = translated.split(delimiter)
                    if len(parts) != len(texts):
                        return [(batch_idxs[j], f"[PARTIAL FAIL] {texts[j]}") for j in range(len(texts))]
                    return [(batch_idxs[j], parts[j].strip() or texts[j]) for j in range(len(texts))]
                except Exception as e:
                    self.after(0, lambda: self.stat.configure(text=f"Batch error: {str(e)[:50]}", text_color="red"))
                    return [(i, subs[i].text) for i in batch_idxs]

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = [pool.submit(batch_job, b) for b in batches]
                for fut in futures:
                    try:
                        results = fut.result(timeout=180)
                        for i, txt in results:
                            out[i] = txt
                        done += len(results)
                        progress = (idx + done / total) / total_files
                        self.after(0, lambda p=progress: self.prog.set(p))
                        self.after(0, lambda: self.stat.configure(text=f"File {idx+1}/{total_files} — {done}/{total} lines", text_color="cyan"))
                    except Exception as e:
                        self.after(0, lambda: self.stat.configure(text=f"Error: {e}", text_color="red"))

            translated_subs = [pysrt.SubRipItem(index=s.index, start=s.start, end=s.end,
                                text=out[i] if out[i] else s.text) for i, s in enumerate(subs)]
            self.translated_subs_list.append((path, translated_subs))

        self.after(0, self._done_batch)

    def _done_batch(self):
        self.stat.configure(text="Translation Complete!", text_color="#00ff00")
        self.save_btn.configure(state="normal")
        self.tr_btn.configure(state="normal")

    def _save_all(self):
        if not self.translated_subs_list: return
        folder = self.output_folder.get() or os.path.dirname(self.selected_files[0])
        lang_code = LANGUAGES[self.dst.get()].replace("-", "").lower()
        for orig_path, subs in self.translated_subs_list:
            name, ext = os.path.splitext(os.path.basename(orig_path))
            save_path = os.path.join(folder, f"{name}.{lang_code}{ext}")
            try:
                pysrt.SubRipFile(subs).save(save_path, encoding="utf-8")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {save_path}\n{e}")
        messagebox.showinfo("Success", f"All files saved to:\n{folder}")
        self.stat.configure(text="All saved!", text_color="#00ff00")

    # =============================================
    # 2. UTF-8 CONVERTER WITH LOG
    # =============================================
    def _utf8_ui(self):
        ctk.CTkLabel(self, text="SRT to UTF-8 Converter", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)
        ff = ctk.CTkFrame(self)
        ff.pack(pady=10, padx=80, fill="x")
        self.files_lbl = ctk.CTkLabel(ff, text="No files selected", text_color="gray")
        self.files_lbl.pack(side="left", padx=20, fill="x", expand=True)
        ctk.CTkButton(ff, text="Select .srt Files", command=self._browse_utf8).pack(side="right", padx=20)

        self.convert_btn = ctk.CTkButton(self, text="Start Conversion", height=50, font=ctk.CTkFont(size=15, weight="bold"), state="disabled", command=self._convert_utf8)
        self.convert_btn.pack(pady=15)

        prog_frame = ctk.CTkFrame(self)
        prog_frame.pack(pady=10, padx=80, fill="x")
        self.utf8_progress_label = ctk.CTkLabel(prog_frame, text="Progress: 0 / 0")
        self.utf8_progress_label.pack(side="left")
        self.utf8_progress = ctk.CTkProgressBar(prog_frame)
        self.utf8_progress.pack(side="right", fill="x", expand=True, padx=(20, 0))
        self.utf8_progress.set(0)

        log_frame = ctk.CTkFrame(self)
        log_frame.pack(pady=(5, 20), padx=80, fill="both", expand=True)
        ctk.CTkLabel(log_frame, text="Conversion Log:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(8, 4))
        self.utf8_log = ctk.CTkTextbox(log_frame, height=180)
        self.utf8_log.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.utf8_log.configure(state="disabled")

    def _browse_utf8(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT Files", "*.srt")])
        if files:
            self.selected_files = list(files)
            self.files_lbl.configure(text=f"{len(files)} files selected")
            self.convert_btn.configure(state="normal")
            self.utf8_progress.set(0)
            self.utf8_progress_label.configure(text="Progress: 0 / 0")
            self._clear_utf8_log()

    def _clear_utf8_log(self):
        self.utf8_log.configure(state="normal")
        self.utf8_log.delete("1.0", "end")
        self.utf8_log.configure(state="disabled")

    def _convert_utf8(self):
        if not self.selected_files: return
        self.convert_btn.configure(state="disabled")
        self._clear_utf8_log()
        Thread(target=self._utf8_worker, daemon=True).start()

    def _utf8_worker(self):
        total = len(self.selected_files)
        success = 0
        for i, file_path in enumerate(self.selected_files):
            name = os.path.basename(file_path)
            self.utf8_queue.put(("log", f"[{i+1}/{total}] {name}\n"))
            try:
                if _USE_NORMALIZER:
                    encoding = from_path(file_path).best().encoding if from_path(file_path).best() else "utf-8"
                else:
                    raw = open(file_path, "rb").read()
                    encoding = chardet.detect(raw)["encoding"] or "utf-8"

                with open(file_path, "r", encoding=encoding, errors="replace") as f:
                    content = f.read()
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    f.write(content)

                success += 1
                self.utf8_queue.put(("log", "   Success\n\n"))
            except Exception as e:
                self.utf8_queue.put(("log", f"   Failed: {str(e)}\n\n"))

            self.utf8_queue.put(("progress", ((i+1)/total, i+1, total)))

        self.utf8_queue.put(("log", f"Complete! {success}/{total} succeeded.\n"))
        self.utf8_queue.put(("done", None))

    # =============================================
    # 3. ENGLISH SUBTITLE EXTRACTOR
    # =============================================
    def _extractor_ui(self):
        ctk.CTkLabel(self, text="Extract English Subtitles from Video", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(20, 15))
        ff = ctk.CTkFrame(self)
        ff.pack(pady=10, padx=80, fill="both", expand=False)
        ctk.CTkLabel(ff, text="Selected Video Files:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(8, 4))
        self.video_listbox = ctk.CTkTextbox(ff, height=100)
        self.video_listbox.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        self.video_listbox.configure(state="disabled")
        btnf = ctk.CTkFrame(ff)
        btnf.pack(fill="x", padx=15, pady=(0, 8))
        ctk.CTkButton(btnf, text="Add Video Files", width=140, command=self._add_videos).pack(side="left", padx=5)
        ctk.CTkButton(btnf, text="Clear All", fg_color="gray", width=100, command=self._clear_videos).pack(side="left", padx=5)

        of = ctk.CTkFrame(self)
        of.pack(pady=12, padx=80, fill="x")
        ctk.CTkLabel(of, text="Output Folder:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=20)
        self.extractor_output_label = ctk.CTkLabel(of, text="Not selected", text_color="gray", anchor="w")
        self.extractor_output_label.pack(side="left", fill="x", expand=True, padx=(10, 20))
        ctk.CTkButton(of, text="Choose Folder", width=140, command=self._choose_extractor_output).pack(side="right", padx=20)

        prog_frame = ctk.CTkFrame(self)
        prog_frame.pack(pady=12, padx=80, fill="x")
        self.extractor_progress_label = ctk.CTkLabel(prog_frame, text="Progress: 0 / 0")
        self.extractor_progress_label.pack(side="left", padx=5)
        self.extractor_progress = ctk.CTkProgressBar(prog_frame)
        self.extractor_progress.pack(side="right", fill="x", expand=True, padx=(20, 5))
        self.extractor_progress.set(0)

        self.extractor_start_btn = ctk.CTkButton(self, text="Start Extraction", height=50, font=ctk.CTkFont(size=16, weight="bold"), fg_color="#1a8754", command=self._start_extraction)
        self.extractor_start_btn.pack(pady=18)

        log_frame = ctk.CTkFrame(self)
        log_frame.pack(pady=(5, 20), padx=80, fill="both", expand=True)
        ctk.CTkLabel(log_frame, text="Log Output:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(8, 4))
        self.extractor_log = ctk.CTkTextbox(log_frame, height=140)
        self.extractor_log.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.extractor_log.configure(state="disabled")

    def _add_videos(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mkv *.mp4 *.avi *.mov *.webm *.ts *.m2ts")])
        if files:
            for f in files:
                if f not in self.video_files:
                    self.video_files.append(f)
            self._refresh_video_list()
            self.extractor_progress_label.configure(text=f"Progress: 0 / {len(self.video_files)}")

    def _clear_videos(self):
        self.video_files.clear()
        self._refresh_video_list()
        self.extractor_progress_label.configure(text="Progress: 0 / 0")

    def _refresh_video_list(self):
        self.video_listbox.configure(state="normal")
        self.video_listbox.delete("1.0", "end")
        for f in self.video_files:
            self.video_listbox.insert("end", os.path.basename(f) + "\n")
        self.video_listbox.configure(state="disabled")

    def _choose_extractor_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.extractor_output_dir = folder
            self.extractor_output_label.configure(text=folder, text_color="#00ff00")

    def _start_extraction(self):
        if not self.video_files or not self.extractor_output_dir:
            messagebox.showwarning("Missing", "Add files and choose output folder first!")
            return
        self.extractor_start_btn.configure(state="disabled")
        self.extractor_log.configure(state="normal")
        self.extractor_log.delete("1.0", "end")
        self.extractor_log.configure(state="disabled")
        Thread(target=self._extractor_worker, daemon=True).start()

    def _extractor_worker(self):
        total = len(self.video_files)
        for i, path in enumerate(self.video_files):
            name = os.path.basename(path)
            self.extractor_queue.put(("log", f"[{i+1}/{total}] {name}\n"))
            streams = find_english_subtitle_streams(path)
            if not streams:
                self.extractor_queue.put(("log", "   No English subtitles found.\n\n"))
            else:
                self.extractor_queue.put(("log", f"   Found {len(streams)} English track(s)\n"))
                for s in streams:
                    idx = s["index"]
                    out_name = f"{os.path.splitext(name)[0]}_eng_{idx}.srt"
                    out_path = os.path.join(self.extractor_output_dir, out_name)
                    self.extractor_queue.put(("log", f"   Extracting → {out_name} ... "))
                    success, _ = extract_subtitle_stream(path, idx, out_path)
                    self.extractor_queue.put(("log", "Success!\n" if success else "Failed!\n"))
                self.extractor_queue.put(("log", "\n"))
            self.extractor_queue.put(("progress", ((i+1)/total, i+1, total)))
        self.extractor_queue.put(("log", "All extraction completed!\n"))
        self.extractor_queue.put(("done", None))

    def _process_queues(self):
        for q, log_widget, prog, prog_label, btn in [
            (self.extractor_queue, getattr(self, "extractor_log", None), getattr(self, "extractor_progress", None), getattr(self, "extractor_progress_label", None), getattr(self, "extractor_start_btn", None)),
            (self.utf8_queue, getattr(self, "utf8_log", None), getattr(self, "utf8_progress", None), getattr(self, "utf8_progress_label", None), getattr(self, "convert_btn", None))
        ]:
            try:
                while True:
                    msg_type, payload = q.get_nowait()
                    if msg_type == "log" and log_widget:
                        log_widget.configure(state="normal")
                        log_widget.insert("end", payload)
                        log_widget.see("end")
                        log_widget.configure(state="disabled")
                    elif msg_type == "progress" and prog:
                        prog.set(payload[0])
                        prog_label.configure(text=f"Progress: {payload[1]} / {payload[2]}")
                    elif msg_type == "done" and btn:
                        btn.configure(state="normal")
            except queue.Empty:
                pass
        self.after(100, self._process_queues)

# =============================================
# Run App
# =============================================
if __name__ == "__main__":
    app = SRTTranslatorApp()
    app.mainloop()