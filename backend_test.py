#!/usr/bin/env python3
"""
Backend API Testing for JobTalk Admin Dashboard
Tests SSH authentication changes and partner configuration
"""

import asyncio
import aiohttp
import json
import os
import sys
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

class BackendTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.mongo_client = None
        self.db = None
        self.test_results = []
        self.created_partners = []  # Track created partners for cleanup
        
    async def setup(self):
        """Initialize test session and database connection"""
        print(f"🔧 Setting up test environment...")
        print(f"Backend URL: {API_BASE}")
        print(f"MongoDB URL: {MONGO_URL}")
        
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
                self.created_partners.append(data["id"])  # Track for cleanup
                return data
            else:
                error_text = await response.text()
                raise Exception(f"Partner creation failed: {response.status} - {error_text}")
    
    async def get_partner(self, partner_id):
        """Get partner by ID"""
        async with self.session.get(
            f"{API_BASE}/partners/{partner_id}", 
            headers=self.get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Get partner failed: {response.status} - {error_text}")
    
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
    
    async def test_create_partner_ssh_password_only(self):
        """Test 1: Create Partner with SSH Password Only"""
        print(f"\n🧪 Test 1: Create Partner with SSH Password Only")
        
        partner_data = {
            "partnerName": f"TestPartner_PWD_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 1,
            "dbHost": "test-db.example.com",
            "dbPort": 3306,
            "dbName": "test_db",
            "dbUsername": "test_user",
            "dbPassword": "test_db_password",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh.example.com",
                "port": 22,
                "username": "ssh_user",
                "password": "ssh_test_password_123",
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
            
            # Verify partner was created
            if created_partner["partnerName"] == partner_data["partnerName"]:
                self.log_result("create_ssh_password", True, "Partner created successfully with SSH password")
            else:
                self.log_result("create_ssh_password", False, "Partner data mismatch after creation")
                return
            
            # Check database encryption
            db_partner = await self.get_partner_from_db(partner_id)
            if db_partner:
                ssh_password = db_partner["sshConfig"]["password"]
                if ssh_password and ssh_password != "ssh_test_password_123":
                    self.log_result("ssh_password_encryption", True, "SSH password is encrypted in database")
                else:
                    self.log_result("ssh_password_encryption", False, f"SSH password not encrypted: {ssh_password}")
                
                # Verify private key is None/empty
                private_key = db_partner["sshConfig"].get("privateKey")
                if not private_key:
                    self.log_result("ssh_no_private_key", True, "Private key correctly empty when using password auth")
                else:
                    self.log_result("ssh_no_private_key", False, f"Private key should be empty: {private_key}")
            else:
                self.log_result("db_verification", False, "Could not retrieve partner from database")
                
        except Exception as e:
            self.log_result("create_ssh_password", False, f"Test failed: {str(e)}")
    
    async def test_create_partner_ssh_key_only(self):
        """Test 2: Create Partner with SSH Private Key Only"""
        print(f"\n🧪 Test 2: Create Partner with SSH Private Key Only")
        
        test_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""
        
        partner_data = {
            "partnerName": f"TestPartner_KEY_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 2,
            "dbHost": "test-db2.example.com",
            "dbPort": 3306,
            "dbName": "test_db2",
            "dbUsername": "test_user2",
            "dbPassword": "test_db_password2",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh2.example.com",
                "port": 22,
                "username": "ssh_user2",
                "password": None,
                "privateKey": test_private_key,
                "passphrase": "key_passphrase_123"
            },
            "concurrencyLimit": 15,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Verify partner was created
            if created_partner["partnerName"] == partner_data["partnerName"]:
                self.log_result("create_ssh_key", True, "Partner created successfully with SSH private key")
            else:
                self.log_result("create_ssh_key", False, "Partner data mismatch after creation")
                return
            
            # Check database encryption
            db_partner = await self.get_partner_from_db(partner_id)
            if db_partner:
                private_key = db_partner["sshConfig"]["privateKey"]
                if private_key and private_key != test_private_key:
                    self.log_result("ssh_key_encryption", True, "SSH private key is encrypted in database")
                else:
                    self.log_result("ssh_key_encryption", False, f"SSH private key not encrypted")
                
                passphrase = db_partner["sshConfig"]["passphrase"]
                if passphrase and passphrase != "key_passphrase_123":
                    self.log_result("ssh_passphrase_encryption", True, "SSH passphrase is encrypted in database")
                else:
                    self.log_result("ssh_passphrase_encryption", False, f"SSH passphrase not encrypted")
                
                # Verify password is None/empty
                password = db_partner["sshConfig"].get("password")
                if not password:
                    self.log_result("ssh_no_password", True, "SSH password correctly empty when using key auth")
                else:
                    self.log_result("ssh_no_password", False, f"SSH password should be empty: {password}")
            else:
                self.log_result("db_verification", False, "Could not retrieve partner from database")
                
        except Exception as e:
            self.log_result("create_ssh_key", False, f"Test failed: {str(e)}")
    
    async def test_validation_no_ssh_credentials(self):
        """Test 3: Validation Test - No SSH Credentials"""
        print(f"\n🧪 Test 3: Validation Test - No SSH Credentials")
        
        partner_data = {
            "partnerName": f"TestPartner_INVALID_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 3,
            "dbHost": "test-db3.example.com",
            "dbPort": 3306,
            "dbName": "test_db3",
            "dbUsername": "test_user3",
            "dbPassword": "test_db_password3",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh3.example.com",
                "port": 22,
                "username": "ssh_user3",
                "password": None,  # No password
                "privateKey": None,  # No private key
                "passphrase": None
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # This should fail validation
            created_partner = await self.create_partner(partner_data)
            # If we get here, validation failed
            self.log_result("validation_no_credentials", False, "Partner created without SSH credentials - validation failed")
            
        except Exception as e:
            # This is expected - should fail
            error_msg = str(e).lower()
            if "validation" in error_msg or "password" in error_msg or "key" in error_msg or "400" in error_msg:
                self.log_result("validation_no_credentials", True, "Correctly rejected partner without SSH credentials")
            else:
                self.log_result("validation_no_credentials", False, f"Unexpected error: {str(e)}")
    
    async def test_edit_partner_no_double_encryption(self):
        """Test 4: Edit Partner - Verify No Double Encryption"""
        print(f"\n🧪 Test 4: Edit Partner - Verify No Double Encryption")
        
        # First create a partner
        partner_data = {
            "partnerName": f"TestPartner_EDIT_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 4,
            "dbHost": "test-db4.example.com",
            "dbPort": 3306,
            "dbName": "test_db4",
            "dbUsername": "test_user4",
            "dbPassword": "test_db_password4",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh4.example.com",
                "port": 22,
                "username": "ssh_user4",
                "password": "original_ssh_password",
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
            
            # Get original encrypted password from DB
            original_db_partner = await self.get_partner_from_db(partner_id)
            original_encrypted_password = original_db_partner["sshConfig"]["password"]
            
            # Update partner without changing SSH credentials (should not double-encrypt)
            update_data = {
                "partnerName": f"Updated_{partner_data['partnerName']}",
                "concurrencyLimit": 20
                # Note: Not including sshConfig to test no double encryption
            }
            
            updated_partner = await self.update_partner(partner_id, update_data)
            
            # Check that SSH password remains the same (not double-encrypted)
            updated_db_partner = await self.get_partner_from_db(partner_id)
            updated_encrypted_password = updated_db_partner["sshConfig"]["password"]
            
            if original_encrypted_password == updated_encrypted_password:
                self.log_result("no_double_encryption", True, "SSH password not double-encrypted during update")
            else:
                self.log_result("no_double_encryption", False, "SSH password was double-encrypted during update")
            
            # Verify other fields were updated
            if updated_db_partner["partnerName"] == update_data["partnerName"]:
                self.log_result("update_other_fields", True, "Other fields updated correctly")
            else:
                self.log_result("update_other_fields", False, "Other fields not updated correctly")
                
        except Exception as e:
            self.log_result("edit_no_double_encryption", False, f"Test failed: {str(e)}")
    
    async def test_edit_partner_update_ssh_password_only(self):
        """Test 5: Edit Partner - Update SSH Password Only"""
        print(f"\n🧪 Test 5: Edit Partner - Update SSH Password Only")
        
        # First create a partner with both password and key
        test_private_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""
        
        partner_data = {
            "partnerName": f"TestPartner_UPDATE_{datetime.now().strftime('%H%M%S')}",
            "tenantId": 5,
            "dbHost": "test-db5.example.com",
            "dbPort": 3306,
            "dbName": "test_db5",
            "dbUsername": "test_user5",
            "dbPassword": "test_db_password5",
            "dbType": "mysql",
            "sshConfig": {
                "enabled": True,
                "host": "ssh5.example.com",
                "port": 22,
                "username": "ssh_user5",
                "password": "original_password",
                "privateKey": test_private_key,
                "passphrase": "original_passphrase"
            },
            "concurrencyLimit": 10,
            "isActive": True
        }
        
        try:
            # Create partner
            created_partner = await self.create_partner(partner_data)
            partner_id = created_partner["id"]
            
            # Get original encrypted values from DB
            original_db_partner = await self.get_partner_from_db(partner_id)
            original_encrypted_key = original_db_partner["sshConfig"]["privateKey"]
            original_encrypted_passphrase = original_db_partner["sshConfig"]["passphrase"]
            
            # Update only SSH password
            update_data = {
                "sshConfig": {
                    "enabled": True,
                    "host": "ssh5.example.com",
                    "port": 22,
                    "username": "ssh_user5",
                    "password": "new_updated_password",
                    # Not including privateKey and passphrase to test they remain unchanged
                }
            }
            
            updated_partner = await self.update_partner(partner_id, update_data)
            
            # Check database state
            updated_db_partner = await self.get_partner_from_db(partner_id)
            
            # Verify new password is encrypted and different
            new_encrypted_password = updated_db_partner["sshConfig"]["password"]
            if new_encrypted_password and new_encrypted_password != "new_updated_password":
                self.log_result("new_password_encrypted", True, "New SSH password is encrypted")
            else:
                self.log_result("new_password_encrypted", False, "New SSH password not encrypted")
            
            # Verify private key and passphrase remain unchanged
            current_encrypted_key = updated_db_partner["sshConfig"].get("privateKey")
            current_encrypted_passphrase = updated_db_partner["sshConfig"].get("passphrase")
            
            if current_encrypted_key == original_encrypted_key:
                self.log_result("key_unchanged", True, "SSH private key remained unchanged")
            else:
                self.log_result("key_unchanged", False, "SSH private key was modified unexpectedly")
            
            if current_encrypted_passphrase == original_encrypted_passphrase:
                self.log_result("passphrase_unchanged", True, "SSH passphrase remained unchanged")
            else:
                self.log_result("passphrase_unchanged", False, "SSH passphrase was modified unexpectedly")
                
        except Exception as e:
            self.log_result("edit_update_password", False, f"Test failed: {str(e)}")
    
    async def test_backend_encryption_verification(self):
        """Test 6: Backend Encryption Verification"""
        print(f"\n🧪 Test 6: Backend Encryption Verification")
        
        try:
            # Query all partners from database
            partners = await self.db.partner_configs.find({}, {"_id": 0}).to_list(1000)
            
            encrypted_count = 0
            plaintext_count = 0
            
            for partner in partners:
                ssh_config = partner.get("sshConfig", {})
                
                # Check SSH password
                password = ssh_config.get("password")
                if password:
                    # Check if it looks encrypted (base64-like, not plaintext)
                    if len(password) > 20 and not any(word in password.lower() for word in ["password", "test", "admin", "123"]):
                        encrypted_count += 1
                    else:
                        plaintext_count += 1
                        print(f"   ⚠️  Found potential plaintext password in partner {partner.get('partnerName', 'Unknown')}")
                
                # Check SSH private key
                private_key = ssh_config.get("privateKey")
                if private_key:
                    # Private keys should be encrypted (not start with -----BEGIN)
                    if not private_key.startswith("-----BEGIN"):
                        encrypted_count += 1
                    else:
                        plaintext_count += 1
                        print(f"   ⚠️  Found potential plaintext private key in partner {partner.get('partnerName', 'Unknown')}")
                
                # Check SSH passphrase
                passphrase = ssh_config.get("passphrase")
                if passphrase:
                    # Check if it looks encrypted
                    if len(passphrase) > 20 and not any(word in passphrase.lower() for word in ["passphrase", "test", "admin", "123"]):
                        encrypted_count += 1
                    else:
                        plaintext_count += 1
                        print(f"   ⚠️  Found potential plaintext passphrase in partner {partner.get('partnerName', 'Unknown')}")
            
            if plaintext_count == 0:
                self.log_result("encryption_verification", True, f"All SSH credentials appear encrypted ({encrypted_count} encrypted fields found)")
            else:
                self.log_result("encryption_verification", False, f"Found {plaintext_count} potentially unencrypted fields")
                
        except Exception as e:
            self.log_result("encryption_verification", False, f"Test failed: {str(e)}")
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        print(f"🚀 Starting JobTalk Admin Dashboard Backend Tests")
        print(f"=" * 60)
        
        try:
            await self.setup()
            
            # Run all test scenarios
            await self.test_create_partner_ssh_password_only()
            await self.test_create_partner_ssh_key_only()
            await self.test_validation_no_ssh_credentials()
            await self.test_edit_partner_no_double_encryption()
            await self.test_edit_partner_update_ssh_password_only()
            await self.test_backend_encryption_verification()
            
        finally:
            await self.cleanup()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print(f"\n" + "=" * 60)
        print(f"📊 TEST RESULTS SUMMARY")
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
        
        print(f"\n" + "=" * 60)

async def main():
    """Main test runner"""
    tester = BackendTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())