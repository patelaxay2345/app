#!/usr/bin/env python3
"""
Focused SSH Authentication Fix Testing
Tests the specific scenarios mentioned in the review request
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://dash-jobtalk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'recruitment_admin')

# Test credentials
TEST_USERNAME = "admin"
TEST_PASSWORD = "Admin@2024"

class SSHFixTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.mongo_client = None
        self.db = None
        self.test_results = []
        self.created_partners = []
        
    async def setup(self):
        """Initialize test session and database connection"""
        print(f"🔧 Setting up SSH Fix Test environment...")
        print(f"Backend URL: {API_BASE}")
        
        # Setup HTTP session
        self.session = aiohttp.ClientSession()
        
        # Setup MongoDB connection
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        
        # Authenticate
        await self.authenticate()
        
    async def cleanup(self):
        """Clean up test resources"""
        print(f"\n🧹 Cleaning up test resources...")
        
        # Delete created test partners
        for partner_id in self.created_partners:
            try:
                await self.delete_partner(partner_id)
                print(f"   ✅ Deleted test partner: {partner_id}")
            except Exception as e:
                print(f"   ⚠️  Failed to delete partner {partner_id}: {e}")
        
        # Close connections
        if self.session:
            await self.session.close()
        if self.mongo_client:
            self.mongo_client.close()
            
    async def authenticate(self):
        """Authenticate with the backend API"""
        print(f"🔐 Authenticating as {TEST_USERNAME}...")
        
        login_data = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        
        async with self.session.post(f"{API_BASE}/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data["access_token"]
                print(f"   ✅ Authentication successful")
                return True
            else:
                error_text = await response.text()
                raise Exception(f"Authentication failed: {response.status} - {error_text}")
    
    def get_headers(self):
        """Get headers with authentication token"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    async def create_partner(self, partner_data):
        """Create a new partner"""
        async with self.session.post(
            f"{API_BASE}/partners", 
            json=partner_data, 
            headers=self.get_headers()
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.created_partners.append(data["id"])
                return data
            else:
                error_text = await response.text()
                raise Exception(f"Partner creation failed: {response.status} - {error_text}")
    
    async def update_partner(self, partner_id, update_data):
        """Update partner"""
        async with self.session.put(
            f"{API_BASE}/partners/{partner_id}", 
            json=update_data, 
            headers=self.get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Partner update failed: {response.status} - {error_text}")
    
    async def delete_partner(self, partner_id):
        """Delete partner"""
        async with self.session.delete(
            f"{API_BASE}/partners/{partner_id}", 
            headers=self.get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Partner deletion failed: {response.status} - {error_text}")
    
    async def get_partner_from_db(self, partner_id):
        """Get partner directly from MongoDB"""
        return await self.db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    async def test_backend_validation_no_ssh_auth(self):
        """Test 1: Backend Validation Test - No SSH Authentication Method"""
        print(f"\n🧪 Test 1: Backend Validation - SSH enabled but no password or privateKey")
        
        partner_data = {
            "partnerName": f"ValidationTest_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 1,
            "dbHost": "validation-test.example.com",
            "dbPort": 3306,
            "dbName": "validation_db",
            "dbUsername": "validation_user",
            "dbPassword": "validation_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh-validation.example.com",
                "port": 22,
                "username": "ssh_validation_user",
                "password": "",  # Empty password
                "privateKey": "",  # Empty private key
                "passphrase": ""
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # This should fail with 400 error
            created_partner = await self.create_partner(partner_data)
            self.log_result("backend_validation", False, "Backend allowed partner creation without SSH auth method - validation missing")
            
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg and ("authentication" in error_msg.lower() or "password" in error_msg.lower() or "key" in error_msg.lower()):
                self.log_result("backend_validation", True, f"Backend correctly rejected invalid SSH config: {error_msg}")
            else:
                self.log_result("backend_validation", False, f"Unexpected error (should be 400 validation error): {error_msg}")
    
    async def test_ssh_config_merge_update_password_only(self):
        """Test 2: SSH Config Merge - Update Password Only"""
        print(f"\n🧪 Test 2: SSH Config Merge - Update Password Only (preserve privateKey)")
        
        test_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""
        
        # Create partner with both password and private key
        partner_data = {
            "partnerName": f"MergeTest_PWD_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 2,
            "dbHost": "merge-test.example.com",
            "dbPort": 3306,
            "dbName": "merge_db",
            "dbUsername": "merge_user",
            "dbPassword": "merge_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh-merge.example.com",
                "port": 22,
                "username": "ssh_merge_user",
                "password": "original_password_123",
                "privateKey": test_private_key,
                "passphrase": "original_passphrase_456"
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Get original encrypted values
            original_db_partner = await self.get_partner_from_db(partner_id)
            original_private_key = original_db_partner["sshConfig"]["privateKey"]
            original_passphrase = original_db_partner["sshConfig"]["passphrase"]
            
            # Update ONLY the password (don't send privateKey in update)
            update_data = {
                "sshConfig": {
                    "enabled": True,
                    "host": "ssh-merge.example.com",
                    "port": 22,
                    "username": "ssh_merge_user",
                    "password": "updated_password_789"
                    # Intentionally NOT including privateKey and passphrase
                }
            }
            
            updated_partner = await self.update_partner(partner_id, update_data)
            
            # Verify in database
            updated_db_partner = await self.get_partner_from_db(partner_id)
            
            # Check that privateKey is still present and encrypted
            current_private_key = updated_db_partner["sshConfig"].get("privateKey")
            if current_private_key and current_private_key == original_private_key:
                self.log_result("preserve_private_key", True, "Private key preserved during password-only update")
            else:
                self.log_result("preserve_private_key", False, f"Private key lost or changed: {current_private_key}")
            
            # Check that passphrase is still present and encrypted
            current_passphrase = updated_db_partner["sshConfig"].get("passphrase")
            if current_passphrase and current_passphrase == original_passphrase:
                self.log_result("preserve_passphrase", True, "Passphrase preserved during password-only update")
            else:
                self.log_result("preserve_passphrase", False, f"Passphrase lost or changed: {current_passphrase}")
            
            # Check that password was updated and encrypted
            new_password = updated_db_partner["sshConfig"]["password"]
            if new_password and new_password != "updated_password_789":
                self.log_result("update_password", True, "Password updated and encrypted correctly")
            else:
                self.log_result("update_password", False, f"Password not encrypted properly: {new_password}")
                
        except Exception as e:
            self.log_result("ssh_merge_password", False, f"Test failed: {str(e)}")
    
    async def test_ssh_config_merge_update_key_only(self):
        """Test 3: SSH Config Merge - Update Key Only"""
        print(f"\n🧪 Test 3: SSH Config Merge - Update Key Only (preserve password)")
        
        original_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""
        
        new_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA9876543210fedcba...
-----END OPENSSH PRIVATE KEY-----"""
        
        # Create partner with both password and private key
        partner_data = {
            "partnerName": f"MergeTest_KEY_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 3,
            "dbHost": "merge-key-test.example.com",
            "dbPort": 3306,
            "dbName": "merge_key_db",
            "dbUsername": "merge_key_user",
            "dbPassword": "merge_key_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh-merge-key.example.com",
                "port": 22,
                "username": "ssh_merge_key_user",
                "password": "original_password_abc",
                "privateKey": original_private_key,
                "passphrase": "original_passphrase_def"
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Get original encrypted values
            original_db_partner = await self.get_partner_from_db(partner_id)
            original_password = original_db_partner["sshConfig"]["password"]
            
            # Update ONLY the privateKey (don't send password in update)
            update_data = {
                "sshConfig": {
                    "enabled": True,
                    "host": "ssh-merge-key.example.com",
                    "port": 22,
                    "username": "ssh_merge_key_user",
                    "privateKey": new_private_key,
                    "passphrase": "updated_passphrase_ghi"
                    # Intentionally NOT including password
                }
            }
            
            updated_partner = await self.update_partner(partner_id, update_data)
            
            # Verify in database
            updated_db_partner = await self.get_partner_from_db(partner_id)
            
            # Check that password is still present and encrypted
            current_password = updated_db_partner["sshConfig"].get("password")
            if current_password and current_password == original_password:
                self.log_result("preserve_password", True, "Password preserved during key-only update")
            else:
                self.log_result("preserve_password", False, f"Password lost or changed: {current_password}")
            
            # Check that privateKey was updated and encrypted
            new_key = updated_db_partner["sshConfig"]["privateKey"]
            if new_key and new_key != new_private_key:
                self.log_result("update_private_key", True, "Private key updated and encrypted correctly")
            else:
                self.log_result("update_private_key", False, f"Private key not encrypted properly: {new_key}")
            
            # Check that passphrase was updated and encrypted
            new_passphrase = updated_db_partner["sshConfig"]["passphrase"]
            if new_passphrase and new_passphrase != "updated_passphrase_ghi":
                self.log_result("update_passphrase", True, "Passphrase updated and encrypted correctly")
            else:
                self.log_result("update_passphrase", False, f"Passphrase not encrypted properly: {new_passphrase}")
                
        except Exception as e:
            self.log_result("ssh_merge_key", False, f"Test failed: {str(e)}")
    
    async def test_ssh_config_no_credential_changes(self):
        """Test 4: SSH Config Merge - No Credential Changes"""
        print(f"\n🧪 Test 4: SSH Config Merge - No Credential Changes (update other fields only)")
        
        # Create partner with SSH password
        partner_data = {
            "partnerName": f"NoChangeTest_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 4,
            "dbHost": "no-change-test.example.com",
            "dbPort": 3306,
            "dbName": "no_change_db",
            "dbUsername": "no_change_user",
            "dbPassword": "no_change_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh-no-change.example.com",
                "port": 22,
                "username": "ssh_no_change_user",
                "password": "stable_password_xyz",
                "privateKey": None,
                "passphrase": None
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Get original encrypted password
            original_db_partner = await self.get_partner_from_db(partner_id)
            original_password = original_db_partner["sshConfig"]["password"]
            
            # Update partner but don't change SSH credentials (just update partner name)
            update_data = {
                "partnerName": f"Updated_{partner_data['partnerName']}",
                "concurrencyLimit": 20
                # Not including sshConfig at all
            }
            
            updated_partner = await self.update_partner(partner_id, update_data)
            
            # Verify SSH password remains unchanged and encrypted
            updated_db_partner = await self.get_partner_from_db(partner_id)
            current_password = updated_db_partner["sshConfig"]["password"]
            
            if current_password == original_password:
                self.log_result("ssh_unchanged", True, "SSH password remains encrypted and unchanged")
            else:
                self.log_result("ssh_unchanged", False, f"SSH password changed unexpectedly: {current_password}")
            
            # Verify other fields were updated
            if updated_db_partner["partnerName"] == update_data["partnerName"]:
                self.log_result("other_fields_updated", True, "Other fields updated correctly while preserving SSH")
            else:
                self.log_result("other_fields_updated", False, "Other fields not updated correctly")
                
        except Exception as e:
            self.log_result("no_credential_changes", False, f"Test failed: {str(e)}")
    
    async def test_verify_no_double_encryption(self):
        """Test 5: Verify No Double Encryption"""
        print(f"\n🧪 Test 5: Verify No Double Encryption")
        
        # Create partner
        partner_data = {
            "partnerName": f"DoubleEncTest_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 5,
            "dbHost": "double-enc-test.example.com",
            "dbPort": 3306,
            "dbName": "double_enc_db",
            "dbUsername": "double_enc_user",
            "dbPassword": "double_enc_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh-double-enc.example.com",
                "port": 22,
                "username": "ssh_double_enc_user",
                "password": "test_password_for_encryption",
                "privateKey": None,
                "passphrase": None
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Get encrypted password from database
            db_partner_1 = await self.get_partner_from_db(partner_id)
            encrypted_password_1 = db_partner_1["sshConfig"]["password"]
            
            # Update partner multiple times without changing SSH credentials
            for i in range(3):
                update_data = {
                    "concurrencyLimit": 10 + i
                }
                await self.update_partner(partner_id, update_data)
                
                # Check that password remains the same (not re-encrypted)
                db_partner = await self.get_partner_from_db(partner_id)
                current_password = db_partner["sshConfig"]["password"]
                
                if current_password != encrypted_password_1:
                    self.log_result("no_double_encryption", False, f"Password changed on update {i+1} - possible double encryption")
                    return
            
            self.log_result("no_double_encryption", True, "SSH password not double-encrypted across multiple updates")
                
        except Exception as e:
            self.log_result("double_encryption_test", False, f"Test failed: {str(e)}")
    
    async def run_ssh_fix_tests(self):
        """Run all SSH fix test scenarios"""
        print(f"🚀 Starting SSH Authentication Fix Tests")
        print(f"=" * 60)
        
        try:
            await self.setup()
            
            # Run specific test scenarios from review request
            await self.test_backend_validation_no_ssh_auth()
            await self.test_ssh_config_merge_update_password_only()
            await self.test_ssh_config_merge_update_key_only()
            await self.test_ssh_config_no_credential_changes()
            await self.test_verify_no_double_encryption()
            
        finally:
            await self.cleanup()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print(f"\n" + "=" * 60)
        print(f"📊 SSH FIX TEST RESULTS SUMMARY")
        print(f"=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%" if self.test_results else "0%")
        
        if failed > 0:
            print(f"\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}: {result['message']}")
        else:
            print(f"\n🎉 ALL SSH AUTHENTICATION FIXES VERIFIED!")
        
        print(f"\n" + "=" * 60)

async def main():
    """Main test runner"""
    tester = SSHFixTester()
    await tester.run_ssh_fix_tests()

if __name__ == "__main__":
    asyncio.run(main())