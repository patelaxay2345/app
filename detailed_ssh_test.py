#!/usr/bin/env python3
"""
Detailed SSH Authentication Test
Investigates the specific issues found in backend testing
"""

import asyncio
import aiohttp
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://admin-metrics-5.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'recruitment_admin')

# Test credentials
TEST_USERNAME = "admin"
TEST_PASSWORD = "Admin@2024"

async def investigate_ssh_issues():
    """Investigate the specific SSH authentication issues"""
    
    session = aiohttp.ClientSession()
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Authenticate
        login_data = {"username": TEST_USERNAME, "password": TEST_PASSWORD}
        async with session.post(f"{API_BASE}/auth/login", json=login_data) as response:
            data = await response.json()
            auth_token = data["access_token"]
        
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        print("🔍 Investigating SSH Authentication Issues")
        print("=" * 50)
        
        # Test 1: Backend validation issue
        print("\n1. Testing backend validation for SSH credentials...")
        
        invalid_partner = {
            "partnerName": "InvalidSSHTest",
            "tenantId": 999,
            "dbHost": "test.com",
            "dbPort": 3306,
            "dbName": "test",
            "dbUsername": "user",
            "dbPassword": "pass",
            "sshConfig": {
                "enabled": True,
                "host": "ssh.test.com",
                "port": 22,
                "username": "sshuser",
                "password": None,
                "privateKey": None,
                "passphrase": None
            }
        }
        
        async with session.post(f"{API_BASE}/partners", json=invalid_partner, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("   ❌ ISSUE: Backend allowed partner creation without SSH credentials")
                print(f"   Created partner ID: {data['id']}")
                
                # Clean up
                await session.delete(f"{API_BASE}/partners/{data['id']}", headers=headers)
            else:
                print("   ✅ Backend correctly rejected invalid SSH config")
        
        # Test 2: SSH update behavior
        print("\n2. Testing SSH update behavior...")
        
        # Create a partner with both password and key
        test_key = "-----BEGIN OPENSSH PRIVATE KEY-----\ntest_key_content\n-----END OPENSSH PRIVATE KEY-----"
        
        full_partner = {
            "partnerName": "SSHUpdateTest",
            "tenantId": 888,
            "dbHost": "test.com",
            "dbPort": 3306,
            "dbName": "test",
            "dbUsername": "user",
            "dbPassword": "pass",
            "sshConfig": {
                "enabled": True,
                "host": "ssh.test.com",
                "port": 22,
                "username": "sshuser",
                "password": "original_password",
                "privateKey": test_key,
                "passphrase": "original_passphrase"
            }
        }
        
        async with session.post(f"{API_BASE}/partners", json=full_partner, headers=headers) as response:
            partner_data = await response.json()
            partner_id = partner_data['id']
            
            print(f"   Created test partner: {partner_id}")
            
            # Get original encrypted values
            original_db = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
            original_password = original_db['sshConfig']['password']
            original_key = original_db['sshConfig']['privateKey']
            original_passphrase = original_db['sshConfig']['passphrase']
            
            print(f"   Original encrypted password: {original_password[:20]}...")
            print(f"   Original encrypted key: {original_key[:20]}...")
            print(f"   Original encrypted passphrase: {original_passphrase[:20]}...")
            
            # Test partial update (only password)
            update_data = {
                "sshConfig": {
                    "enabled": True,
                    "host": "ssh.test.com",
                    "port": 22,
                    "username": "sshuser",
                    "password": "new_password"
                    # Note: Not including privateKey and passphrase
                }
            }
            
            async with session.put(f"{API_BASE}/partners/{partner_id}", json=update_data, headers=headers) as response:
                if response.status == 200:
                    print("   ✅ Update successful")
                    
                    # Check what happened to the other fields
                    updated_db = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
                    updated_password = updated_db['sshConfig'].get('password')
                    updated_key = updated_db['sshConfig'].get('privateKey')
                    updated_passphrase = updated_db['sshConfig'].get('passphrase')
                    
                    print(f"   Updated password: {updated_password[:20] if updated_password else 'None'}...")
                    print(f"   Updated key: {updated_key[:20] if updated_key else 'None'}...")
                    print(f"   Updated passphrase: {updated_passphrase[:20] if updated_passphrase else 'None'}...")
                    
                    # Analysis
                    if updated_password != original_password:
                        print("   ✅ Password was updated (encrypted)")
                    else:
                        print("   ❌ Password was not updated")
                    
                    if updated_key == original_key:
                        print("   ✅ Private key remained unchanged")
                    else:
                        print("   ❌ ISSUE: Private key was modified/lost")
                    
                    if updated_passphrase == original_passphrase:
                        print("   ✅ Passphrase remained unchanged")
                    else:
                        print("   ❌ ISSUE: Passphrase was modified/lost")
                        
                else:
                    print(f"   ❌ Update failed: {response.status}")
            
            # Clean up
            await session.delete(f"{API_BASE}/partners/{partner_id}", headers=headers)
            
    finally:
        await session.close()
        mongo_client.close()

if __name__ == "__main__":
    asyncio.run(investigate_ssh_issues())