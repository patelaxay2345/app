#!/usr/bin/env python3
"""
Test script to add ApTask partner and test connection
This script will:
1. Add ApTask partner to the database
2. Test SSH connection
3. Test database connection
4. Fetch sample data
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
from services.ssh_connection import SSHConnectionService
from models import PartnerConfig, SSHConfig

# Load environment
load_dotenv(Path(__file__).parent / 'backend' / '.env')

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def log_success(msg):
    print(f"{GREEN}✓{NC} {msg}")

def log_error(msg):
    print(f"{RED}✗{NC} {msg}")

def log_info(msg):
    print(f"{BLUE}ℹ{NC} {msg}")

def log_warning(msg):
    print(f"{YELLOW}!{NC} {msg}")


async def main():
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}  ApTask Partner Setup & Connection Test{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

    # Connect to MongoDB
    log_info("Connecting to MongoDB...")
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'recruitment_admin')
    
    if not mongo_url:
        log_error("MONGO_URL not found in environment")
        return
    
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        log_success(f"Connected to MongoDB: {db_name}")
    except Exception as e:
        log_error(f"Failed to connect to MongoDB: {e}")
        return

    # Initialize encryption service
    encryption_service = EncryptionService()
    log_success("Encryption service initialized")

    # Check if partner already exists
    log_info("Checking if ApTask partner already exists...")
    existing = await db.partner_configs.find_one({"partnerName": "ApTask"})
    
    if existing:
        log_warning("ApTask partner already exists in database")
        partner_id = existing['id']
        log_info(f"Using existing partner ID: {partner_id}")
    else:
        # Create ApTask partner configuration
        log_info("Creating ApTask partner configuration...")
        
        partner_id = str(uuid.uuid4())
        
        # SSH Private Key (provided by user)
        ssh_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
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

        # Encrypt sensitive data
        encrypted_db_password = encryption_service.encrypt("AVNS_ME4QjhAtv17LviPV32D")
        encrypted_ssh_key = encryption_service.encrypt(ssh_private_key)
        
        partner_data = {
            "id": partner_id,
            "partnerName": "ApTask",
            "dbHost": "a348714-akamai-prod-4134270-default.g2a.akamaidb.net",
            "dbPort": 25960,
            "dbName": "defaultdb",
            "dbUser": "akmadmin",
            "dbPassword": encrypted_db_password,
            "sshConfig": {
                "enabled": True,
                "host": "50.116.57.177",
                "port": 22,
                "username": "root",
                "privateKey": encrypted_ssh_key,
                "passphrase": None
            },
            "isActive": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "lastSyncAt": None
        }
        
        await db.partner_configs.insert_one(partner_data)
        log_success("ApTask partner added to database")

    # Load partner from database
    log_info("Loading partner configuration...")
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    
    if not partner_data:
        log_error("Failed to load partner configuration")
        return
    
    partner = PartnerConfig(**partner_data)
    log_success(f"Partner loaded: {partner.partnerName}")

    # Test SSH connection
    print(f"\n{BLUE}Testing SSH Connection...{NC}")
    ssh_service = SSHConnectionService(db, encryption_service)
    
    try:
        test_result = await ssh_service.test_connection(partner)
        
        if test_result.success:
            log_success(f"SSH Connection: {test_result.message}")
        else:
            log_error(f"SSH Connection Failed: {test_result.message}")
            if test_result.details:
                log_error(f"Details: {test_result.details}")
    except Exception as e:
        log_error(f"SSH Connection Error: {str(e)}")

    # Test database query through SSH tunnel
    print(f"\n{BLUE}Testing Database Connection...{NC}")
    
    try:
        # Try to connect and run a simple query
        connection = await ssh_service.get_connection(partner)
        
        if connection.get('client'):
            log_success("Database connection established")
            
            # Try to fetch some data
            log_info("Fetching sample data...")
            
            try:
                partner_db = connection['client'][partner.dbName]
                
                # List collections
                collections = await partner_db.list_collection_names()
                log_success(f"Found {len(collections)} collections")
                print(f"  Collections: {', '.join(collections[:5])}...")
                
                # Count documents in each collection
                print(f"\n{BLUE}Collection Statistics:{NC}")
                for collection_name in collections[:10]:  # First 10 collections
                    try:
                        count = await partner_db[collection_name].count_documents({})
                        print(f"  • {collection_name}: {count} documents")
                    except Exception as e:
                        print(f"  • {collection_name}: Error - {str(e)}")
                
            except Exception as e:
                log_error(f"Failed to fetch data: {str(e)}")
            finally:
                # Close connection
                if connection.get('client'):
                    connection['client'].close()
                    log_info("Database connection closed")
        else:
            log_error("Failed to establish database connection")
            
    except Exception as e:
        log_error(f"Database Connection Error: {str(e)}")

    # Summary
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{GREEN}Test Complete!{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")
    
    print("Next Steps:")
    print(f"1. Check the dashboard at: {BLUE}http://localhost:3000{NC}")
    print(f"2. Login with: {BLUE}admin / Admin@2024{NC}")
    print(f"3. Navigate to Partners to see ApTask")
    print(f"4. Click 'Test Connection' to verify")
    print(f"5. Click 'Force Sync' to fetch data\n")

    # Close MongoDB connection
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{NC}")
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
