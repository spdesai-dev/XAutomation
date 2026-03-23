import sys
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Capture console messages
        page.on("console", lambda msg: print(f"Browser Console [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser Page Error:\n{err}\nStack: {getattr(err, 'stack', 'No stack')}"))
        
        print("Navigating to http://127.0.0.1:5000...")
        try:
            page.goto("http://127.0.0.1:5000", wait_until="networkidle")
            page.wait_for_timeout(2000)
            
            # Print HTML to see if ai-toggle exists
            ai_toggle_exists = page.evaluate("!!document.getElementById('ai-toggle')")
            print(f"ai-toggle exists: {ai_toggle_exists}")
            
            ai_toggle_outer = page.evaluate("document.getElementById('ai-toggle') ? document.getElementById('ai-toggle').outerHTML : 'null'")
            print(f"ai-toggle outerHTML: {ai_toggle_outer}")
            
        except Exception as e:
            print(f"Failed to load: {e}")
            
        browser.close()

if __name__ == "__main__":
    main()
