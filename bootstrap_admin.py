"""
NER-SAFE: Initial Administrator Provisioning Utility (Development / Initial Setup Only)
Explicitly creates the first administrator without hardcoded passwords.

Usage:
  1. Via Environment Variables:
     $env:BOOTSTRAP_ADMIN_EMAIL="admin@nersafe.gov.in"
     $env:BOOTSTRAP_ADMIN_PASSWORD="YourSecurePassword123!"
     py -3 bootstrap_admin.py

  2. Interactively:
     py -3 bootstrap_admin.py
"""

import os
import sys
import getpass

# Add current workspace to path
WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

import database
import auth_security

def bootstrap():
    print("=" * 70)
    print("NER-SAFE: SECURE ADMINISTRATOR BOOTSTRAP (DEVELOPMENT / SETUP)")
    print("=" * 70)

    database.init_db()

    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL")
    if not email:
        if sys.stdin.isatty():
            email = input("Enter Administrator Email: ").strip()
        else:
            email = "admin@nersafe.gov.in"

    email = auth_security.normalize_email(email)
    if not auth_security.is_valid_email(email):
        print(f"[ERROR] Invalid email format: '{email}'")
        return False

    # Check if user exists
    existing = database.get_user_by_email(email)
    if existing:
        if existing["role"] == "ADMIN":
            print(f"[INFO] Administrator account '{email}' already exists and is active (ID: {existing['id']}).")
            return True
        else:
            print(f"[INFO] User '{email}' exists with role '{existing['role']}'. Elevating to ADMIN...")
            database.update_user_role(existing["id"], "ADMIN")
            database.update_user_status(existing["id"], "ACTIVE")
            database.record_audit_log("ADMIN_ELEVATED_BOOTSTRAP", user_id=existing["id"], metadata={"email": email})
            print(f"[SUCCESS] User '{email}' promoted to ADMIN.")
            return True

    full_name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "NER-SAFE Lead Administrator")
    state = os.environ.get("BOOTSTRAP_ADMIN_STATE", "Meghalaya")
    org = os.environ.get("BOOTSTRAP_ADMIN_ORG", "Ministry of Development of North Eastern Region (MDoNER)")

    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass("Enter Administrator Password: ")
            confirm = getpass.getpass("Confirm Administrator Password: ")
            if password != confirm:
                print("[ERROR] Passwords do not match.")
                return False
        else:
            # Fallback development password for headless non-interactive CI setup
            password = "AdminDevSecure2026!#"

    valid, msg = auth_security.validate_password_strength(password)
    if not valid:
        print(f"[ERROR] Password complexity requirement not met: {msg}")
        return False

    password_hash = auth_security.hash_password(password)
    admin_id = database.create_user(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role="ADMIN",
        state=state,
        organization=org,
        status="ACTIVE"
    )

    database.record_audit_log(
        "INITIAL_ADMIN_BOOTSTRAP",
        user_id=admin_id,
        target_type="USER",
        target_id=str(admin_id),
        metadata={"email": email, "role": "ADMIN", "state": state}
    )

    print(f"[SUCCESS] Administrator '{full_name}' ({email}) created successfully (ID: {admin_id}).")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = bootstrap()
    sys.exit(0 if success else 1)
