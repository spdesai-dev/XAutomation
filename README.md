# XAutomation 🤖

A web-based automation tool that sends personalized Direct Messages (DMs) on X (Twitter) to users from an uploaded spreadsheet. It supports both manual template-based messages and AI-generated personalized messages powered by OpenRouter.

---

## 📁 Project Structure

```
XAutomation/
├── server.py           # Flask web server — handles UI, file uploads, API endpoints
├── worker.py           # Background subprocess — runs generate/send phases
├── bot.py              # Playwright browser automation — opens DMs, types messages
├── spreadsheet.py      # Reads/writes CSV and XLSX user data files
├── ai_generator.py     # Calls OpenRouter API to generate personalized DMs
├── config.py           # Constants: delay timings, selectors, API settings
├── main.py             # Legacy CLI entry point
├── static/
│   ├── app.js          # Frontend JavaScript — UI logic, polling, approvals
│   └── style.css       # UI Styling
├── templates/
│   └── index.html      # Main web dashboard HTML
├── uploads/            # Uploaded spreadsheet files (auto-created)
├── user_data/          # Playwright persistent browser session (login state)
├── requirements.txt    # Python dependencies
├── XAutomation.bat     # One-click launcher for Windows
└── PRD.md              # Original Product Requirements Document
```

---

## 🚀 How to Run

### First Time Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install browser (one time)
playwright install chrome
```

### Start the App
Double-click **`XAutomation.bat`** — this starts the Flask server and opens the browser.

Or manually:
```bash
python server.py
```
Then visit: **http://localhost:5000**

---

## 📋 Spreadsheet Format

Upload a `.csv` or `.xlsx` file with these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `username` | ✅ | X/Twitter handle (without @) |
| `profile_url` | ✅ | Direct URL to profile (fallback) |
| `post_url` | ✅ | Link to the tweet being referenced |
| `post_content` | ✅ | Text of the tweet (used in message) |

After processing, the sheet gains:
- `status` — `pending` / `pending_approval` / `approved` / `sent` / `failed`
- `reply` — `none` / `replied`
- `generated_message` — the AI-generated or approved message text

---

## 🔄 Detailed Workflow (with Function & Route Names)

### Phase 0: Startup
```
XAutomation.bat
  └─► python server.py
        └─► Flask app starts on localhost:5000
        └─► GET / → index() → renders templates/index.html
        └─► app.js loads in browser → DOMContentLoaded → sets up all event listeners
```

---

### Phase 1: Upload Spreadsheet
```
User: drops/selects a .csv or .xlsx file
  └─► app.js: handleFileUpload(file)
        └─► fetch POST /upload
              └─► server.py: upload_file()
                    └─► spreadsheet.py: SpreadsheetManager.__init__()
                          └─► SpreadsheetManager._load_data()       ← reads CSV/XLSX
                          └─► SpreadsheetManager._validate_columns() ← checks required cols
                          └─► SpreadsheetManager._initialize_tracking_columns()
                                └─► adds status, reply, generated_message cols
                                └─► SpreadsheetManager.save()       ← writes back to file
                    └─► server.py: update_stats(sm)                 ← updates dashboard counters
              └─► returns { success, stats }
        └─► app.js: showUploadFeedback() + updateStatsUI()
```

---

### Phase 2A: Generate AI Messages (AI Mode)
```
User: toggles AI ON → enters OpenRouter API Key → clicks "Generate Messages"
  └─► app.js: btnGenerate click handler
        └─► reads aiApiKey.value, aiModel.value (also saved to localStorage)
        └─► fetch POST /generate  { message_template, use_ai: true, openrouter_api_key, openrouter_model }
              └─► server.py: generate_messages()
                    └─► validates: file exists, AI is ON, not already running
                    └─► subprocess.Popen(worker.py ... --use-ai --generate-only)
                    └─► threading.Thread(_read_process_output) ← streams logs to UI
              └─► Worker subprocess (worker.py) starts:
                    └─► worker.py: main()
                          └─► argparse: parses --generate-only flag
                          └─► spreadsheet.py: SpreadsheetManager(file_path)
                          └─► sm.get_pending_users()            ← yields rows with status='pending'
                          └─► FOR EACH pending user:
                                └─► ai_generator.generate_dm(post_content, username, api_key, model)
                                      └─► builds SYSTEM_PROMPT + user_prompt
                                      └─► if feedback provided: appends to user_prompt
                                      └─► requests.post("https://openrouter.ai/api/v1/chat/completions")
                                      └─► on error/timeout: _apply_fallback(template, post_content)
                                └─► sm.update_user_status(index, status='pending_approval', generated_message=message)
                                      └─► SpreadsheetManager.save()  ← writes to file immediately
