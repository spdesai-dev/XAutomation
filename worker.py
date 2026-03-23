"""
worker.py — Run as a subprocess by server.py.
Args: <file_path> <message_template_json> [--api-key KEY] [--model MODEL] [--use-ai]
"""
import sys
import time
import json
import argparse
from loguru import logger

import config
from spreadsheet import SpreadsheetManager
from bot import XAutomationBot
from ai_generator import generate_dm, RateLimitError, OpenRouterError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")
    parser.add_argument("message_template_json")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--use-ai", action="store_true")
    parser.add_argument("--generate-only", action="store_true", help="Only generate messages for pending users, do not send.")
    parser.add_argument("--send-only", action="store_true", help="Only send messages that are already approved.")
    parser.add_argument("--system-prompt", default="", help="Custom system prompt for AI generation.")
    parser.add_argument("--regenerate-row", type=int, default=-1, help="Regenerate message for a specific row index.")
    parser.add_argument("--feedback", default="", help="Feedback for regeneration.")
    args = parser.parse_args()

    file_path       = args.file_path
    message_template = json.loads(args.message_template_json)
    api_key         = args.api_key
    model           = args.model
    use_ai          = args.use_ai
    generate_only   = args.generate_only
    send_only       = args.send_only
    system_prompt   = args.system_prompt
    regenerate_row  = args.regenerate_row
    feedback        = args.feedback

    # Log to stdout so server can capture it
    logger.remove()
    logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}", colorize=False)
    logger.add("xautomation.log", rotation="1 MB", encoding="utf-8")

    # Support multiple models separated by commas
    models = [m.strip() for m in model.split(',') if m.strip()]
    if not models:
        models = [""]

    logger.info(f"Worker started. AI mode: {'ON' if use_ai else 'OFF'} | Models: {', '.join(models)}")

    try:
        sm = SpreadsheetManager(file_path)
    except Exception as e:
        logger.error(f"Failed to load spreadsheet: {e}")
        sys.exit(1)

    try:
        if generate_only:
            logger.info("Running in GENERATE-ONLY mode.")
            pending_users = list(sm.get_pending_users())
            if not pending_users:
                logger.info("No pending users to generate messages for.")
                return
        elif regenerate_row != -1:
            logger.info(f"Regenerating message for row {regenerate_row}...")
            user_data = sm.get_row_by_index(regenerate_row)
            if not user_data:
                logger.error(f"Row {regenerate_row} not found.")
                return
            pending_users = [(regenerate_row, user_data)]
        else:
            pending_users = [] # To be handled by send/standard modes below
            
        if generate_only or regenerate_row != -1:
            if not pending_users:
                logger.info("No users to process.")
                return

            logger.info(f"Found {len(pending_users)} users to process for generation.")
            for index, user_data in pending_users:
                username     = str(user_data.get('username') or '').strip().lstrip('@')
                post_content = user_data.get('post_content', '')
                post_url     = user_data.get('post_url', '')

                if not username:
                    logger.error(f"Row {index} has no username — skipping.")
                    sm.update_user_status(index, status='failed')
                    continue

                if use_ai and api_key:
                    logger.info(f"Generating AI messages for @{username}...")
                    variations = []
                    
                    # Target 2 variations (DM and Comment)
                    target_count = 2
                    
                    # If multiple models are provided, we distribute the calls
                    calls_to_make = []
                    for i in range(target_count):
                        calls_to_make.append(models[i % len(models)])
                    
                    for i, mod in enumerate(calls_to_make):
                        if i > 0:
                            time.sleep(2.0) # slightly increased base delay
                        
                        max_retries = 3
                        retry_count = 0
                        while retry_count <= max_retries:
                            try:
                                msg = generate_dm(
                                    post_content=post_content,
                                    username=username,
                                    api_key=api_key,
                                    model=mod,
                                    fallback_template=message_template,
                                    system_prompt=system_prompt,
                                    feedback=feedback if regenerate_row != -1 else "",
                                    variation_index=i,
                                    allow_fallback=True,
                                    message_type="dm" if i == 0 else "comment"
                                )
                                variations.append(msg)
                                break
                            except RateLimitError as e:
                                retry_count += 1
                                if retry_count <= max_retries:
                                    wait_time = 5 * retry_count # 5s, 10s, 15s...
                                    logger.warning(f"Rate limit hit for @{username}. Retrying in {wait_time}s... ({retry_count}/{max_retries})")
                                    time.sleep(wait_time)
                                else:
                                    logger.error(f"Rate limit persistent for @{username}. Falling back to template.")
                                    from ai_generator import _apply_fallback
                                    variations.append(_apply_fallback(message_template, post_content))
                                    break
                            except Exception as e:
                                logger.error(f"AI generation error for @{username}: {e}")
                                from ai_generator import _apply_fallback
                                variations.append(_apply_fallback(message_template, post_content))
                                break
                    message = json.dumps(variations)
                else:
                    message_text = message_template.replace("{post_content}", post_content or "your recent post")
                    message_text = message_text.replace("{post_url}", post_url or "")
                    message = json.dumps([message_text] * 2)
                    logger.info(f"Using manual template for @{username} (2 variations).")

                logger.info(f"Messages generated for @{username}. Awaiting manual approval.")
                sm.update_user_status(index, status="pending_approval", generated_message=message)
            
            logger.success("Generation phase finished.")
            return

        # ---- Send Phase or Standard Phase ----
        bot = XAutomationBot(headless=False)
        bot.start()

        if send_only:
            logger.info("Running in SEND-ONLY mode.")
            approved_users = list(sm.get_approved_users())
            if not approved_users:
                logger.info("No approved users to send messages to.")
            else:
                logger.info(f"Found {len(approved_users)} approved messages to send.")
                for index, user_data in approved_users:
                    username = str(user_data.get('username') or '').strip().lstrip('@')
                    
                    if not username:
                        logger.error(f"Approved row {index} has no username — skipping.")
                        sm.update_user_status(index, status='failed')
                        continue

                    generated_message = user_data.get('generated_message', '')
                    
                    if not generated_message:
                        logger.error(f"Approved user @{username} has no generated message! Reverting to pending.")
                        sm.update_user_status(index, status='pending')
                        continue

                    # Pass the full JSON array to the bot, enabling dual DM vs Comment parsing
                    message_to_send = generated_message

                    user_data['username'] = username  # ensure cleaned value
                    user_data['message_template'] = message_to_send
                    logger.info(f"Sending approved message to: @{username}")
                    result = bot.process_user(user_data)
                    sm.update_user_status(index, status=result['status'], reply=result['reply'])
                    
                    delay = config.MESSAGE_DELAY_SECONDS
                    logger.info(f"Sleeping {delay}s before next action...")
                    time.sleep(delay)
            
            logger.success("Sending phase finished.")
        else:
            # Standard sequential mode (if not using human in loop)
            logger.info("Running in STANDARD mode (generate and send sequentially).")
            pending_users = list(sm.get_pending_users())
            if not pending_users:
                 logger.info("No pending users.")
            else:
                for index, user_data in pending_users:
                    username     = str(user_data.get('username') or '').strip().lstrip('@')
                    post_content = user_data.get('post_content', '')
                    post_url     = user_data.get('post_url', '')

                    if not username:
                        logger.error(f"Row {index} has no username — skipping.")
                        sm.update_user_status(index, status='failed')
                        continue

                    user_data['username'] = username  # ensure cleaned value

                    if use_ai and api_key:
                        logger.info(f"Generating AI messages for @{username}...")
                        variations = []
                        target_count = 2
                        calls_to_make = [models[i % len(models)] for i in range(target_count)]

                        for i, mod in enumerate(calls_to_make):
                            if i > 0:
                                time.sleep(1.5)
                            msg = generate_dm(
                                post_content=post_content,
                                username=username,
                                api_key=api_key,
                                model=mod,
                                fallback_template=message_template,
                                system_prompt=system_prompt,
                                variation_index=i,
                                message_type="dm" if i == 0 else "comment"
                            )
                            variations.append(msg)
                        message = json.dumps(variations)
                    else:
                        message_text = message_template.replace("{post_content}", post_content or "your recent post")
                        message_text = message_text.replace("{post_url}", post_url or "")
                        message = json.dumps([message_text] * 2)

                    # Pass the full JSON array to the bot, enabling dual DM vs Comment parsing
                    message_to_send = message

                    user_data['message_template'] = message_to_send
                    logger.info(f"Processing (direct send): @{username}")
                    result = bot.process_user(user_data)
                    sm.update_user_status(index, status=result['status'], reply=result['reply'], generated_message=message_to_send)
                    
                    delay = config.MESSAGE_DELAY_SECONDS
                    logger.info(f"Sleeping {delay}s before next user...")
                    time.sleep(delay)
                    
            logger.success("Automation loop finished.")

    except Exception as e:
        logger.error(f"Critical error in worker: {e}")
    finally:
        if 'bot' in locals():
            try:
                bot.stop()
            except Exception:
                pass
        logger.info("Worker process finished.")

if __name__ == "__main__":
    main()
