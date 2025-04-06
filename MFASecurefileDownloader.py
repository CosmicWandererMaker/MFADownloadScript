#!/usr/bin/env python3

import os
import time
import getpass
import sys
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
# Removed: from webdriver_manager.chrome import ChromeDriverManager - WebDriverManager is no longer used
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)


# --- Configuration ---
# TODO: Set the directory where you want files to be downloaded.
# Use an absolute path for reliability.
DOWNLOAD_DIR = os.path.join(os.getcwd(), "selenium_downloads")

# --- !! IMPORTANT !! ---
# Chromedriver setup: Remove webdriver-manager dependency.
# Option 1 (Recommended if not in PATH): Specify the full path to your chromedriver executable.
#            Download from: https://chromedriver.chromium.org/downloads
#            Example: CHROMEDRIVER_PATH = "/path/to/your/chromedriver" # On Linux/macOS
#            Example: CHROMEDRIVER_PATH = r"C:\path\to\your\chromedriver.exe" # On Windows
CHROMEDRIVER_PATH = None # Set this to the path if chromedriver is NOT in your system PATH

# Option 2: Leave CHROMEDRIVER_PATH = None if chromedriver is already in your system's PATH.
# --- End Chromedriver Setup ---


MAX_WAIT_TIME = 300  # Max seconds to wait for elements or downloads (Increased from 30)
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
        try:
            current_files = set(os.listdir(download_dir))
            new_files = current_files - initial_files
        except FileNotFoundError:
            print(f"\nError: Download directory '{download_dir}' not found during check.")
            return None # Directory gone?

        if not new_files:
            # No new file detected yet
            time.sleep(DOWNLOAD_CHECK_INTERVAL)
            continue

        # Check for temporary download files (specific to Chrome here)
        downloading = False
        potential_filename = None
        active_download_fname = None # Store the name of the .crdownload file
        for fname in new_files:
            if fname.endswith(".crdownload"):
                downloading = True
                active_download_fname = fname
                # Keep track of the potential final name
                potential_filename = os.path.splitext(fname)[0]
                break # Found an active download, no need to check others yet
            elif not fname.endswith(".tmp"): # Ignore other temp files if any
                 potential_filename = fname # Assume this is the file if no .crdownload found

        if downloading:
            print(f"\rDownload in progress ({active_download_fname})...", end="")
            last_size = -1 # Reset size check while actively downloading
            stable_time_start = None
            time.sleep(DOWNLOAD_CHECK_INTERVAL)
            continue

        # If no .crdownload files, check if the potential file exists and is stable
        if potential_filename:
            filepath = os.path.join(download_dir, potential_filename)
            if os.path.exists(filepath):
                try:
                    current_size = os.path.getsize(filepath)
                except OSError:
                    # File might be locked or inaccessible briefly
                    time.sleep(0.1)
                    continue

                if current_size == last_size and current_size > 0: # Ensure size is stable and not zero
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
                    # Size changed, or was zero, reset stability timer
                    # print(f"\rFile size changed ({current_size} bytes), waiting...", end="") # Can be noisy
                    last_size = current_size
                    stable_time_start = None
            else:
                 # File might have been renamed quickly, or disappeared, reset
                 last_size = -1
                 stable_time_start = None


        time.sleep(DOWNLOAD_CHECK_INTERVAL)

    print(f"\nDownload timed out after {timeout} seconds or file did not stabilize.")
    # Clean up potential leftover .crdownload files if timeout occurred
    try:
        current_files_on_timeout = set(os.listdir(download_dir))
        new_files_on_timeout = current_files_on_timeout - initial_files
        for fname in new_files_on_timeout:
            if fname.endswith(".crdownload"):
                crdownload_path = os.path.join(download_dir, fname)
                final_path = os.path.join(download_dir, os.path.splitext(fname)[0])
                # Check if the final file exists and has size, otherwise remove .crdownload
                if not (os.path.exists(final_path) and os.path.getsize(final_path) > 0):
                    print(f"Cleaning up incomplete download file: {fname}")
                    try:
                        os.remove(crdownload_path)
                    except OSError as e:
                        print(f"Warning: Could not remove incomplete file {fname}: {e}")

    except Exception as e:
        print(f"Warning: Error during cleanup check: {e}") # Non-critical

    return None


