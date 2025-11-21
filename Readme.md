# SRT Translator & UTF-8 Converter

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-orange)
![License](https://img.shields.io/badge/License-MIT-green)

> **Fast, reliable SRT subtitle translator using Google Translate**  
> **Batch UTF-8 converter for legacy subtitle files**  
> **CJK languages excluded from target for better accuracy**

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

> **CJK languages (Chinese, Japanese, Korean, Thai, Vietnamese) are excluded from target language selection** to ensure high-quality, reliable translations.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/srt-translator-utf8.git
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python Translator_1.0.1.py
```

---

### Translate SRT
1. Click **"Translate SRT"**
2. Browse and load a `.srt` file
3. Select **Source** (use **Auto** for best results) and **Target** language
4. Click **"Translate SRT (Fast)"**
5. Save the translated `.srt` file

### Convert to UTF-8
1. Click **"Convert to UTF-8"**
2. Select up to **20 .srt files**
3. Choose an output folder
4. Click **"Convert to UTF-8"**

---

## Supported Target Languages

| Language | Code | Language | Code |
|--------|------|----------|------|
| Arabic | `ar` | Italian | `it` |
| Czech | `cs` | Malay | `ms` |
| Danish | `da` | Norwegian | `no` |
| Dutch | `nl` | Polish | `pl` |
| English | `en` | Romanian | `ro` |
| Filipino | `tl` | Russian | `ru` |
| Finnish | `fi` | **Sinhala** | `si` |
| French | `fr` | Swedish | `sv` |
| German | `de` | Turkish | `tr` |
| Greek | `el` | Ukrainian | `uk` |
| Hungarian | `hu` | Indonesian | `id` |
| Croatian | `hr` | ... | |

---

## Contributing
We welcome contributions!
1. **Fork** the repo
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License
This project is licensed under the **MIT License**. See the [LICENSE](https://github.com/Chamindu-Gayanuka/Subtitle-Translator/blob/main/LICENSE) file for details.