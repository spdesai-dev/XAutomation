# XAutomation - Product Requirements Document (PRD)

## 1. Product Purpose
XAutomation automates sending Twitter/X direct messages to users listed in an uploaded spreadsheet.
The system processes each row sequentially and performs the following actions:
- Searches the username manually in the Twitter search bar.
- Opens the correct profile.
- Sends a DM referencing the tweet/post provided in the spreadsheet.
- Sends only one message every 10 minutes.
- Marks when a message is sent.
- Detects and marks when a reply is received.
- If the username search fails or produces ambiguous results, the system opens the profile using the profile URL provided in the spreadsheet.

## 2. Core Functional Requirements
- Upload spreadsheet
- Read usernames and associated post data
- Search usernames manually using the Twitter search bar
- If search fails → open profile using `profile_url`
- Generate DM based on the uploaded post
- Send DM message
- Wait 10 minutes between messages
- Track message status
- Detect replies

## 3. Spreadsheet Module
**Supported Formats:** CSV, XLSX

**Required Columns:**
| Column | Description |
| :--- | :--- |
| `username` | Twitter/X username |
| `profile_url` | Direct link to Twitter profile |
| `post_url` | Link to the tweet/post |
| `post_content` | Text content of the tweet |

**Processing Steps:** Upload → Parse file → Extract fields → Create queue

## 4. Message Generation Logic
Messages must reference the post provided in the spreadsheet (`post_content` or `post_url` if content is unavailable).

**Structure:** Greeting → Reference to tweet/post → Short reaction → Connection message

## 5 & 6. Search & Fallback Behavior
1. **Manual Search First:** Click Twitter search bar → Type username → Wait for results → Check exact exact match → Open profile.
2. **Fallback:** If manual search fails or is ambiguous, open profile using `profile_url` (e.g., `https://twitter.com/username`).

## 7. DM Sending Process
Click Message button → Insert generated message → Click Send

## 8. Execution Rules & Delays
- **10-minute delay** between messages. Automation pauses until the next scheduled send time.

## 9 & 10. Tracking & Reply Detection
- **Message Status:** `pending`, `sent`, `failed`
- **Reply Status:** `none`, `replied` (Detects if the most recent message in the DM conversation is from the recipient).

## 11. Execution Loop
```
FOR each row in spreadsheet
   attempt username search
   IF profile found
      open profile
   ELSE
      open profile_url
   generate message based on post_content
   send DM
   mark status = sent
   wait 10 minutes
repeat
```

## 12. Exception Handling (Problems)
- **Cannot Receive DMs:** Mark `status = failed`, skip user.
- **Invalid Profile URL:** Mark `status = failed`, `reason = invalid_profile`.
- **Missing Post Content:** Use `post_url` instead.
- **Twitter Rate Limits:** Automation stops (captchas, locks, restrictions).
- **UI Changes / Network Issues:** Selectors might break, or connection drops.

## 13. Constraints
- Manual search first, fallback to URL.
- One message every 10 mins.
- Message MUST reference the uploaded post.
- Only process users in the spreadsheet.
- Track status and replies limit.

## 14. Expected Output
Updated spreadsheet with results: `username`, `profile_url`, `status`, `reply`.