def download_file_with_selenium_mfa():
    """
    Uses Selenium to log in with email, password, MFA and download a file using a multi-step login.
    Prompts for separate Login URL and Download URL.
    Prompts for MFA code *after* initial login attempt.
    Requires user customization for element locators and manual chromedriver setup.
    *** Locators below are BEST GUESSES or USER-PROVIDED for Site - VERIFY THEM! ***
    """
    # --- Get Initial User Input ---
    # Set default login URL for convenience, can be overridden by user input
    default_login_url = "https://google.com"
    login_url_input = input(f"Enter the LOGIN page URL [{default_login_url}]: ")
    login_url = login_url_input if login_url_input else default_login_url

    download_target_url = input("Enter the specific URL for the download link/page (visited after login): ")
    email_address = input("Enter your email address: ")
    try:
        password = getpass.getpass("Enter your password: ")
    except Exception as error:
        print(f"\nError reading password: {error}")
        sys.exit(1)

    # --- MFA code input is MOVED to later ---

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
        # --- Initialize Chrome Service (Manual Path Handling) ---
        if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
            # Use the specified path
            service = ChromeService(executable_path=CHROMEDRIVER_PATH)
            print(f"Using chromedriver from specified path: {CHROMEDRIVER_PATH}")
        else:
            # Assume chromedriver is in PATH
            service = ChromeService()
            print("Using chromedriver found in system PATH.")
            print("Ensure the correct version is installed and accessible.")
            if CHROMEDRIVER_PATH: # If path was set but not found
                 print(f"Warning: Specified CHROMEDRIVER_PATH '{CHROMEDRIVER_PATH}' not found. Falling back to PATH.")

        driver = webdriver.Chrome(service=service, options=options)
        # Increase implicit wait slightly if pages load slower, but explicit waits are better
        # driver.implicitly_wait(10)
        wait = WebDriverWait(driver, MAX_WAIT_TIME)
        print("WebDriver initialized.")

        # --- Login Steps ---
        print(f"Navigating to login page: {login_url}")
        driver.get(login_url)

        # --- !! VERIFY THESE LOCATORS !! ---
        # Use your browser's Developer Tools (F12) to inspect elements on securefile.mandiant.com

        # --- Enter Email Address ---
        print("Finding email field...")
        # GUESS: Trying common ID/Name attributes for email. Verify this!
        email_locator = (By.ID, "email") # <<-- VERIFY THIS LOCATOR (e.g., By.ID, By.NAME, By.XPATH)
        email_field = wait.until(EC.visibility_of_element_located(email_locator))
        print("Entering email address...")
        email_field.clear() # Clear field first
        email_field.send_keys(email_address)

        # --- Click Next Button ---
        # --- NEW STEP ---
        print("Finding and clicking Next button...")
        # Using user-provided XPath. Still verify this!
        next_button_locator = (By.XPATH, '//*[@id="signinApp"]/div[1]/div[2]/div/div[1]/div[3]/button') # <<-- VERIFY THIS LOCATOR (User-provided XPath)
        next_button = wait.until(EC.element_to_be_clickable(next_button_locator))
        next_button.click()
        print("Next button clicked. Waiting for password field...")
        # Add a small pause or preferably an explicit wait for the password field to appear/become interactive
        # Example explicit wait:
        # wait.until(EC.visibility_of_element_located((By.ID, "password"))) # Use the correct password locator here
        time.sleep(1) # Small pause as fallback, increase if needed but explicit wait is better

        # --- Enter Password ---
        print("Finding password field (after clicking Next)...")
        # GUESS: Trying common ID/Name attributes for password. Verify this!
        password_locator = (By.ID, "password") # <<-- VERIFY THIS LOCATOR
        # Wait specifically for the password field to be visible now
        password_field = wait.until(EC.visibility_of_element_located(password_locator))
        print("Entering password...")
        password_field.clear() # Clear field first
        password_field.send_keys(password)

        # --- Click Sign In Button ---
        # --- MODIFIED STEP (was Login Button) ---
        print("Finding and clicking Sign in button...")
        # MODIFIED: Using user-provided XPath, adjusted to target button instead of inner span. Verify this!
        signin_button_locator = (By.XPATH, '//*[@id="signinApp"]/div[1]/div[2]/div/div[1]/div/div[4]/button') # <<-- VERIFY THIS LOCATOR (User-provided XPath, adjusted to button)
        signin_button = wait.until(EC.element_to_be_clickable(signin_button_locator))
        signin_button.click()
        print("Sign in submitted.") # Modified print statement
        # --- End modification ---

        # --- !! NEW FLOW: Prompt for MFA code AFTER initial login attempt !! ---
        print("\n" + "="*40)
        print("Please check your email, SMS, or authenticator app for the MFA code.")
        print("The script will now pause and wait for you to enter it.")
        print("="*40 + "\n")
        # The input() call itself will pause the script until the user presses Enter
        mfa_code = input("Enter your 6-digit MFA code: ")
        if not (mfa_code.isdigit() and len(mfa_code) == 6):
           print("Warning: MFA code entered does not appear to be 6 digits. Continuing anyway...")
        # --- End of new MFA prompt section ---


        # --- Handle MFA Field Input ---
        # Now that the user has provided the code, try to find the field and enter it.
        print("Attempting to find MFA code field on the page...")
        # GUESS: Trying common IDs/Names for MFA/OTP fields. Verify this!
        mfa_locator = (By.ID, "otp") # <<-- VERIFY THIS LOCATOR (e.g., By.ID, By.NAME 'mfa_code', 'token')
        try:
            # Wait for the MFA field to be visible *after* the initial login click
            mfa_field = wait.until(EC.visibility_of_element_located(mfa_locator))
            print("MFA field found. Entering MFA code...")
            mfa_field.clear() # Clear field first
            mfa_field.send_keys(mfa_code) # Use the code entered by the user

            # --- Click MFA Submit Button (if necessary) ---
            print("Finding and clicking MFA submit button...")
            # MODIFIED: Using user-provided Full XPath for the MFA submit button.
            # Note: Full XPaths can be brittle if the page structure changes.
            mfa_submit_locator = (By.XPATH, '/html/body/div[1]/div/main/div[2]/div[5]/button') # <<-- VERIFY THIS LOCATOR (User-provided Full XPath for MFA submit)
            # Add a small explicit wait before clicking MFA submit, sometimes needed
            time.sleep(2) # Increased sleep slightly before MFA submit click
            mfa_submit_button = wait.until(EC.element_to_be_clickable(mfa_submit_locator))
            mfa_submit_button.click()
            print("MFA submitted.")

        except TimeoutException:
            # This means the MFA field wasn't found after the initial login + pause + user input
            print("\nError: MFA field was not found on the page after the initial login attempt.")
            print("Possibilities:")
            print(" - Initial email/password was incorrect.")
            print(" - The page did not load the MFA prompt correctly after sign-in.")
            print(" - The locator for the MFA field ('mfa_locator') is incorrect.")
            print(" - The website doesn't require MFA for this login.")
            raise # Re-raise the TimeoutException

        # --- Navigate to Download Page ---
        print("\nLogin/MFA process complete.")
        # --- NEW: Navigate to the specific download URL provided by the user ---
        print(f"Navigating to download page: {download_target_url}")
        driver.get(download_target_url)
        print("Waiting for download page elements to load...")
        # TODO: Add a specific wait for an element expected on the download page for robustness
        # This ensures the page is ready before searching for the download link.
        # Example: wait.until(EC.visibility_of_element_located((By.ID, "some_element_on_download_page")))
        time.sleep(3) # Replace this simple pause with an explicit wait if possible

        # --- Find and Click Download Link/Button on the Download Page ---
        print("Finding download link/button on the download page...")
        # !! MUST BE CUSTOMIZED by inspecting the download_target_url page after login !!
        download_locator = (By.XPATH, "//a[contains(@href, 'download')]") # <<-- GENERIC EXAMPLE - REPLACE THIS
        download_link = wait.until(EC.element_to_be_clickable(download_locator))

        print("Clicking download link/button...")
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
        # Specific TimeoutException handling moved inside the MFA block for clarity
        # This top-level handler catches timeouts during other stages (finding user/pass fields, login btn, download link etc.)
        print(f"\nError: An element was not found or operation timed out after {MAX_WAIT_TIME} seconds.")
        print("Check your internet connection, the URLs, and the element locators (IDs, XPaths, etc.).")
        print("Also ensure the correct chromedriver is installed and accessible via PATH or CHROMEDRIVER_PATH setting.")
        # print(f"Page source (first 1000 chars):\n{driver.page_source[:1000] if driver else 'N/A'}")
        # print(f"Current URL: {driver.current_url if driver else 'N/A'}")
        # print(e)
    except NoSuchElementException as e:
        print("\nError: Could not find an element.")
        print("The website structure might have changed, or the locator is incorrect.")
        print(f"Locator attempted: {e.msg}") # Check which locator failed
    except WebDriverException as e:
        # Catch more specific webdriver errors if possible
        if "chrome not reachable" in str(e) or "cannot connect to chrome" in str(e):
             print(f"\nError: WebDriver lost connection to the Chrome browser: {e}")
        elif "unable to discover open window" in str(e):
             print(f"\nError: Browser window may have been closed unexpectedly: {e}")
        elif "session not created" in str(e) or "could not start a new session" in str(e):
             print(f"\nError: Failed to create a new WebDriver session: {e}")
             print("Check if chromedriver version matches Chrome browser version and if chromedriver is executable.")
        else:
            print(f"\nError: WebDriver encountered an issue: {e}")
            print("Ensure the browser is installed and the correct chromedriver is accessible.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

    # --- Cleanup ---
    finally:
        if driver:
            print("Closing WebDriver...")
            try:
                driver.quit()
                print("WebDriver closed.")
            except Exception as e:
                print(f"Warning: Error during WebDriver cleanup: {e}")

if __name__ == "__main__":
    download_file_with_selenium_mfa()
