"""
bot.py — XAutomation Browser Bot
DM Flow:
  1. Open x.com/messages
  2. Click the Compose / New Message button
  3. Type the username in the "Search name or username" input
  4. Wait for dropdown results
     a. If found → click the user → click Next → type message → click Send
     b. If NOT found → navigate to x.com/<username> → click Message button
        → type message → click Send
"""
import time
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

import config


class XAutomationBot:
    def __init__(self, headless: bool = False, user_data_dir: str = "./user_data"):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.playwright = None
        self.browser_context = None
        self.page = None

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def start(self):
        """Initializes playwright and launches the persistent browser context."""
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()

        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            slow_mo=50,
        )

        if self.browser_context.pages:
            self.page = self.browser_context.pages[0]
        else:
            self.page = self.browser_context.new_page()

        logger.add("xautomation.log", rotation="1 MB", encoding="utf-8")
        logger.info("Navigating to X (Twitter)...")
        try:
            self.page.goto(config.TWITTER_BASE_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"Initial navigation warning (non-fatal): {e}")

        # Confirm we are logged in
        try:
            self.page.wait_for_selector("[aria-label='Home timeline']", timeout=12000)
            logger.info("Confirmed: logged in.")
        except PlaywrightTimeoutError:
            logger.warning("=" * 55)
            logger.warning("NOT LOGGED IN — Please log in inside the browser window.")
            logger.warning("Waiting up to 90 seconds for manual login...")
            logger.warning("=" * 55)
            try:
                self.page.wait_for_selector("[aria-label='Home timeline']", timeout=90000)
                logger.info("Logged in after manual intervention.")
            except PlaywrightTimeoutError:
                logger.error("Login timeout. Continuing anyway — DMs may fail.")

    def stop(self):
        """Closes the browser and stops playwright."""
        logger.info("Closing browser...")
        try:
            if self.browser_context:
                self.browser_context.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    def process_user(self, user_data: dict) -> dict:
        """
        Sends a DM to one user.
        Returns {'status': 'sent'|'failed', 'reply': 'replied'|'none'}.
        """
        username = user_data.get("username", "").strip().lstrip("@")
        profile_url = user_data.get("profile_url", "").strip()
        post_content = user_data.get("post_content", "")
        post_url = user_data.get("post_url", "")
        message_template = user_data.get("message_template", "Hi,\n\nWould love to connect.")

        if not username:
            logger.error("Missing username — skipping this row.")
            return {"status": "failed", "reply": "none"}

        logger.info(f"--- Processing @{username} ---")
        import json
        dm_msg_text = message_template
        comment_msg_text = message_template
        try:
            parsed = json.loads(message_template)
            if isinstance(parsed, list) and len(parsed) >= 2:
                dm_msg_text = parsed[0]
                comment_msg_text = parsed[1]
            elif isinstance(parsed, list) and len(parsed) == 1:
                dm_msg_text = parsed[0]
                comment_msg_text = parsed[0]
        except Exception:
            pass

        dm_message = self._build_message(dm_msg_text, post_content, post_url)
        comment_message = self._build_message(comment_msg_text, post_content, "")

        reply_status = "none"
        dm_opened = False

        # ── Step 1: Try the Messages compose flow ─────────────────────────────
        logger.info(f"Step 1: Opening Messages tab to DM @{username}...")
        dm_opened = self._open_dm_via_messages_compose(username)

        # ── Step 2: Fallback — visit profile URL / x.com/<username> ──────────
        if not dm_opened:
            logger.warning(f"@{username} not found via compose search. Trying profile page...")
            dm_opened = self._open_dm_via_profile(username, profile_url)

        if not dm_opened:
            logger.warning(f"Could not open DM for @{username}. Attempting fallback: Find post on profile and comment.")
            comment_sent = self._comment_on_post(username, post_content, comment_message)
            if comment_sent:
                logger.info(f"DONE: Commented on post for @{username}")
                return {"status": "commented", "reply": "none"}
            else:
                logger.error(f"FAIL: Could not comment on post for @{username}.")
                return {"status": "failed", "reply": "none"}

        # ── Step 3: Check prior replies ───────────────────────────────────────
        reply_status = self._detect_reply()

        # ── Step 4: Type and send the message ─────────────────────────────────
        logger.info(f"Step 4: Sending message to @{username}...")
        dm_sent = self._send_dm(dm_message)

        if dm_sent:
            logger.info(f"DONE: Message sent to @{username}")
            return {"status": "sent", "reply": reply_status}
        else:
            logger.error(f"FAIL: Failed to send DM to @{username}.")
            return {"status": "failed", "reply": reply_status}

    # ─────────────────────────────────────────────────────────────────────────
    # Comment Fallback
    # ─────────────────────────────────────────────────────────────────────────

    def _comment_on_post(self, username: str, post_content: str, message: str) -> bool:
        """
        Navigates to the user's profile, finds a matching post, and leaves a comment.
        """
        try:
            profile_url = f"https://x.com/{username}"
            logger.info(f"Navigating to profile to find post: {profile_url}")
            self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # 1. Scroll and find a matching post
            max_scrolls = 5
            found_post_el = None
            
            # Look for post content snippet (case-insensitive, partial match)
            search_text = post_content[:50].lower().strip() if post_content else ""
            
            for i in range(max_scrolls):
                logger.debug(f"Scrolling profile to find post... (attempt {i+1})")
                
                # Look for tweet/post containers
                post_locators = self.page.locator("[data-testid='tweet']")
                count = post_locators.count()
                
                for j in range(count):
                    post_el = post_locators.nth(j)
                    inner_text = post_el.inner_text().lower()
                    
                    if not search_text or search_text in inner_text:
                        logger.info(f"Found matching post on @{username}'s profile.")
                        found_post_el = post_el
                        break
                
                if found_post_el:
                    break
                
                # Scroll down
                self.page.mouse.wheel(0, 1000)
                time.sleep(0.8)

            if not found_post_el:
                logger.warning(f"Could not find a post matching content snippet on @{username}'s profile. Using first available post.")
                try:
                    found_post_el = self.page.locator("[data-testid='tweet']").first
                    if not found_post_el.is_visible(timeout=2000):
                        found_post_el = None
                except Exception:
                    found_post_el = None

            if not found_post_el:
                logger.error("No posts found on profile.")
                return False

            # 2. Click on the post to open it (to ensure we are on the status page as requested)
            # Clicking the timestamp or the text body is usually safe
            try:
                # Scroll post into view first
                found_post_el.scroll_into_view_if_needed()
                time.sleep(0.5)
                # Click to open post
                found_post_el.click()
                time.sleep(1.5)
                logger.debug("Navigated to post detail page.")
            except Exception as e:
                logger.warning(f"Failed to click post, may already be on detail page or click blocked: {e}")

            # 3. Robust Typing Logic on Post Detail Page
            logger.info("Attempting to type comment...")
            
            # The "Post your reply" area often needs a click to reveal the real textbox
            reply_placeholder_selectors = [
                "div[data-testid='reply']",
                "[aria-label='Reply']",
                "div[role='textbox'][aria-label='Post text']",
                "div[contenteditable='true']",
                "text='Post your reply'",
            ]

            area_clicked = False
            for sel in reply_placeholder_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=4000):
                        el.click(force=True)
                        area_clicked = True
                        logger.debug(f"Clicked comment area via: {sel}")
                        time.sleep(0.8)
                        break
                except Exception:
                    continue

            # Target the actual textbox
            textbox_selectors = [
                "div[role='textbox'][aria-label='Post text']",
                "div[data-testid='tweetTextarea_0']",
                "div[contenteditable='true'][role='textbox']",
                ".public-DraftEditor-content",
            ]

            textbox = None
            for sel in textbox_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        textbox = el
                        break
                except Exception:
                    continue

            if not textbox:
                logger.error("Could not find active textbox for comment after clicking area.")
                self._screenshot("comment_typing_failed")
                return False

            # Ensure focus and clear (just in case)
            textbox.focus()
            textbox.click()
            time.sleep(0.5)
            
            # Clear any existing text
            self.page.keyboard.press("Control+a")
            self.page.keyboard.press("Backspace")
            time.sleep(0.3)

            # Strategy: Sequential typing with delay to look human and avoid anti-bot triggers
            logger.debug(f"Typing message: {message[:30]}...")
            try:
                # Using press_sequentially with a delay for realism
                textbox.press_sequentially(message, delay=40)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Sequential typing failed, falling back to instant insert: {e}")
                self.page.keyboard.insert_text(message)

            # Verification: Check if text actually appeared and matches expected length
            current_val = textbox.inner_text().strip()
            if not current_val or len(current_val) < len(message) * 0.8:
                logger.warning(f"Textbox content mismatch (length {len(current_val)} vs {len(message)}). Retrying with force fill.")
                try:
                    # Final attempt via fill (triggers React events differently)
                    textbox.fill(message)
                    time.sleep(1.0)
                except Exception as e2:
                    logger.error(f"Force fill also failed: {e2}")

            # Submit
            submit_btn_selectors = [
                "[data-testid='tweetButtonInline']",
                "button[data-testid='tweetButtonInline']",
                "button:has-text('Reply')",
                "div[role='button']:has-text('Reply')",
            ]

            submitted = False
            # Wait for button to be enabled if needed
            time.sleep(0.5)
            
            for sel in submit_btn_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        # Ensure it's enabled; if not, wait a bit or force it
                        if not btn.is_enabled():
                            logger.debug("Submit button disabled, waiting...")
                            time.sleep(1.0)
                        
                        btn.click(force=True)
                        submitted = True
                        logger.debug(f"Clicked Reply button via: {sel}")
                        time.sleep(1.5)
                        break
                except Exception:
                    continue

            if not submitted:
                logger.info("Submit button not clicked, attempting Control+Enter...")
                self.page.keyboard.press("Control+Enter")
                time.sleep(2.5)
                submitted = True

            return submitted

        except Exception as e:
            logger.error(f"Error in _comment_on_post: {e}")
            self._screenshot("comment_flow_error")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # DM Open Methods
    # ─────────────────────────────────────────────────────────────────────────

    def _open_dm_via_messages_compose(self, username: str) -> bool:
        """
        Flow:
          1. Go to x.com/messages
          2. Click the New Message / Compose button
          3. Type username in the search input
          4. Select from TypeaheadUser dropdown
          5. Click Next
          6. Confirm DM composer is visible
        Returns True if the DM composer window is ready.
        """
        try:
            # 1. Navigate to Messages
            logger.debug("Navigating to x.com/messages ...")
            self.page.goto("https://x.com/messages", wait_until="domcontentloaded", timeout=20000)
            time.sleep(1.8)

            # 2. Click the compose / New Message button
            compose_selectors = [
                "a[href='/messages/compose']",
                "[data-testid='dm-new-chat-button']",
                "[data-testid='dm-empty-conversation-new-chat-button']",
                "[aria-label='New message']",
                "button[aria-label='New message']",
            ]
            compose_clicked = False
            for sel in compose_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        compose_clicked = True
                        logger.debug(f"Clicked compose via: {sel}")
                        time.sleep(0.8)
                        break
                except Exception:
                    continue

            if not compose_clicked:
                # Try navigating directly to the compose URL
                logger.debug("Compose button not found, trying direct URL...")
                try:
                    self.page.goto("https://x.com/messages/compose", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    compose_clicked = True
                except Exception:
                    pass

            if not compose_clicked:
                logger.warning("Could not open New Message compose dialog.")
                return False

            # 3. Wait for and find the search input
            search_selectors = [
                "input[placeholder='Search name or username']",
                "input[placeholder='Search people']",
                "input[data-testid='searchPeople']",
                "[data-testid='searchPeopleTypeahead'] input",
                "input[aria-label='Search name or username']",
                "input[type='text']",
            ]
            search_el = None
            for sel in search_selectors:
                try:
                    el = self.page.locator(sel).first
                    el.wait_for(state="visible", timeout=5000)
                    search_el = el
                    logger.debug(f"Found search input via: {sel}")
                    break
                except Exception:
                    continue

            if not search_el:
                logger.warning("Search input not found in compose dialog.")
                self._screenshot(f"compose_no_search_{username}")
                return False

            # 4. Type the username
            logger.debug(f"Typing username: @{username}")
            search_el.click()
            search_el.fill("")
            search_el.press_sequentially(username, delay=30)
            
            # 5. Select user from dropdown
            # We wait for the dropdown to appear and then click the match
            if not self._select_user_from_dropdown(username):
                logger.warning(f"Failed to select @{username} from DM search dropdown.")
                return False

            logger.debug(f"Selected @{username}. Clicking Next...")

            # 6. Click "Next" button
            next_selectors = [
                 "[data-testid='nextButton']",
                 "button:has-text('Next')",
                 "[role='button']:has-text('Next')",
            ]
            next_clicked = False
            for sel in next_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        next_clicked = True
                        logger.debug(f"Clicked Next via: {sel}")
                        break
                except Exception:
                    continue

            if not next_clicked:
                 # Sometimes clicking the item automatically opens the chat or enables the next button
                 logger.debug("Next button not clicked - continuing to check if composer appeared.")

            # 7. Confirm DM composer is visible
            return self._wait_for_composer(username)

        except Exception as e:
            logger.debug(f"_open_dm_via_messages_compose error: {e}")
            return False

    def _open_dm_via_profile(self, username: str, profile_url: str) -> bool:
        """
        Fallback flow:
          1. Navigate to https://x.com/<username> (or provided profile_url)
          2. Click the Message button on the profile
          3. Confirm DM composer is visible
        """
        url = (
            profile_url
            if profile_url and profile_url.startswith("http")
            else f"https://x.com/{username}"
        )
        try:
            logger.debug(f"Navigating to profile: {url}")
            self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(1.5)

            # Look for a "Message" button
            message_btn_selectors = [
                "[data-testid='sendDMFromProfile']",
                "button[aria-label='Message']",
                "div[data-testid='sendDMFromProfile']",
                "button:has-text('Message')",
                "[role='button']:has-text('Message')",
                "div[aria-label='Message']",
                "svg[aria-label='Message']",
            ]
            btn_clicked = False
            for sel in message_btn_selectors:
                try:
                    el = self.page.locator(sel).first
                    el.wait_for(state="visible", timeout=6000)
                    if el.is_visible():
                        el.click()
                        btn_clicked = True
                        logger.debug(f"Clicked Message button via: {sel}")
                        time.sleep(2.0)
                        break
                except Exception:
                    continue

            if not btn_clicked:
                logger.warning(f"No Message button found on profile for @{username}.")
                self._screenshot(f"profile_no_msgbtn_{username}")
                return False

            return self._wait_for_composer(username)

        except Exception as e:
            logger.debug(f"_open_dm_via_profile error: {e}")
            return False

    def _select_user_from_dropdown(self, username: str) -> bool:
        """Helper to click the specific user in the DM search dropdown."""
        # Clean username
        u = username.lower().lstrip("@")
        
        # Combined selector for speed - matches data-testid or text handles
        # Use a short timeout because it should appear quickly after typing
        selectors = [
            f"[data-testid='typeaheadUserItem'] >> text='@{u}'",
            f"[data-testid='TypeaheadUser'] >> text='@{u}'",
            f"[role='option']:has-text('@{u}')",
            f"text='@{u}'"
        ]
        
        # Wait for ANY of the result containers first
        try:
            self.page.wait_for_selector("[data-testid='typeaheadUserItem'], [data-testid='TypeaheadUser'], [role='option']", timeout=5000)
        except Exception:
            pass

        for sel in selectors:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=1000):
                    el.click()
                    logger.debug(f"Selected user via: {sel}")
                    return True
            except Exception:
                continue
        
        # Last effort: click the first thing that looks like a search result
        try:
            el = self.page.locator("[data-testid='typeaheadUserItem'], [data-testid='TypeaheadUser']").first
            if el.is_visible(timeout=500):
                el.click()
                logger.warning(f"Clicked first result for @{u} without handle confirmation.")
                return True
        except Exception:
            pass

        return False

    def _wait_for_composer(self, username: str) -> bool:
        """Waits for the DM text composer to become visible."""
        # Prioritise the most specific DM selectors first.
        # The outer wrapper alone is not typeable — but its presence confirms the chat is open.
        primary_selectors = [
            "div[data-testid='dmComposerTextInput']",
            "[placeholder='Unencrypted message']",
            "[placeholder='Start a message']",
            "[placeholder='Message']",
            "div[role='textbox'][aria-label='Start a message']",
            "div[role='textbox'][aria-label='Message']",
        ]
        combined_sel = ",".join(primary_selectors)
        try:
            self.page.wait_for_selector(combined_sel, state="visible", timeout=10000)
            logger.info(f"DM composer ready for @{username}.")
            return True
        except Exception:
            pass

        logger.warning(f"DM composer did not appear for @{username}.")
        self._screenshot(f"no_composer_{username}")
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Message Sending
    # ─────────────────────────────────────────────────────────────────────────

    def _send_dm(self, text: str) -> bool:
        """
        Clicks the DM composer inner contenteditable, types the message,
        then clicks Send or falls back to Enter.
        """
        try:
            # ── Step 1: Find the INNER typeable element ─────────────────────────
            # The outer div[data-testid='dmComposerTextInput'] is only a wrapper;
            # keyboard events must go to the inner contenteditable.
            inner_selectors = [
                # Most specific: inner contenteditable inside the DM composer wrapper
                "div[data-testid='dmComposerTextInput'] div[contenteditable='true']",
                "div[data-testid='dmComposerTextInput'] div[role='textbox']",
                # Placeholder-based (works on input AND contenteditable)
                "[placeholder='Unencrypted message']",
                "[placeholder='Start a message']",
                "[placeholder='Message']",
                "div[role='textbox'][aria-label='Start a message']",
                "div[role='textbox'][aria-label='Message']",
                # Generic contenteditable fallback
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true']",
                "div[role='textbox']",
                # Broader fallbacks — only reached if above fail
                "div[role='textbox'][data-testid='dmComposerTextInput']",
                "div[contenteditable='true'][data-testid='dmComposerTextInput']",
            ]

            combined_sel = ",".join(inner_selectors)
            composer_el = self.page.locator(combined_sel).first
            
            try:
                # Wait for any of the selectors to become available
                composer_el.wait_for(state="visible", timeout=5000)
            except Exception:
                logger.error("DM composer inner element not found.")
                self._screenshot("send_no_composer")
                return False

            # ── Step 2: Focus the element robustly ─────────────────────────────
            # Triple-click to select all, then force-click to make sure focus lands
            try:
                composer_el.click(force=True)
                time.sleep(0.1)
                composer_el.triple_click()
                time.sleep(0.1)
            except Exception:
                pass

            # Also use JS to ensure focus on the element
            try:
                self.page.evaluate("el => { if(el) { el.focus(); el.click(); } }",
                                   composer_el.element_handle())
                time.sleep(0.1)
            except Exception:
                pass

            # ── Step 3: Clear existing text ─────────────────────────────────────
            self.page.keyboard.press("Control+a")
            self.page.keyboard.press("Backspace")
            time.sleep(0.1)

            # Try typing with delay for realism
            logger.info(f"Typing message: {len(text)} chars total...")
            typed_ok = False
            try:
                # Character by character - more reliable for triggering React state and looking human
                composer_el.press_sequentially(text, delay=40)
                typed_ok = True
                logger.debug("Typed via press_sequentially")
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Sequential typing failed ({e}), falling back to instant insert")
                self.page.keyboard.insert_text(text)
                typed_ok = True

            # Verify if text actually landed
            current_text = composer_el.inner_text().strip()
            # If the text is exactly the placeholder, it usually means it didn't take
            placeholder_val = composer_el.get_attribute("placeholder") or ""
            
            if not typed_ok or (not current_text or current_text == placeholder_val):
                try:
                    logger.debug(f"Instant typing seems empty ('{current_text}'), falling back to press_sequentially...")
                    composer_el.click(force=True)
                    time.sleep(0.2)
                    # Clear any existing text
                    self.page.keyboard.press("Control+a")
                    self.page.keyboard.press("Backspace")
                    time.sleep(0.2)
                    # Type character by character - more reliable for triggering React state
                    composer_el.press_sequentially(text, delay=35)
                    typed_ok = True
                except Exception as e2:
                    logger.error(f"Fallback typing failed: {e2}")
                    self._screenshot("typing_failed")
                    return False

            time.sleep(0.8)

            # 4. Click Send button
            send_selectors = [
                "[data-testid='dmComposerSendButton']",
                "button[data-testid='dmComposerSendButton']",
                "[aria-label='Send message']",
                "[aria-label='Send']",
                "button:has-text('Send')",
            ]
            send_clicked = False
            for sel in send_selectors:
                try:
                    btn = self.page.locator(sel).first
                    btn.wait_for(state="visible", timeout=1000)
                    if btn.is_visible() and btn.is_enabled():
                        btn.click()
                        send_clicked = True
                        logger.debug(f"Send button clicked via: {sel}")
                        break
                except Exception:
                    continue

            if not send_clicked:
                logger.debug("Send button not found — pressing Enter to send.")
                self.page.keyboard.press("Enter")

            time.sleep(2.0)
            return True

        except Exception as e:
            logger.error(f"Error in _send_dm: {e}")
            self._screenshot("send_dm_error")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_reply(self) -> str:
        """Detects if there is a prior message in the conversation."""
        try:
            time.sleep(1.0)
            messages = self.page.locator(config.SELECTORS["message_entry"]).all()
            return "replied" if messages else "none"
        except Exception:
            return "none"

    def _build_message(self, template: str, post_content: str, post_url: str) -> str:
        """Substitutes placeholders in the template."""
        content = post_content.strip() if isinstance(post_content, str) and post_content.strip() else "your recent post"
        url = post_url.strip() if isinstance(post_url, str) else ""
        try:
            msg = template.replace("{post_content}", content)
            msg = msg.replace("{post_url}", url)
            return msg.strip()
        except Exception:
            return "Hi,\n\nWould love to connect."

    def _screenshot(self, label: str):
        """Saves a debug screenshot."""
        try:
            path = f"debug_{label}.png"
            self.page.screenshot(path=path)
            logger.debug(f"Screenshot saved: {path}")
        except Exception:
            pass
