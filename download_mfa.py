#!/usr/bin/env python3

import requests
import getpass
import os
from urllib.parse import urlparse
import sys

def download_file_with_mfa_prompt():
    """
    Prompts for URL, credentials, MFA code, and attempts to download a file.
    Assumes HTTP Basic Authentication for username/password. MFA handling
    is highly site-specific and may require script modification or different tools.
    """
    # --- Get User Input ---
    url = input("Enter the full URL to download the file from: ")
    if not url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)

    username = input("Enter your username: ")
    try:
        # Use getpass to securely read the password without echoing it
        password = getpass.getpass("Enter your password: ")
    except Exception as error:
        print(f"\nError reading password: {error}")
        sys.exit(1)

    mfa_code = input("Enter your 6-digit MFA code: ")
    if not (mfa_code.isdigit() and len(mfa_code) == 6):
       print("Warning: MFA code entered does not appear to be 6 digits. Continuing anyway...")
       # You might want to add stricter validation or exit here:
       # print("Error: MFA code must be exactly 6 digits.")
       # sys.exit(1)

    # --- Prepare Authentication ---
    # Basic Authentication for username/password
    auth = (username, password)

    # *** How the MFA code is used is SITE-SPECIFIC ***
    # This script DOES NOT automatically handle complex multi-step MFA flows.
    # Option 1: Maybe it's a custom header (unlikely for direct download GET)?
    # You would need to know the exact header name the server expects.
    # Example: headers = {'X-MFA-TOKEN': mfa_code}
    headers = {} # Start with empty headers, modify if needed for your specific case

    # Option 2: Multi-step login (Common) - This script CANNOT handle this directly.
    # Requires tools like Selenium or knowledge of specific API calls & session cookies.

    print("-" * 30)
    print("Attempting download using Basic Authentication (username/password).")
    print("NOTE: Standard web MFA often requires multiple steps not handled by this basic script.")
    print(f"The provided MFA code '{mfa_code}' is collected but may not be used ")
    print("unless the target URL specifically accepts it via a simple mechanism ")
    print("(like a custom header configured above).")
    print("-" * 30)

    # --- Make Request and Download ---
    try:
        print(f"Connecting to {url}...")
        # Use stream=True to avoid loading the entire file into memory at once
        with requests.get(url, auth=auth, headers=headers, stream=True, timeout=30) as response:
            # Check if the request was successful (status code 2xx)
            response.raise_for_status()
            print("Authentication successful (based on initial response). Starting download...")

            # --- Determine Filename ---
            filename = None
            # 1. Try Content-Disposition header
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                # Basic parsing: find 'filename=' and extract value
                parts = content_disposition.split('filename=')
                if len(parts) > 1:
                    filename = parts[1].strip('"\' ') # Remove quotes/spaces

            # 2. Fallback: Get filename from URL path
            if not filename:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                if not filename: # If path is empty or just '/'
                    filename = "downloaded_file" # Default fallback name
                    print(f"Could not determine filename from headers or URL, using default: {filename}")
                else:
                    print(f"Determined filename from URL: {filename}")
            else:
                 print(f"Determined filename from Content-Disposition header: {filename}")


            # --- Download Content with Progress ---
            total_size = response.headers.get('content-length')
            downloaded_size = 0

            with open(filename, 'wb') as f:
                if total_size is None: # No content length header
                    print("No size information available. Downloading...")
                    f.write(response.content) # Read all at once (potential memory issue for large files)
                    print(f"\nDownload complete. Saved as '{filename}'")
                else:
                    total_size = int(total_size)
                    block_size = 8192 # 8KB chunks
                    print(f"Total size: {total_size / (1024*1024):.2f} MB")
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # Calculate and display progress
                            progress = int(50 * downloaded_size / total_size)
                            percent = downloaded_size * 100 / total_size
                            sys.stdout.write(f"\rDownloading: [{'=' * progress}{' ' * (50 - progress)}] {percent:.1f}%")
                            sys.stdout.flush()
                    print(f"\nDownload complete. Saved as '{filename}'")

    # --- Error Handling ---
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        if status_code == 401:
            print(f"\nError: Authentication failed (401 Unauthorized).")
            print("Please check your username and password.")
            print("Also, the site might require a more complex MFA login process not supported by this script.")
        elif status_code == 403:
             print(f"\nError: Access forbidden (403 Forbidden).")
             print("You may have authenticated but lack permission to access this specific resource.")
        elif status_code == 404:
             print(f"\nError: File not found at URL (404 Not Found). Check the URL.")
        else:
            print(f"\nHTTP Error occurred: {http_err}")
            # print(f"Response body sample: {http_err.response.text[:500]}") # Uncomment for debugging
    except requests.exceptions.ConnectionError as conn_err:
        print(f"\nConnection Error: Could not connect to the server.")
        print(f"Details: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"\nRequest timed out: The server did not respond in time.")
        print(f"Details: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"\nAn error occurred during the request: {req_err}")
    except IOError as io_err:
         print(f"\nFile writing error: Could not save the file '{filename}'.")
         print(f"Details: {io_err}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging


if __name__ == "__main__":
    download_file_with_mfa_prompt()