```

---

### Phase 2B: Review & Approve Messages (Approvals Tab)
```
User: clicks "Approvals" in sidebar
  └─► app.js: navApprovals click → pollApprovals()
        └─► fetch GET /api/approvals
              └─► server.py: get_approvals()
                    └─► spreadsheet.py: sm.get_pending_approvals()
                          └─► returns rows where status IN ['pending_approval', 'approved', 'sent', 'failed']
              └─► returns { approvals: [...] }
        └─► app.js: renderApprovals(approvals)
              └─► DOM diff: compares currentSignature vs newSignature (id:status pairs)
              └─► renders approval cards with status-aware actions

User: edits message text in card textarea
User: clicks "Approve" button
  └─► app.js: handleApprove(idx)
        └─► reads textarea value (edited message)
        └─► fetch POST /api/approve  { index, message }
              └─► server.py: approve_message()
                    └─► sm.update_user_status(index, status='approved', generated_message=message)
                    └─► update_stats(sm)
              └─► returns { success: true }
        └─► app.js: immediately updates card DOM to show ✅ Approved badge
              └─► card.dataset.status = 'approved'
              └─► replaces action buttons with Approved indicator
              └─► disables the message textarea

User: clicks "Disapprove" → provides feedback → clicks "Regenerate"
  └─► app.js: handleRegenerate(idx)
        └─► reads feedbackInput.value
        └─► fetch POST /api/disapprove  { index, feedback, api_key, model, fallback_template }
              └─► server.py: disapprove_message()
                    └─► sm.data[index] → gets username, post_content
                    └─► ai_generator.generate_dm(..., feedback=feedback)
                    └─► sm.update_user_status(index, status='pending_approval', generated_message=new_message)
              └─► returns { success, new_message }
        └─► app.js: updates textarea with new_message
```

---

### Phase 3: Send Approved Messages
```
User: clicks "Start Sending"
  └─► app.js: btnStart click handler
        └─► fetch POST /start  { message_template, use_ai: true, openrouter_api_key, openrouter_model }
              └─► server.py: start_automation()
                    └─► validates: not already running, file exists
                    └─► subprocess.Popen(worker.py ... --use-ai --send-only)
                    └─► threading.Thread(_read_process_output) ← streams logs to UI

Worker subprocess (worker.py) — SEND-ONLY mode:
  └─► worker.py: main()
        └─► argparse: parses --send-only flag
        └─► SpreadsheetManager(file_path)
        └─► sm.get_approved_users()           ← yields rows with status='approved'
        └─► FOR EACH approved user:
              └─► reads user_data['generated_message']  ← the approved text
              └─► user_data['message_template'] = generated_message
              └─► bot.py: bot.process_user(user_data)
                    ┌──────────────────────────────────────────────────────────┐
                    │  XAutomationBot.process_user(user_data)                  │
                    │                                                          │
                    │  1. _open_dm_via_messages_tab(username)                  │
                    │       └─► page.goto("https://x.com/messages")            │
                    │       └─► locator('[data-testid=dm-new-chat-button]')    │
                    │       └─► locator('input[placeholder=Search...]').type() │
                    │       └─► _select_user_from_dropdown(username)           │
                    │             └─► wait_for_selector('[data-testid=         │
                    │                  TypeaheadUser]')                        │
                    │             └─► find item containing @username → .click()│
                    │       └─► locator('[data-testid=nextButton]') → .click() │
                    │       └─► wait_for_selector('div[data-testid=            │
                    │            dmComposerTextInput]')  → return True         │
                    │                                                          │
                    │  2. Fallback: _open_dm_via_profile(username, profile_url)│
                    │       └─► page.goto(profile_url)                         │
                    │       └─► locator('[data-testid=sendDMFromProfile]')     │
                    │       └─► wait for dmComposerTextInput                   │
                    │                                                          │
                    │  3. _detect_reply()                                      │
                    │       └─► locator('[data-testid=messageEntry]').all()    │
                    │       └─► returns 'replied' or 'none'                    │
                    │                                                          │
                    │  4. _generate_message(template, post_content, post_url)  │
                    │       └─► replaces {post_content}, {post_url} in text    │
                    │                                                          │
                    │  5. _send_dm(message)                                    │
                    │       └─► locator('div[data-testid=dmComposerTextInput]')│
                    │            → .click()   ← focuses inner contenteditable  │
                    │       └─► keyboard.press("Control+a") + "Delete"         │
                    │       └─► keyboard.type(line, delay=30) per line          │
                    │       └─► Shift+Return between lines                     │
                    │       └─► locator('[data-testid=dmComposerSendButton]')  │
                    │            → .click()                                    │
                    │       └─► fallback: keyboard.press("Enter")              │
                    │                                                          │
                    │  Returns { status: 'sent'|'failed', reply: 'none'|...}  │
                    └──────────────────────────────────────────────────────────┘
              └─► sm.update_user_status(index, status=result['status'], reply=result['reply'])
              └─► time.sleep(config.MESSAGE_DELAY_SECONDS)  ← 600s = 10 min
