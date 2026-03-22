# WebFlow — Usage Guide

This guide walks you through every step of using WebFlow to transfer your browser data.

---

## Prerequisites

- **Python 3.11 or newer** installed ([python.org](https://python.org))
- **Both browsers** you want to transfer between installed on the same machine
- **At least one browser closed** during transfer (so its profile files aren't locked)

---

## Step 0 — Installation

```bash
# Navigate to the webflow directory
cd webflow

# (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux / macOS
# venv\Scripts\activate       # Windows (PowerShell)

# Install all dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.111.0 uvicorn-0.29.0 sqlalchemy-2.0.30 ...
```

---

## Step 1 — Launch the app

```bash
python run.py
```

The terminal will show:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8765
```

A **native desktop window** will open automatically — no browser needed.

---

## Step 2 — Create an account

On the welcome screen:
1. Click **"Create account"**
2. Enter a username (letters, numbers, `_` or `-`, 3–32 chars)
3. Enter your email
4. Choose a **strong master password** — this password protects ALL your data with AES encryption

> **Important:** Write your master password down somewhere safe. If you forget it, your encrypted data cannot be recovered (by design — this is a security feature).

---

## Step 3 — Select your source browser

WebFlow automatically scans your system for installed browsers.

| Browser | What it detects |
|---------|----------------|
| Google Chrome | `~/.config/google-chrome` (Linux), `~/Library/Application Support/Google/Chrome` (Mac) |
| Firefox | `~/.mozilla/firefox` (Linux), `~/Library/Application Support/Firefox` (Mac) |
| Opera GX | `~/.config/opera` (Linux), `~/Library/Application Support/com.operasoftware.Opera` (Mac) |
| Microsoft Edge | `~/.config/microsoft-edge` (Linux) |
| Brave | `~/.config/BraveSoftware` (Linux) |

Click the browser card to select it, then choose your profile from the dropdown (most users have just one: "Default").

---

## Step 4 — Choose what to transfer

Select the data types you want to move:

| Type | What gets transferred |
|------|-----------------------|
| 🔖 Bookmarks | All bookmarks, placed in an "Imported by WebFlow" folder |
| 📅 History | URLs, titles, visit counts (last 90 days) |
| 🔑 Passwords | Saved logins — exported as importable CSV |
| 🧩 Extensions | A list with direct install links |
| ⚙️ Settings | Homepage URL, default search engine |

Click **"🔍 Scan browser"** — WebFlow will read your browser data and show counts per category.

> The source browser should be **closed** during this step to avoid database lock errors.

---

## Step 5 — Select your destination browser

Choose the browser you want to transfer data **to**. Select its profile.

WebFlow will warn you if you try to transfer from and to the same browser/profile.

---

## Step 6 — Start the transfer

Click **"🚀 Start transfer"**.

A progress bar will appear for each data type. The transfer runs in the background — you can watch the live status update.

Typical times:
- Bookmarks: < 1 second
- History (1000 entries): ~2 seconds
- Passwords (50 entries): ~1 second
- Extensions list: < 1 second

---

## Step 7 — Post-transfer steps

### Passwords
WebFlow cannot write directly into the browser's encrypted password store (this is a browser security restriction). Instead, it creates a file:

```
[destination profile folder]/webflow_passwords_import.csv
```

To import it:

**Chrome/Edge/Brave:**
1. Go to `chrome://settings/passwords` (or `edge://settings/passwords`)
2. Click the ⋮ menu → **Import passwords**
3. Select the `webflow_passwords_import.csv` file

**Firefox:**
1. Go to `about:logins`
2. Click ⋮ → **Import from a file**
3. Select the `webflow_passwords_import.csv` file

> Delete the CSV file after importing — it contains your passwords in plaintext.

### Extensions
An HTML file is saved to:
```
[destination profile folder]/webflow_extensions.html
```

Open it in the destination browser and click the install links for each extension.

---

## Verifying the transfer

### Bookmarks
1. Open the destination browser
2. Open the bookmarks manager
3. Look for the **"Imported by WebFlow"** folder

### History
1. Open the destination browser
2. Press `Ctrl+H` (or `Cmd+Y` on Mac) to open history
3. Imported entries will appear alongside existing history

### Settings
1. Open the destination browser's settings
2. Verify the homepage and search engine

---

## Troubleshooting

### "Profile path does not exist"
The browser's profile directory wasn't found. Make sure the browser is installed and has been opened at least once.

### "Browser locked" / SQLite errors
Close the source browser before scanning. Chrome, Firefox etc. lock their database files while running.

### Passwords show `<NSS unavailable>`
Firefox stores passwords using NSS (Network Security Services). If `libnss3` isn't found on your system:
1. Install Firefox (the NSS library is bundled with it)
2. Or manually export passwords: Firefox → Settings → Privacy & Security → Saved Logins → ⋮ → Export Logins

### Chrome passwords show `<encrypted — key unavailable>` on Linux
Install `python3-secretstorage`:
```bash
pip install secretstorage
```
Then restart WebFlow and retry.

### Rate limit error on login
You've hit the 5-attempts-per-minute limit. Wait 60 seconds and try again.

---

## Security checklist

Before using WebFlow on sensitive data:

- [ ] You're running it on your own machine (not a shared computer)
- [ ] You've chosen a strong master password
- [ ] You'll delete the password CSV after importing it into the browser
- [ ] You'll delete `webflow.db` when you no longer need the stored snapshots
- [ ] The app runs entirely on your machine (not accessible from any other device)

---

## Uninstalling / cleaning up

```bash
# Close the WebFlow window, or press Ctrl+C in the terminal if running from source

# Remove the encrypted database
rm webflow.db

# Remove the password CSV files from your profile folder
rm ~/.config/[browser]/Default/webflow_passwords_import.csv

# Remove the extensions HTML
rm ~/.config/[browser]/Default/webflow_extensions.html

# Deactivate and remove the venv
deactivate
rm -rf venv
```

---

## Security architecture (for the curious)

```
Registration:
  1. Generate 32 random bytes → salt (stored in DB as hex)
  2. Hash password with bcrypt (cost=12) → stored in DB

Login:
  1. Verify bcrypt hash
  2. PBKDF2-HMAC-SHA256(password, salt, 480000 iterations) → 32-byte key
  3. Wrap in Fernet → stored in RAM as {JWT_jti: Fernet}
  4. Return JWT (30-min expiry, signed with server SECRET_KEY)

Data storage:
  - Fernet.encrypt(json.dumps(browser_data)) → stored in DB
  - To decrypt: Fernet.decrypt(blob) → only possible with the in-memory key

Browser password decryption flow:
  Chrome (Linux):  libsecret → PBKDF2("saltysalt", 1 iter) → AES-CBC key → decrypt
  Chrome (macOS):  Keychain "Chrome Safe Storage" → PBKDF2 → AES-CBC key → decrypt
  Chrome (Win):    DPAPI unwrap → AES-GCM key → decrypt
  Firefox:         NSS_Init(profile) → PK11SDR_Decrypt(encrypted_value)
```

---

*For support or to report a security issue, open a GitHub issue.*
