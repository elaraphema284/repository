from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def decline_cookies():
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://www.facebook.com/login/identify/?ctx=recover&ars=facebook_login&next=https%3A%2F%2Fwww.facebook.com%2Flogin%2Fidentify&from_login_screen=0"
        print(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for the button to appear (timeout 10 seconds)
        wait = WebDriverWait(driver, 10)
        
        print("Looking for cookie consent button...")
        
        # Try finding the button with Arabic or English aria-label
        # Selector found: div[aria-label="رفض ملفات تعريف الارتباط الاختيارية"] or div[aria-label="Decline optional cookies"]
        
        button = None
        try:
            # First try Arabic
            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="رفض ملفات تعريف الارتباط الاختيارية"]')))
            print("Found Arabic cookie button.")
        except:
            try:
                # Then try English
                button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Decline optional cookies"]')))
                print("Found English cookie button.")
            except:
                print("Could not find cookie button with standard labels. Checking for 'Available options' flow or other variations.")
        
        if button:
            button.click()
            print("Clicked 'Decline optional cookies' successfully.")
            # Verify if needed or just wait a bit
            time.sleep(5) 
        else:
            print("No cookie popup found or button not identified.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Keep browser open for a bit to see result, or close it. 
        # User said "Open link and understand me" -> imply they want to see it or just have it done.
        # I'll leave it open for a few seconds then close, or better yet, pause.
        print("Script finished. Closing in 5 seconds...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    decline_cookies()
