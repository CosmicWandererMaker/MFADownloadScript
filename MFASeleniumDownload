#!/usr/bin/env python3

import os
import time
import getpass
import sys
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
# TODO: Set the directory where you want files to be downloaded.
# Use an absolute path for reliability.
DOWNLOAD_DIR = os.path.join(os.getcwd(), "selenium_downloads")
MAX_WAIT_TIME = 30  # Max seconds to wait for elements or downloads
DOWNLOAD_CHECK_INTERVAL = 1 # Seconds between checking download status
DOWNLOAD_STABILITY_TIME = 3 # Seconds the file size must be stable to be considered complete

def create_download_dir_if_not_exists(directory):
    """Creates the download directory if it doesn't exist."""
    if not os.path.exists(directory):
        print(f"Creating download directory: {directory}")
        os.makedirs(directory)
    else:
        print(f"Using existing download directory: {directory}")

def get_downloaded_filename(driver, download_dir, timeout=MAX_WAIT_TIME):
    """
    Waits for a download to complete in the specified directory.

    Args:
        driver: The Selenium WebDriver instance.
        download_dir: The directory where the file is being downloaded.
        timeout: Maximum time to wait for the download.

    Returns:
        The filename of the completed download, or None if timeout or error.
    """
    print("Waiting for download to start and complete...")
    start_time = time.time()
    initial_files = set(os.listdir(download_dir))
    last_size = -1
    stable_time_start = None

    while time.time() - start_time < timeout:
        current_files = set(os.listdir(download_dir))
        new_files = current_files - initial_files

        if not new_files:
            # No new file detected yet
            time.sleep(DOWNLOAD_CHECK_INTERVAL)
            continue

        # Check for temporary download files (specific to Chrome here)
        downloading = False
        potential_filename = None
        for fname in new_files:
            if fname.endswith(".crdownload"):
                downloading = True
                # Keep track of the potential final name
                potential_filename = os.path.splitext(fname)[0]
                break # Found an active download, no need to check others yet
            elif not fname.endswith(".tmp"): # Ignore other temp files if any
                 potential_filename = fname # Assume this is the file if no .crdownload found

        if downloading:
            print(f"\rDownload in progress ({fname})...", end="")
            last_size = -1 # Reset size check while actively downloading
            stable_time_start = None
            time.sleep(DOWNLOAD_CHECK_INTERVAL)
            continue

        # If no .crdownload files, check if the potential file exists and is stable
        if potential_filename:
            filepath = os.path.join(download_dir, potential_filename)
            if os.path.exists(filepath):
                current_size = os.path.getsize(filepath)
                if current_size == last_size:
                    # Size is stable
                    if stable_time_start is None:
                        stable_time_start = time.time()
                    elif time.time() - stable_time_start >= DOWNLOAD_STABILITY_TIME:
                        print(f"\nDownload appears complete: {potential_filename} (size stable)")
                        return potential_filename # Success!
                    else:
                        # Still waiting for stability duration
                         print(f"\rFile size stable, confirming ({time.time() - stable_time_start:.1f}s)...", end="")

                else:
                    # Size changed, reset stability timer
                    print(f"\rFile size changed ({current_size} bytes), waiting...", end="")
                    last_size = current_size
                    stable_time_start = None
            else:
                 # File might have been renamed quickly, reset
                 last_size = -1
                 stable_time_start = None


        time.sleep(DOWNLOAD_CHECK_INTERVAL)

    print("\nDownload timed out or file did not stabilize.")
    return None


