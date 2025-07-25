#!/usr/bin/env python3
"""
Security utility script for PowerDesk authentication
Run this script to generate secure tokens and passwords
"""

import base64
import secrets
import hashlib
from werkzeug.security import generate_password_hash

def generate_api_token():
    """Generate a secure API token"""
    # Generate 32 random bytes and base64 encode
    token_bytes = secrets.token_bytes(32)
    token = base64.b64encode(token_bytes).decode('utf-8')
    return token

def generate_password():
    """Generate a secure random password"""
    return secrets.token_urlsafe(16)

def hash_password(password):
    """Generate password hash"""
    return generate_password_hash(password)

def generate_secret_key():
    """Generate Flask secret key"""
    return secrets.token_urlsafe(32)

def main():
    print("=== PowerDesk Security Token Generator ===\n")
    
    print("1. API Tokens (for Bearer authentication):")
    for i in range(3):
        token = generate_api_token()
        print(f"   API_TOKEN_{i+1}={token}")
    
    print("\n2. Secure Passwords:")
    print(f"   TEKNISI_PASSWORD={generate_password()}")
    print(f"   APT_PASSWORD={generate_password()}")
    print(f"   ADMIN_PASSWORD={generate_password()}")
    
    print("\n3. Flask Secret Key:")
    print(f"   SECRET_KEY={generate_secret_key()}")
    
    print("\n4. Password Hashes (for verification):")
    test_password = "TestPassword123!"
    print(f"   Test password: {test_password}")
    print(f"   Hash: {hash_password(test_password)}")
    
    print("\n=== Security Recommendations ===")
    print("1. Store these values in environment variables")
    print("2. Never commit tokens/passwords to version control")
    print("3. Rotate tokens regularly (monthly)")
    print("4. Use strong passwords with mixed case, numbers, and symbols")
    print("5. Enable logging and monitoring for authentication events")
    print("6. Consider using a proper secret management system for production")

if __name__ == "__main__":
    main()
