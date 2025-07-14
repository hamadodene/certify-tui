# Certify TUI

**Certify TUI** is a terminal-based interactive tool for generating Certificate Signing Requests (CSRs) and converting certificate formats — built using [Textual](https://github.com/Textualize/textual).

<img width="1666" height="886" alt="image" src="https://github.com/user-attachments/assets/d0bbaa1a-6e27-46d1-b19e-69572d562820" />

<img width="1648" height="878" alt="image" src="https://github.com/user-attachments/assets/424ebfe0-fe2c-439c-aed9-7f84685009c7" />

---

## Features

- ✅ Generate CSR with passwordless or password-protected private keys
- ✅ Add/remove SANs interactively
- ✅ Live OpenSSL config preview
- ✅ Convert between formats:
  - `.cer + .key → .p12`
  - `.p12 → .cer + .key`
  - `.cer → .pem`
  - `.p12 → .pem`
  - `.pem + .key → .p12`

---

## Installation

### Option 1. Clone the repository

```bash
git clone https://github.com/<your-username>/certify-tui.git
cd certify-tui
pip install .
```
This installs certify-tui as a command-line tool. You can now launch it using:
```bash
certify-tui --workdir /path/to/output
```

### Option 2: Install directly via GitHub (no clone required)

```bash
pip install git+https://github.com/hamadodene/certify-tui.git
certify-tui --workdir /path/to/output
```

### Keyboard Controls

- `TAB` / `SHIFT+TAB`: Navigate between fields
- `ENTER`: Submit a SAN entry
- `Q`: Quit the application

> **Note:** If you're using PuTTY or SSH, use **right-click** to paste (instead of `Ctrl+V`).

---

## Usage
```bash
certify-tui --workdir /path/to/output
```
> **Note:** If --workdir is omitted, files will be saved in the current directory.

---
## Interface Overview

### CSR Tab
- Fill in certificate details (CN, O, OU, etc.)
- Add multiple SANs
- Preview OpenSSL config
- Generate `.csr` and `.key` files

### Conversions Tab
- Choose a conversion type from the dropdown
- Provide input/output file paths
- Optionally add a password
- View conversion logs below the form

---

## Requirements

- Python 3.9+
- `openssl` installed and available in `$PATH`
- Linux/macOS or terminal emulator with UTF-8 support

---

## requirements.txt

See below for the contents of `requirements.txt`.

---

## License

MIT License — free to use, modify, and distribute.

---
