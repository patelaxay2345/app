#!/usr/bin/env python3
"""
Add ApTask partner with REAL credentials to JobTalk dashboard
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

# SSH Private Key
SSH_PRIVATE_KEY = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEAxpMb1S18RlJWMlWIQp2dEPJIVrw+ykGIpd5Q97DRaP32elAp75BS
zRViz31aKSP0jrb4U+HITST6oxJTiIL2B2uUASQXU+6AviOl3vjXL7Mda37nxciCXv4Q3b
03GJuh9pEGcVXptDxC1wzUOXHeEcPhrGq29kSaODv2T49jHNCaApWBAmCKuIg74zHl4z88
fXHS0ApsMnH1gKlsBrKoJUWBrFVumLSJTUvLgcL8nKHjGwI0bSTtrMGKFLFf6Tsq6n7BGD
JnhLLmQ+JVa9d7yvdKuFwMMg6+YO0syVcXL62ylOuNswhjJEf3KmcGBrBOiySQgPOaEU39
pqAf13RnlQAAA9gkbaTUJG2k1AAAAAdzc2gtcnNhAAABAQDGkxvVLXxGUlYyVYhCnZ0Q8k
hWvD7KQYil3lD3sNFo/fZ6UCnvkFLNFWLPfVopI/SOtvhT4chNJPqjElOIgvYHa5QBJBdT
7oC+I6Xe+Ncvsx1rfufFyIJe/hDdvTcYm6H2kQZxVem0PELXDNQ5cd4Rw+Gsarb2RJo4O/
ZPj2Mc0JoClYECYIq4iDvjMeXjPzx9cdLQCmwycfWAqWwGsqglRYGsVW6YtIlNS8uBwvyc
oeMbAjRtJO2swYoUsV/pOyrqfsEYMmeEsuZD4lVr13vK90q4XAwyDr5g7SzJVxcvrbKU64
2zCGMkR/cqZwYGsE6LJJCA85oRTf2moB/XdGeVAAAAAwEAAQAAAQAcoU8tAD7fwLVO0ogv
2puvus71OnTvIl26VIBmBedbdOpZnj89nBhkG0ZA1jjun5F+FiFdrrr7bG56noTOtNsWHM
udEoAOiN+lCmy65jPYW8HNIuH14T/yxDzYS5SrBp1meGhuZM2qP9n/OYlLswAqnYxnGIfC
oAeAPhz4QZsvpx68R1sWT6aJyPjIlGRzZX8kLggFJyHL86piY+CX8YiFXZSAM9IACWTTVM
KuCfKhPD2yORYj6ZCkmX96PhyEBgKKBCipgCerKwHYehmdw1RGv5rYKJ4/ZRTfvwyYgUdq
G2G3grfi/YVqzUzdjwFXxvf7z4iVaY8i6ooQErMxP3sNAAAAgQDtpMykzbgYgEahSHBe/o
pvsbkUCuNuFwmK33rN+SZYPJQwtUzrW60n7+dsd47b23T7MmgMd/dQRKk62je9hqlfYfLn
HDMOaUp9vAqdifwgvKrEbMP+ecAINNLZFA4cU50Na/5/km3Wxt1f71l2am1o4Nhk2m+6si
T7V35ORoFAlwAAAIEA7zUvk9wK45mwlD7sn4x1pCYWjrx9fmfY5TvaoisOvhsNDTaCoCNV
xYPlS2EDFBKBaEZDOlnlqJiGNFplDQnJCYMvq4SDHPkXZp6NiL1nQgIvGYdtiyeUqGh3Z3
SCy9zTkkx6RM7hqRIsP6jJjB2TheKmW0sJ63CV4gKEAmY+sWsAAACBANSDtAZoxfTkY66k
zsUcrMD2Tiy3pcY7zmZzE0CjQbefeNuwlD5h/PaluvnAxReRVkm57hTXyVHcxNsc2Ikb5x
odaGy+Y1F/26B/DPJl93HkNAFn4/Q2Tdzx4OnkQxQ01reZaUEmi3Jmx+2BkIBdVQj0lSwA
ITUheRc1VW+rmor/AAAAG0ZvciBHSVRMQUIgQ0kvQ0QgZGVwbG95bWVudAECAwQFBgc=
-----END OPENSSH PRIVATE KEY-----"""

async def main():
    print("\n" + "="*70)
    print("  Adding ApTask Partner to JobTalk Dashboard")
    print("="*70 + "\n")

    # Connect to MongoDB (your JobTalk database)
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'recruitment_admin')
    
    if not mongo_url:
        print("❌ MONGO_URL not found in environment")
        return
    
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        print(f"✅ Connected to JobTalk database: {db_name}\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    # Initialize encryption service
    encryption_service = EncryptionService()
    
    # Check if ApTask partner already exists
    existing = await db.partner_configs.find_one({"partnerName": "ApTask"})
    
    if existing:
        print("⚠️  ApTask partner already exists!")
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
    encrypted_db_password = encryption_service.encrypt("AVNS_ME4QjhAtv17LviPV32D")
    encrypted_ssh_key = encryption_service.encrypt(SSH_PRIVATE_KEY)
    
    partner_data = {
        "id": partner_id,
        "partnerName": "ApTask",
        "tenantId": 1,
        "dbHost": "a348714-akamai-prod-4134270-default.g2a.akamaidb.net",
        "dbPort": 25960,
        "dbName": "defaultdb",
        "dbUsername": "akmadmin",
        "dbPassword": encrypted_db_password,
        "dbType": "mysql",
        "sshConfig": {
            "enabled": True,
            "host": "50.116.57.177",
            "port": 22,
            "username": "root",
            "password": None,
            "privateKey": encrypted_ssh_key,
            "passphrase": None
        },
        "concurrencyLimit": 50,  # Adjust based on your needs
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
    print("  ApTask Partner Configuration")
    print("="*70)
    print(f"  Partner ID: {partner_id}")
    print(f"  Partner Name: ApTask")
    print(f"  Database: {partner_data['dbHost']}:{partner_data['dbPort']}")
    print(f"  SSH Tunnel: {partner_data['sshConfig']['host']}")
    print(f"  Concurrency Limit: {partner_data['concurrencyLimit']}")
    print(f"  Status: {'Active' if partner_data['isActive'] else 'Inactive'}")
    print("="*70 + "\n")
    
    print("🎉 Setup Complete!\n")
    print("Next steps:")
    print("  1. Start your backend: cd backend && uvicorn server:app --reload")
    print("  2. Access dashboard: http://localhost:3000")
    print("  3. Navigate to Partners page")
    print("  4. Click 'Force Sync' to fetch REAL data from ApTask database\n")
    
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
