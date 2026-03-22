# 🌊 WebFlow — Browser Data Transfer Tool

> Transfer your bookmarks, history, passwords, and extensions from one browser to another — locally, privately, and securely.

---

> ### ⚠️ Antivirus / SmartScreen warning — read this first
>
> When you download and run WebFlow, **Windows Defender, SmartScreen, or your antivirus may flag it.
> This is a false positive and completely normal** — here's why:
>
> - WebFlow needs to **read your browser profile folders** (bookmarks, history, passwords).
>   Antivirus software is designed to be suspicious of any app that does this.
> - The `.exe` is **unsigned** — I don't yet have a paid code-signing certificate (~150€/year).
>   Windows automatically warns about unsigned executables from unknown publishers.
> - WebFlow contains **no malware, spyware, or trackers** — the full source code is right here in this repo, open for anyone to inspect.
>
> **How to run it anyway:**
> - **Windows SmartScreen** → click "More info" → "Run anyway"
> - **Windows Defender popup** → click "Show more" → "Run anyway"
> - **Antivirus quarantine** → add an exception for the `WebFlow.exe` file
>
> If you're not comfortable, you can always **run from source** instead (see below) — same code, no binary trust required.

---

## Download & Run (no setup needed)

**Windows:**

1. Go to the **[Releases](../../releases/latest)** page of this repo
2. Download **`WebFlow.exe`**
3. If Windows SmartScreen appears → click **"More info" → "Run anyway"**
4. A **native app window opens instantly**

No browser. No terminal. No Python. No pip.

---

## What is WebFlow?

WebFlow is a **native desktop app** that lets you migrate your browser data between different browsers — similar to how TuneMyMusic transfers playlists between music services, but for browsers. It runs entirely on your machine with no internet connection required.

**Supported browsers:** Google Chrome · Mozilla Firefox · Opera GX · Microsoft Edge · Brave

**Data you can transfer:**
| Data Type | Status | Notes |
|-----------|--------|-------|
| 🔖 Bookmarks | ✅ Fully automated | Folder structure preserved |
| 📅 History | ✅ Fully automated | Last 90 days by default |
| 🔑 Passwords | ✅ Exported as importable CSV | See password note below |
| 🧩 Extensions | ✅ List with reinstall links | Manual 1-click reinstall |
| ⚙️ Settings | ✅ Homepage, search engine | Basic settings |
| 🍪 Cookies | ❌ Not transferred | Security risk |
| 💳 Payment methods | ❌ Not transferred | OS-level restriction |

---

## Security Model

WebFlow was designed with security as the top priority.

```
Your password
     │
     ▼
PBKDF2-SHA256 (480,000 iterations)  ← OWASP 2023 minimum
     │
     ▼
Fernet key (AES-128-CBC + HMAC-SHA256)  ← lives in RAM only
     │                                      never written to disk
     ▼
Encrypted blob in SQLite  ← you see: "gAAAAA..." not plaintext
```

**What this means:**
- Your **master password** is never stored — only a bcrypt hash (cost=12)
- Your **encryption key** is derived from your password at login and stays in RAM — lost on server restart (you just log in again)
- All browser data (bookmarks, history, passwords) is **Fernet-encrypted** before being saved to SQLite
- If someone steals the `webflow.db` file, they see **only encrypted blobs** — useless without your password
- The app runs **entirely on your machine** — no data ever leaves your machine
- JWT tokens stored in `sessionStorage` (cleared when you close the tab) — never `localStorage`
- Rate limiting: 5 login attempts/min, 3 registrations/hour per IP
- Security headers on every response: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, CSP
- All SQL via ORM — no raw queries, no SQL injection possible
- Input validation via Pydantic on all API endpoints

**Password note:** Browser passwords are OS-encrypted at rest (Chrome uses DPAPI/Keychain/libsecret). WebFlow decrypts them in memory, re-encrypts with your Fernet key, then exports an importable CSV to your target browser's profile folder. You then import it via the browser's built-in password manager.

---

## Run from source (developers)

If you want to run the code directly or contribute:

### Requirements
- Python 3.11+
- Browsers installed on the same machine

### Steps

```bash
# 1. Clone the repo
cd /path/to/webflow

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
python run.py
# A native desktop window opens automatically
```

