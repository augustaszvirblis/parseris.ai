#!/usr/bin/env python3
"""
Script to setup default adapters for Parseris.ai
Run with your API keys as arguments
"""

import os
import sys

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, '/home/ubuntu/unstract/backend')

import django
django.setup()

from adapter_processor_v2.models import AdapterInstance
from tenant_account_v2.models import Organization
from account_v2.models import User
from unstract.sdk1.constants import AdapterTypes
from django.conf import settings
from cryptography.fernet import Fernet
import json

def main():
    print("=== Parseris.ai Adapter Setup ===\n")
    
    # Show organizations
    print("Available Organizations:")
    orgs = Organization.objects.all()
    for org in orgs:
        print(f"  - {org.display_name} (Schema: {org.schema_name})")
    
    print("\nUsers:")
    users = User.objects.all()
    for user in users:
        print(f"  - {user.email}")
    
    print("\n" + "="*50)
    print("To create adapters, edit this script and add your API keys")
    print("="*50)

if __name__ == '__main__':
    main()
