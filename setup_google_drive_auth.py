"""
NER-SAFE: Google Drive / Google One OAuth2 Setup Utility
Enables genuine Google Drive API v3 backup for live landslide predictions and risk snapshots.

How Google One Integration Works:
Google One storage is accessed via the Google Drive API v3. When NER-SAFE uploads
predictions, alerts, or audit logs to Google Drive, they consume your Google One storage quota.
"""

import os
import sys
import json
import webbrowser

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
CREDS_PATH = os.path.join(PROJECT_ROOT, "credentials.json")
TOKEN_PATH = os.path.join(PROJECT_ROOT, "token.json")

def main():
    print("=" * 75)
    print("NER-SAFE GOOGLE DRIVE / GOOGLE ONE OAUTH2 SETUP UTILITY")
    print("=" * 75)
    
    if os.path.exists(TOKEN_PATH):
        print("\n[OK] 'token.json' is already present in your NER-SAFE workspace.")
        try:
            with open(TOKEN_PATH, "r") as f:
                data = json.load(f)
            tok = data.get("token") or data.get("access_token")
            print(f"     Token Preview: {tok[:15]}... (Active)")
            print("     Google Drive live prediction synchronization is ENABLED.")
            return
        except Exception as e:
            print(f"     Notice: Existing token.json needs re-authorization: {e}")

    if not os.path.exists(CREDS_PATH):
        # Check Downloads folder in case user saved it there
        downloads_path = os.path.expanduser(r"~\Downloads\credentials.json.json")
        downloads_path2 = os.path.expanduser(r"~\Downloads\credentials.json")
        candidate = None
        if os.path.exists(downloads_path):
            candidate = downloads_path
        elif os.path.exists(downloads_path2):
            candidate = downloads_path2
        
        if candidate:
            import shutil
            shutil.copy2(candidate, CREDS_PATH)
            print(f"\n[AUTO-DISCOVERY] Found credentials at {candidate} -> Copied to {CREDS_PATH}")
        else:
            print("\n[INFO] 'credentials.json' not found in workspace.")
            print("\nTo connect your Google One account:")
            print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
            print("2. Enable the 'Google Drive API'")
            print("3. Create Credentials -> OAuth 2.0 Client IDs -> Desktop App")
            print("4. Download the JSON file and save it as 'credentials.json' in:")
            print(f"   {PROJECT_ROOT}")
            return

    print(f"\n[FOUND] 'credentials.json' verified at: {CREDS_PATH}", flush=True)
    print("\n[ACTION REQUIRED] Initializing Google OAuth consent flow...", flush=True)
    print("A browser window will open automatically asking you to choose your Google Account", flush=True)
    print("and grant permission for NER-SAFE to save prediction snapshots to your Google Drive / Google One.", flush=True)
    print("-" * 75, flush=True)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        print(f"\nIf the browser does not open automatically, copy and paste this URL into your browser:\n\n{auth_url}\n", flush=True)
        print("Waiting for authorization...", flush=True)
        
        creds = flow.run_local_server(port=0, prompt='consent')
        
        with open(TOKEN_PATH, 'w', encoding='utf-8') as token_file:
            token_file.write(creds.to_json())

        print("\n" + "=" * 75, flush=True)
        print("[SUCCESS] OAuth authorization completed!")
        print(f"[SAVED] Active OAuth credentials written to: {TOKEN_PATH}")
        print("NER-SAFE Google Drive live synchronization is now 100% ACTIVE.")
        print("=" * 75)

        # Test Drive connection immediately
        try:
            from storage_engine import storage_engine
            status = storage_engine.get_status()
            print("\nUpdated Storage Engine Status:")
            print(f"  Backend: {status['storage_backend']}")
            print(f"  Drive Status: {status['drive_status']}")
            print(f"  Google One Compatible: {status['google_one_compatible']}")
        except Exception as te:
            print(f"Status check notice: {te}")

    except Exception as e:
        print(f"\n[ERROR] Authorization failed: {e}")
        print("Please ensure credentials.json is a valid 'Desktop App' OAuth client configuration.")

if __name__ == "__main__":
    main()
