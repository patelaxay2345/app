#!/usr/bin/env python3
"""
Add partner configuration to JobTalk dashboard
Usage: 
  1. Set environment variables for partner credentials
  2. Run: python3 add-partner.py
  
Required Environment Variables:
  - PARTNER_NAME: Partner name
  - PARTNER_DB_HOST: Database host
  - PARTNER_DB_PORT: Database port (default: 3306)
  - PARTNER_DB_NAME: Database name
  - PARTNER_DB_USER: Database username
  - PARTNER_DB_PASSWORD: Database password
  - PARTNER_SSH_HOST: SSH host
  - PARTNER_SSH_PORT: SSH port (default: 22)
  - PARTNER_SSH_USER: SSH username
  
SSH Authentication (choose one):
  - PARTNER_SSH_PASSWORD: SSH password (recommended, simpler)
  - PARTNER_SSH_KEY: SSH private key (optional, if no password)
  - PARTNER_SSH_KEY_PATH: Path to SSH private key file (optional)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid

# Import services
from services.encryption import EncryptionService

# Load environment
load_dotenv(Path(__file__).parent / 'backend' / '.env')

async def main():
    print("\n" + "="*70)
    print("  Adding Partner to JobTalk Dashboard")
    print("="*70 + "\n")

    # Get partner credentials from environment
    partner_name = os.getenv('PARTNER_NAME')
    db_host = os.getenv('PARTNER_DB_HOST')
    db_port = int(os.getenv('PARTNER_DB_PORT', '3306'))
    db_name = os.getenv('PARTNER_DB_NAME')
    db_user = os.getenv('PARTNER_DB_USER')
    db_password = os.getenv('PARTNER_DB_PASSWORD')
    
    ssh_host = os.getenv('PARTNER_SSH_HOST')
    ssh_port = int(os.getenv('PARTNER_SSH_PORT', '22'))
    ssh_user = os.getenv('PARTNER_SSH_USER')
    ssh_key = os.getenv('PARTNER_SSH_KEY')
    ssh_password = os.getenv('PARTNER_SSH_PASSWORD')
    
    concurrency_limit = int(os.getenv('PARTNER_CONCURRENCY_LIMIT', '50'))
    
    # Validate required fields
    required_fields = {
        'PARTNER_NAME': partner_name,
        'PARTNER_DB_HOST': db_host,
        'PARTNER_DB_NAME': db_name,
        'PARTNER_DB_USER': db_user,
        'PARTNER_DB_PASSWORD': db_password,
        'PARTNER_SSH_HOST': ssh_host,
        'PARTNER_SSH_USER': ssh_user,
    }
    
    missing_fields = [k for k, v in required_fields.items() if not v]
    if missing_fields:
        print(f"❌ Missing required environment variables: {', '.join(missing_fields)}")
        print("\nPlease set them before running this script.")
        print("Example:")
        print("  export PARTNER_NAME='PartnerName'")
        print("  export PARTNER_DB_HOST='db.example.com'")
        print("  # ... set other variables")
        print("  python3 add-partner.py")
        return
    
    if not ssh_key and not ssh_password:
        print("❌ Either PARTNER_SSH_KEY or PARTNER_SSH_PASSWORD must be provided")
        return

    # Connect to MongoDB (your JobTalk database)
    mongo_url = os.environ.get('MONGO_URL')
    db_name_dashboard = os.environ.get('DB_NAME', 'recruitment_admin')
    
    if not mongo_url:
        print("❌ MONGO_URL not found in backend/.env")
        return
    
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name_dashboard]
        
        # Test connection
        await client.admin.command('ping')
        print(f"✅ Connected to JobTalk database: {db_name_dashboard}\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    # Initialize encryption service
    encryption_service = EncryptionService()
    
    # Check if partner already exists
    existing = await db.partner_configs.find_one({"partnerName": partner_name})
    
    if existing:
        print(f"⚠️  Partner '{partner_name}' already exists!")
        print(f"   Partner ID: {existing['id']}")
        
        response = input("\n   Do you want to update it? (yes/no): ")
        if response.lower() != 'yes':
            print("\n   Keeping existing partner. Exiting...")
            client.close()
            return
        
        partner_id = existing['id']
        print(f"\n   Updating existing partner {partner_id}...")
    else:
        partner_id = str(uuid.uuid4())
        print(f"   Creating new partner with ID: {partner_id}")
    
    # Encrypt sensitive data
    print("\n📝 Encrypting credentials...")
    encrypted_db_password = encryption_service.encrypt(db_password)
    
    ssh_config = {
        "enabled": True,
        "host": ssh_host,
        "port": ssh_port,
        "username": ssh_user,
        "password": None,
        "privateKey": None,
        "passphrase": None
    }
    
    if ssh_key:
        encrypted_ssh_key = encryption_service.encrypt(ssh_key)
        ssh_config['privateKey'] = encrypted_ssh_key
    elif ssh_password:
        encrypted_ssh_password = encryption_service.encrypt(ssh_password)
        ssh_config['password'] = encrypted_ssh_password
    
    partner_data = {
        "id": partner_id,
        "partnerName": partner_name,
        "tenantId": 1,
        "dbHost": db_host,
        "dbPort": db_port,
        "dbName": db_name,
        "dbUsername": db_user,
        "dbPassword": encrypted_db_password,
        "dbType": "mysql",
        "sshConfig": ssh_config,
        "concurrencyLimit": concurrency_limit,
        "isActive": True,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "lastSyncAt": None,
        "lastSyncStatus": "NEVER_SYNCED",
        "lastErrorMessage": None
    }
    
    if existing:
        await db.partner_configs.update_one(
            {"id": partner_id},
            {"$set": partner_data}
        )
        print("✅ Partner updated successfully!")
    else:
        await db.partner_configs.insert_one(partner_data)
        print("✅ Partner created successfully!")
    
    print("\n" + "="*70)
    print("  Partner Configuration")
    print("="*70)
    print(f"  Partner ID: {partner_id}")
    print(f"  Partner Name: {partner_name}")
    print(f"  Database: {db_host}:{db_port}/{db_name}")
    print(f"  SSH Tunnel: {ssh_host}:{ssh_port}")
    print(f"  Concurrency Limit: {concurrency_limit}")
    print(f"  Status: {'Active' if partner_data['isActive'] else 'Inactive'}")
    print("="*70 + "\n")
    
    print("🎉 Setup Complete!\n")
    print("Next steps:")
    print("  1. Start your backend: cd backend && uvicorn server:app --reload")
    print("  2. Access dashboard: http://localhost:3000")
    print("  3. Navigate to Partners page")
    print("  4. Click 'Force Sync' to fetch REAL data\n")
    
    client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