### Build the exe yourself

```bash
pip install pyinstaller
pyinstaller webflow.spec
# Output: dist/WebFlow.exe
```

---

## Quick Start

1. **Create an account** — choose a strong master password (it protects all your data)
2. **Select source browser** — WebFlow auto-detects installed browsers
3. **Choose what to transfer** — click "Scan browser" to count items
4. **Select destination browser**
5. **Start transfer** — watch the animated progress per category
6. **Done** — download a report, check the password CSV and extension HTML files

---

## Project Structure

```
webflow/
├── run.py                  # Entry point
├── requirements.txt
├── app/
│   ├── main.py             # FastAPI app + middleware
│   ├── config.py           # Settings (PBKDF2 iterations, etc.)
│   ├── database.py         # SQLAlchemy async engine
│   ├── models.py           # ORM models (User, Snapshot, EncryptedData, Job)
│   ├── schemas.py          # Pydantic validation schemas
│   ├── security.py         # Key derivation, Fernet encrypt/decrypt, JWT
│   ├── session_store.py    # In-memory {jti → Fernet} store
│   ├── routers/
│   │   ├── auth.py         # /api/auth/*
│   │   ├── browsers.py     # /api/browsers/*
│   │   └── transfer.py     # /api/transfer/*
│   └── browsers/
│       ├── base.py         # Abstract extractor/importer
│       ├── chrome.py       # Chrome, Edge, Brave
│       ├── firefox.py      # Firefox
│       └── opera_gx.py     # Opera GX
├── static/
│   ├── css/style.css       # Glassmorphism dark UI
│   └── js/app.js           # SPA wizard logic
├── templates/
│   └── index.html          # 6-step wizard
├── README.md               # This file
└── GUIDE.md                # Detailed usage guide
```

---

## API Reference

The API is self-documented at `http://127.0.0.1:8765/api/docs` (Swagger UI) when running from source.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login, get JWT |
| POST | /api/auth/logout | Clear session |
| GET  | /api/auth/me | Current user info |
| GET  | /api/browsers/detect | Detect installed browsers |
| POST | /api/browsers/snapshot | Scan & encrypt browser data |
| GET  | /api/browsers/snapshots | List saved snapshots |
| POST | /api/transfer/start | Start a transfer job |
| GET  | /api/transfer/status/{id} | Poll transfer status |
| GET  | /api/transfer/jobs | List past transfers |
| GET  | /api/health | Server health check |

---

## Verifying Security

### Check encrypted DB
```bash
sqlite3 webflow.db "SELECT data_type, substr(encrypted_blob,1,40) FROM encrypted_data LIMIT 5;"
# bookmarks|gAAAAAB... (Fernet token, not plaintext)
```

### Check security headers
```bash
curl -I http://127.0.0.1:8765
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: default-src 'self'; ...
```

### Check rate limiting
```bash
for i in $(seq 1 8); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8765/api/auth/login \
    -H "Content-Type: application/json" -d '{"username":"x","password":"y"}'
done
# 401 401 401 401 401 429 429 429  (rate limited after 5 attempts)
```

---

## Platform Notes

### Linux
Password extraction requires `libsecret` / GNOME Keyring. Install `python3-secretstorage` if needed.

### macOS
Chrome Safe Storage key is fetched from Keychain. You may see a system permission dialog.

### Windows
Passwords are decrypted using DPAPI via `pywin32`. Install it with: `pip install pywin32`

---

## FAQ

**Q: Does WebFlow send my data anywhere?**
A: No. The app runs entirely on your machine. Nothing leaves your device.

**Q: What if I restart the server?**
A: Your encrypted data stays in the DB. You just log in again to re-derive the key.

**Q: Can I transfer between browsers on different machines?**
A: Not directly — WebFlow is a local tool. For cross-machine transfer, copy the profile folder manually.

**Q: Why can't passwords be imported automatically?**
A: Modern browsers require passwords to be re-encrypted with the OS keychain on write. The exported CSV can be imported in 2 clicks via the browser's password settings.

**Q: Is the `webflow.db` file safe to back up?**
A: Yes — all sensitive data is Fernet-encrypted. Without your master password, the blobs are unreadable.

---

*WebFlow runs entirely on your machine. Your data stays yours.*
