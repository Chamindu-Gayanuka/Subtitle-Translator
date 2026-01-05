# SRT Translator , UTF-8 Converter & English Subtitle Extractor

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-orange)
![License](https://img.shields.io/badge/License-MIT-green)

> **Fast, reliable SRT subtitle translator using Google Translate**  
> **Batch UTF-8 converter for legacy subtitle files**  
> **English subtitle extractor from video files**

---

## Features

| Mode | Description |
|------|-------------|
| **Translate SRT** | Translate `.srt` files using **Google Translate** with smart batching |
| **UTF-8 Converter** | Convert up to **20 legacy `.srt` files** to proper UTF-8 |
| **Smart Batching** | Smaller batches for CJK source text to prevent errors |
| **Preserves Timing** | Original timestamps and structure fully retained |
| **Modern Dark UI** | Built with **CustomTkinter** |
| **Offline UTF-8 Mode** | No internet required for encoding conversion |

> **CJK languages (Chinese, Japanese, Korean, Thai, Vietnamese) are now included in target language selection** and ensure high-quality, reliable translations.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Chamindu-Gayanuka/Subtitle-Translator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python Translator_1.0.3.py
```

### 4. (Optional) Create Executable with PyInstaller
```bash
pip install pyinstaller
```

```bash
pyinstaller --onefile --windowed --icon=icon.ico --name="Subtitles Translator" --add-data "ffmpeg.exe;." --add-data "ffprobe.exe;." --add-data "icon.ico;." --clean --noconfirm Translator_1.0.3.py       
```

---

### Translate SRT
1. Click **"Translate SRT"**
2. Browse and load `.srt` files
3. Select **Source** (use **Auto** for best results) and **Target** language
4. Click **"Translate SRT (Fast)"**
5. Save the translated `.srt` files

### Convert to UTF-8
1. Click **"Convert to UTF-8"**
2. Select up to **20 .srt files**
3. Click **"Convert to UTF-8"**

### Extract English Subtitles
1. Click **"Extract English Subtitles"**
2. Browse and load video files
3. Choose an output folder
4. Click **"Extract English Subtitles"**

---

## Supported Target Languages

| Language  | Code | Language | Code |
|-----------|------|----------|------|
| Arabic    | `ar` | Italian | `it` |
| Czech     | `cs` | Malay | `ms` |
| Danish    | `da` | Norwegian | `no` |
| Dutch     | `nl` | Polish | `pl` |
| English   | `en` | Romanian | `ro` |
| Filipino  | `tl` | Russian | `ru` |
| Finnish   | `fi` | **Sinhala** | `si` |
| Chinese (Simplified) | `zh-CN` | Spanish | `es` |
| Chinese (Traditional) | `zh-TW` | Korean | `ko` |
| Thai | `th` | Japanese | `ja` |
| French    | `fr` | Swedish | `sv` |
| German    | `de` | Turkish | `tr` |
| Greek     | `el` | Ukrainian | `uk` |
| Hungarian | `hu` | Indonesian | `id` |
| Croatian  | `hr` | ... | |

---

## Contributing
We welcome contributions!
1. **Fork** the repo
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License
This project is licensed under the **MIT License**. See the [LICENSE](https://github.com/Chamindu-Gayanuka/Subtitle-Translator/blob/main/LICENSE) file for details.