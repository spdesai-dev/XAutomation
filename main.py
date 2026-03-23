import argparse
import time
from loguru import logger

import config
from spreadsheet import SpreadsheetManager
from bot import XAutomationBot

def main():
    parser = argparse.ArgumentParser(description="XAutomation Bot for sending DMs")
    parser.add_argument("input_file", nargs='?', default=config.DEFAULT_INPUT_FILE, help="Path to the input CSV/XLSX file")
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode")
    parser.add_argument("--mock-delay", type=int, help="Override the 10-minute wait (useful for testing)")
    
    args = parser.parse_args()
    
    delay = args.mock_delay if args.mock_delay is not None else config.MESSAGE_DELAY_SECONDS
    input_file = args.input_file

    logger.add("xautomation.log", rotation="1 MB")
    logger.info("Starting XAutomation pipeline...")

    try:
        sm = SpreadsheetManager(input_file)
    except Exception as e:
        logger.error("Exiting due to spreadsheet load error.")
        return

    bot = XAutomationBot(headless=args.headless)
    
    try:
        bot.start()
        
        # Generator for pending users
        pending_users = list(sm.get_pending_users())
        total = len(pending_users)
        
        if total == 0:
            logger.info("No pending users to process.")
            return
            
        logger.info(f"Found {total} pending users.")

        for count, (index, user_data) in enumerate(pending_users, start=1):
            logger.info(f"[{count}/{total}] Processing index {index}: {user_data.get('username')}")
            
            result = bot.process_user(user_data)
            
            sm.update_user_status(index, status=result['status'], reply=result['reply'])
            
            # Don't wait after the last user
            if count < total:
                logger.info(f"Waiting {delay} seconds before next user...")
                time.sleep(delay)

        logger.success("Automation completed successfully.")

    except Exception as e:
         logger.critical(f"Critical error in execution loop: {str(e)}")
    finally:
         bot.stop()
         
if __name__ == "__main__":
    main()