def download_file_with_selenium_mfa():
    """
    Uses Selenium to log in with username, password, MFA and download a file.
    Requires user customization for element locators.
    """
    # --- Get User Input ---
    login_url = input("Enter the LOGIN page URL: ")
    # TODO: Sometimes the download isn't on the login page. You might need a separate
    # download_target_url = input("Enter the specific page URL containing the download link (if different): ")
    username = input("Enter your username: ")
    try:
        password = getpass.getpass("Enter your password: ")
    except Exception as error:
        print(f"\nError reading password: {error}")
        sys.exit(1)

    mfa_code = input("Enter your 6-digit MFA code: ")
    if not (mfa_code.isdigit() and len(mfa_code) == 6):
       print("Warning: MFA code entered does not appear to be 6 digits. Continuing anyway...")

    # --- Prepare Download Directory ---
    create_download_dir_if_not_exists(DOWNLOAD_DIR)

    # --- Configure WebDriver ---
    options = webdriver.ChromeOptions()
    # Set download preferences
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False, # Disable download prompt
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True # Optional: Prevent PDF viewing in browser
    }
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless")  # Optional: Run Chrome without a visible window
    options.add_argument("--disable-gpu") # Often needed for headless mode
    options.add_argument("--window-size=1920,1080") # Specify window size
    options.add_argument("--no-sandbox") # May be needed in some environments
    options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems

    driver = None # Initialize driver variable
    try:
        print("Initializing WebDriver...")
        # Use webdriver-manager to automatically handle chromedriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5) # Implicit wait for elements (use cautiously)
        wait = WebDriverWait(driver, MAX_WAIT_TIME)
        print("WebDriver initialized.")

        # --- Login Steps ---
        print(f"Navigating to login page: {login_url}")
        driver.get(login_url)

        # TODO: *** CUSTOMIZE LOCATORS BELOW ***
        # Find elements using ID, Name, XPath, CSS Selector, etc.
        # Use your browser's Developer Tools (usually F12) to inspect elements.

        # --- Enter Username ---
        print("Finding username field...")
        # Example locators (replace with actual ones):
        # username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        # username_field = wait.until(EC.presence_of_element_located((By.NAME, "user")))
        username_locator = (By.ID, "username") # <<-- FIND AND REPLACE THIS
        username_field = wait.until(EC.visibility_of_element_located(username_locator))
        print("Entering username...")
        username_field.send_keys(username)

        # --- Enter Password ---
        print("Finding password field...")
        # Example locators:
        # password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        # password_field = wait.until(EC.presence_of_element_located((By.NAME, "pass")))
        password_locator = (By.ID, "password") # <<-- FIND AND REPLACE THIS
        password_field = wait.until(EC.visibility_of_element_located(password_locator))
        print("Entering password...")
        password_field.send_keys(password)

        # --- Click Login Button ---
        print("Finding and clicking login button...")
        # Example locators:
        # login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign In')]")))
        # login_button = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
        login_button_locator = (By.XPATH, "//button[@type='submit']") # <<-- FIND AND REPLACE THIS
        login_button = wait.until(EC.element_to_be_clickable(login_button_locator))
        login_button.click()
        print("Login submitted. Waiting for potential MFA prompt...")

        # --- Handle MFA ---
        # This part is highly variable. The MFA field might appear immediately,
        # after a delay, or on a new page. Adjust waits and locators accordingly.
        print("Finding MFA code field...")
        # Example locators:
        # mfa_field = wait.until(EC.visibility_of_element_located((By.ID, "mfa-code")))
        # mfa_field = wait.until(EC.visibility_of_element_located((By.NAME, "otp")))
        mfa_locator = (By.ID, "mfa_code") # <<-- FIND AND REPLACE THIS
        try:
            mfa_field = wait.until(EC.visibility_of_element_located(mfa_locator))
            print("Entering MFA code...")
            mfa_field.send_keys(mfa_code)

            # --- Click MFA Submit Button (if necessary) ---
            print("Finding and clicking MFA submit button...")
            # Example locators:
            # mfa_submit_button = wait.until(EC.element_to_be_clickable((By.ID, "mfa-submit")))
            # mfa_submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Verify')]")))
            mfa_submit_locator = (By.XPATH, "//button[contains(text(), 'Verify')]") # <<-- FIND AND REPLACE THIS
            mfa_submit_button = wait.until(EC.element_to_be_clickable(mfa_submit_locator))
            mfa_submit_button.click()
            print("MFA submitted.")

        except TimeoutException:
            print("MFA field did not appear within the timeout period.")
            print("Assuming MFA was not required or login proceeded differently.")
            # You might need more sophisticated checks here depending on the site flow
            # e.g., check if the URL changed to the expected post-login page.

        # --- Navigate to Download Page and Click Download Link/Button ---
        print("Waiting for page load after login/MFA...")
        # TODO: Add waits for elements on the expected landing page if needed
        # Example: wait.until(EC.visibility_of_element_located((By.ID, "dashboard-widget")))
        time.sleep(5) # Simple pause, replace with explicit wait if possible

        # TODO: If the download link is on a different page, navigate there first:
        # print(f"Navigating to download target page: {download_target_url}")
        # driver.get(download_target_url)
        # wait.until(...) # Wait for an element on the download page

        print("Finding download link/button...")
        # TODO: *** CUSTOMIZE LOCATOR FOR THE DOWNLOAD ELEMENT ***
        # Example locators:
        # download_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Download Report")))
        # download_link = wait.until(EC.element_to_be_clickable((By.ID, "download-button")))
        # download_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.button-download")))
        download_locator = (By.XPATH, "//a[contains(@href, 'download')]") # <<-- FIND AND REPLACE THIS
        download_link = wait.until(EC.element_to_be_clickable(download_locator))

        print("Clicking download link/button...")
        # Clear the download directory before starting (optional, be careful)
        # for item in os.listdir(DOWNLOAD_DIR):
        #     item_path = os.path.join(DOWNLOAD_DIR, item)
        #     if os.path.isfile(item_path) or os.path.islink(item_path):
        #         os.unlink(item_path)
        #     elif os.path.isdir(item_path):
        #         shutil.rmtree(item_path)

        download_link.click()

        # --- Wait for Download Completion ---
        downloaded_file = get_downloaded_filename(driver, DOWNLOAD_DIR)

        if downloaded_file:
            print(f"\nSuccessfully downloaded: {downloaded_file}")
            print(f"File saved in: {DOWNLOAD_DIR}")
        else:
            print("\nFailed to confirm download completion.")

    # --- Error Handling ---
    except TimeoutException as e:
        print(f"\nError: An element was not found or operation timed out after {MAX_WAIT_TIME} seconds.")
        print("Check your internet connection, the URL, and the element locators (IDs, XPaths, etc.).")
        # print(f"Page source (first 1000 chars):\n{driver.page_source[:1000] if driver else 'N/A'}")
        # print(f"Current URL: {driver.current_url if driver else 'N/A'}")
        # print(e)
    except NoSuchElementException as e:
        print("\nError: Could not find an element.")
        print("The website structure might have changed, or the locator is incorrect.")
        print(f"Locator attempted: {e.msg}") # Check which locator failed
    except WebDriverException as e:
        print(f"\nError: WebDriver encountered an issue: {e}")
        print("Ensure the browser is installed and WebDriverManager can access it.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

    # --- Cleanup ---
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()
            print("WebDriver closed.")

if __name__ == "__main__":
    download_file_with_selenium_mfa()