```

---

### Phase 4: Live Status Polling (continuous during any phase)
```
app.js: setInterval(pollStatus, 3000)  ← every 3 seconds
  └─► fetch GET /status
        └─► server.py: get_status()
              └─► returns { is_running, logs: [...], stats: {total, pending, sent, failed} }
        └─► app.js: updateStatusUI(is_running)
        └─► app.js: updateStatsUI(stats)
        └─► app.js: updateLogsUI(logs)  ← appends new log lines to the terminal
  └─► if Approvals tab is open: pollApprovals() also runs
```

---

### Phase 5: Stop Automation
```
User: clicks "Stop"
  └─► app.js: btnStop click handler
        └─► fetch POST /stop
              └─► server.py: stop_automation()
                    └─► taskkill /F /T /PID automation_process.pid  (Windows)
                    └─► is_running = False
```



---

## 🤖 Bot Behavior (bot.py)

### DM Navigation Flow
1. Navigate to `https://x.com/messages`
2. Click the **New Message** (compose) button
3. Search for the target username in the search box
4. Wait for dropdown results, find and click the matching handle
5. Click the **Next** button to open the composed chat
6. Wait for the DM composer to load (up to 6s)
7. **Fallback:** If step 6 fails → visit the profile URL directly and click the "Message" button

### Message Typing
- Clicks on `div[data-testid='dmComposerTextInput']` to focus the composer
- Types character-by-character using `keyboard.type(text, delay=30)` 
  - Required for Twitter's React/Draft.js editor to register each keystroke
- Multi-line messages use `Shift+Enter` for line breaks
- Finds the send button via `[data-testid='dmComposerSendButton']` or falls back to pressing `Enter`

---

## 🧰 Key API Endpoints (server.py)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web dashboard |
| `/upload` | POST | Upload spreadsheet file |
| `/generate` | POST | Start AI message generation (worker subprocess) |
| `/start` | POST | Start sending approved messages (worker subprocess) |
| `/stop` | POST | Stop any running worker |
| `/status` | GET | Poll running status + logs + stats |
| `/api/approvals` | GET | Get all pending/approved/sent messages for review tab |
| `/api/approve` | POST | Approve a message for sending |
| `/api/regenerate` | POST | Re-generate a specific message with feedback |

---

## ⚙️ Configuration (config.py)

```python
MESSAGE_DELAY_SECONDS = 600   # 10 minutes between messages
OPENROUTER_API_KEY = ""       # Set in UI (saved to browser localStorage)
OPENROUTER_MODEL = "openai/gpt-4o-mini"
TWITTER_BASE_URL = "https://x.com"
```

---

## 🛠 Known Issues & Fixes Applied

| Issue | Fix Applied |
|-------|-------------|
| Browser caching old JS/HTML | Disabled Flask cache headers (`Cache-Control: no-cache`) |
| Old Python processes blocking port 5000 | Kill with `taskkill /f /im python.exe` before restarting |
| Messages tab search → URL fallback | Added longer waits (2-2.5s) after selecting user from dropdown; tries multiple Next button selectors |
| DM textbox not typed into | Click the `dmComposerTextInput` wrapper first, then `keyboard.type(text, delay=30)` |
| Approved messages disappearing | Frontend DOM diff now compares `id:status` pairs, not just IDs |
| API key lost on restart | OpenRouter key + model + AI toggle stored in `localStorage` |
| Approvals tab shows 0 after approve | `handleApprove` now directly updates the DOM badge; `get_pending_approvals()` also returns `approved`, `sent`, `failed` rows |

---

## 📦 Dependencies

```
playwright     # Browser automation
flask          # Web server
openpyxl       # Excel file support
loguru         # Logging
requests       # HTTP calls (OpenRouter API)
```

---

## 🪟 Windows Launcher

**`XAutomation.bat`** activates the virtual environment and starts the Flask server:
```batch
cd /d C:\XAutomation
call venv\Scripts\activate
python server.py
```

---

## 📝 Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not yet processed |
| `pending_approval` | AI message generated, waiting for human review |
| `approved` | Message approved by user, ready to send |
| `sent` | DM successfully sent |
| `failed` | Could not send (user doesn't accept DMs, invalid profile, etc.) |
