from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext

from models import *
from services.encryption import EncryptionService
from services.ssh_connection import SSHConnectionService
from services.data_fetch import DataFetchService
from services.concurrency import ConcurrencyService
from services.alert import AlertService
from services.email_service import EmailService

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 8))

# Security
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(
    title="JobTalk Admin Dashboard API",
    description="""
    ## JobTalk Admin Dashboard API
    
    Complete API for managing partners, monitoring call campaigns, and tracking metrics.
    
    ### Features:
    * **Partner Management** - Create, update, and manage partner configurations
    * **Real-time Metrics** - Monitor campaigns, calls, and submittals
    * **SSH Tunneling** - Secure connections to partner databases
    * **Period Statistics** - Analyze data over custom date ranges
    * **Concurrency Control** - Manage call concurrency limits
    * **Authentication** - JWT-based secure authentication
    
    ### Authentication:
    All endpoints require JWT authentication. Obtain a token by calling `/api/auth/login`.
    
    Add the token to requests using the Authorization header:
    ```
    Authorization: Bearer <your_token>
    ```
    
    ### Documentation:
    - **Swagger UI**: Available at `/docs` (this page)
    - **ReDoc**: Available at `/redoc`
    - **Markdown Docs**: See `/app/API_DOCUMENTATION.md`
    """,
    version="1.0.0",
    contact={
        "name": "JobTalk Admin Support",
        "email": "support@jobtalk.com"
    },
    license_info={
        "name": "Proprietary"
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize services
encryption_service = EncryptionService()
ssh_service = SSHConnectionService(db, encryption_service)
concurrency_service = ConcurrencyService(db, ssh_service)
email_service = EmailService()
alert_service = AlertService(db, email_service)
data_fetch_service = DataFetchService(db, ssh_service, alert_service)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user_data = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user_data is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return User(**user_data)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# ============= Authentication Routes =============
@api_router.post(
    "/auth/register",
    response_model=User,
    tags=["Authentication"],
    summary="Register new user",
    description="""
    Register a new user account.
    
    **Requirements:**
    - Username must be unique
    - Email must be unique and valid
    - Password will be securely hashed before storage
    
    **Returns:**
    - User object with generated UUID
    - Password hash is not included in response
    
    **Note:** This endpoint does not require authentication.
    """
)
async def register(user_input: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"username": user_input.username}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    existing_email = await db.users.find_one({"email": user_input.email}, {"_id": 0})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create user
    user = User(
        username=user_input.username,
        email=user_input.email,
        role=user_input.role
    )
    
    user_dict = user.model_dump()
    user_dict['passwordHash'] = hash_password(user_input.password)
    user_dict['createdAt'] = user_dict['createdAt'].isoformat()
    user_dict['updatedAt'] = user_dict['updatedAt'].isoformat()
    
    await db.users.insert_one(user_dict)
    return user

@api_router.post(
    "/auth/login",
    response_model=Token,
    tags=["Authentication"],
    summary="User login",
    description="""
    Authenticate user and obtain JWT access token.
    
    **Process:**
    1. Validates username and password
    2. Updates user's last login timestamp
    3. Generates JWT token (valid for 8 hours by default)
    
    **Returns:**
    - Access token (JWT)
    - Token type ("bearer")
    - User object
    
    **Usage:**
    Use the returned token in subsequent requests:
    ```
    Authorization: Bearer <access_token>
    ```
    """
)
async def login(credentials: UserLogin):
    user_data = await db.users.find_one({"username": credentials.username}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user_data['passwordHash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    await db.users.update_one(
        {"id": user_data['id']},
        {"$set": {"lastLogin": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create token
    access_token = create_access_token({"sub": user_data['id']})
    
    user = User(**user_data)
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get(
    "/auth/me",
    response_model=User,
    tags=["Authentication"],
    summary="Get current user",
    description="""
    Retrieve the currently authenticated user's information.
    
    **Authentication Required:** Yes
    
    **Returns:**
    - Complete user profile
    - Last login timestamp
    - User role and permissions
    """
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post(
    "/auth/logout",
    tags=["Authentication"],
    summary="User logout",
    description="""
    Logout the current user.
    
    **Authentication Required:** Yes
    
    **Note:** Since JWT tokens are stateless, client must discard the token.
    The server acknowledges the logout but cannot invalidate the token.
    """
)
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

@api_router.post(
    "/auth/change-password",
    tags=["Authentication"],
    summary="Change password",
    description="""
    Change the current user's password.
    
    **Authentication Required:** Yes
    
    **Request Body:**
    ```json
    {
        "currentPassword": "your_current_password",
        "newPassword": "your_new_password"
    }
    ```
    
    **Process:**
    1. Verifies current password
    2. Hashes new password securely
    3. Updates password in database
    4. Updates user's updatedAt timestamp
    
    **Security:**
    - Current password must be correct
    - New password is hashed using bcrypt
    """
)
async def change_password(
    password_change: dict,
    current_user: User = Depends(get_current_user)
):
    current_password = password_change.get('currentPassword')
    new_password = password_change.get('newPassword')
    
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password required")
    
    # Verify current password
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash new password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password": hashed_password, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Password changed successfully"}

# ============= Partner Management Routes =============
@api_router.get(
    "/partners",
    response_model=List[PartnerConfig],
    tags=["Partner Management"],
    summary="Get all partners",
    description="""
    Retrieve a list of all partner configurations.
    
    **Authentication Required:** Yes
    
    **Returns:**
    - List of all partners with their configurations
    - Includes database connection details
    - SSH configuration (credentials are encrypted)
    - Active/inactive status
    
    **Note:** Sensitive fields (passwords, SSH keys) are returned encrypted.
    """
)
async def get_partners(current_user: User = Depends(get_current_user)):
    partners = await db.partner_configs.find({}, {"_id": 0}).to_list(1000)
    return partners

@api_router.post(
    "/partners",
    response_model=PartnerConfig,
    tags=["Partner Management"],
    summary="Create new partner",
    description="""
    Create a new partner configuration with database and SSH settings.
    
    **Authentication Required:** Yes
    
    **Validations:**
    - Partner name must be unique
    - If SSH is enabled, must provide either password OR private key
    - Database connection details are required
    
    **Security:**
    - Database password is encrypted before storage
    - SSH credentials (password, private key, passphrase) are encrypted
    - All sensitive data uses AES-256-CBC encryption
    
    **Returns:**
    - Created partner configuration
    - Generated UUID
    - Timestamps (createdAt, updatedAt)
    """
)
async def create_partner(partner_input: PartnerConfigCreate, current_user: User = Depends(get_current_user)):
    # Check if partner name exists
    existing = await db.partner_configs.find_one({"partnerName": partner_input.partnerName}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Partner name already exists")
    
    # Validate SSH configuration if enabled
    if partner_input.sshConfig.enabled:
        has_password = partner_input.sshConfig.password and partner_input.sshConfig.password.strip() != ''
        has_private_key = partner_input.sshConfig.privateKey and partner_input.sshConfig.privateKey.strip() != ''
        
        if not has_password and not has_private_key:
            raise HTTPException(
                status_code=400, 
                detail="SSH is enabled but no authentication method provided. Please provide either SSH password or SSH private key."
            )
    
    # Create partner
    partner = PartnerConfig(**partner_input.model_dump())
    
    # Encrypt sensitive data
    partner_dict = partner.model_dump()
    partner_dict['dbPassword'] = encryption_service.encrypt(partner_input.dbPassword)
    if partner_input.sshConfig.password:
        partner_dict['sshConfig']['password'] = encryption_service.encrypt(partner_input.sshConfig.password)
    if partner_input.sshConfig.privateKey:
        partner_dict['sshConfig']['privateKey'] = encryption_service.encrypt(partner_input.sshConfig.privateKey)
    if partner_input.sshConfig.passphrase:
        partner_dict['sshConfig']['passphrase'] = encryption_service.encrypt(partner_input.sshConfig.passphrase)
    
    partner_dict['createdAt'] = partner_dict['createdAt'].isoformat()
    partner_dict['updatedAt'] = partner_dict['updatedAt'].isoformat()
    if partner_dict.get('lastSyncAt'):
        partner_dict['lastSyncAt'] = partner_dict['lastSyncAt'].isoformat()
    
    await db.partner_configs.insert_one(partner_dict)
    return partner

@api_router.get(
    "/partners/{partner_id}",
    response_model=PartnerConfig,
    tags=["Partner Management"],
    summary="Get partner by ID",
    description="""
    Retrieve detailed configuration for a specific partner.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - partner_id: UUID of the partner
    
    **Returns:**
    - Complete partner configuration
    - Encrypted sensitive fields
    
    **Errors:**
    - 404: Partner not found
    """
)
async def get_partner(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerConfig(**partner_data)

@api_router.put(
    "/partners/{partner_id}",
    response_model=PartnerConfig,
    tags=["Partner Management"],
    summary="Update partner",
    description="""
    Update an existing partner's configuration.
    
    **Authentication Required:** Yes
    
    **Special Handling:**
    - Partial updates supported (only send fields to update)
    - SSH credentials are merged, not replaced
    - Empty SSH fields preserve existing encrypted values
    - Prevents double encryption of credentials
    
    **Security:**
    - New credentials are encrypted before storage
    - Existing encrypted credentials preserved during partial updates
    
    **Returns:**
    - Updated partner configuration
    
    **Errors:**
    - 404: Partner not found
    """
)
async def update_partner(partner_id: str, partner_update: PartnerConfigUpdate, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    update_dict = partner_update.model_dump(exclude_unset=True)
    
    # Encrypt sensitive fields if provided
    if 'dbPassword' in update_dict and update_dict['dbPassword']:
        update_dict['dbPassword'] = encryption_service.encrypt(update_dict['dbPassword'])
    
    # Handle SSH config updates carefully - merge with existing config to avoid losing credentials
    if 'sshConfig' in update_dict:
        existing_ssh = partner_data.get('sshConfig', {})
        updated_ssh = update_dict['sshConfig']
        
        # Encrypt new credentials if provided
        if updated_ssh.get('password'):
            updated_ssh['password'] = encryption_service.encrypt(updated_ssh['password'])
        if updated_ssh.get('privateKey'):
            updated_ssh['privateKey'] = encryption_service.encrypt(updated_ssh['privateKey'])
        if updated_ssh.get('passphrase'):
            updated_ssh['passphrase'] = encryption_service.encrypt(updated_ssh['passphrase'])
        
        # Merge: keep existing encrypted credentials if not provided in update
        merged_ssh = existing_ssh.copy()
        for key, value in updated_ssh.items():
            # Only update if value is not None and not empty string
            if value is not None and value != '':
                merged_ssh[key] = value
        
        update_dict['sshConfig'] = merged_ssh
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.partner_configs.update_one({"id": partner_id}, {"$set": update_dict})
    
    updated_partner = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    return PartnerConfig(**updated_partner)

@api_router.delete(
    "/partners/{partner_id}",
    tags=["Partner Management"],
    summary="Delete partner",
    description="""
    Permanently delete a partner configuration.
    
    **Authentication Required:** Yes
    
    **Warning:** This action is irreversible.
    
    **Errors:**
    - 404: Partner not found
    """
)
async def delete_partner(partner_id: str, current_user: User = Depends(get_current_user)):
    result = await db.partner_configs.delete_one({"id": partner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"message": "Partner deleted successfully"}

@api_router.post(
    "/partners/{partner_id}/test",
    response_model=TestConnectionResponse,
    tags=["Partner Management"],
    summary="Test partner connection",
    description="""
    Test SSH tunnel and database connection for a partner.
    
    **Authentication Required:** Yes
    
    **Process:**
    1. Establishes SSH tunnel (if enabled)
    2. Connects to partner's MySQL database
    3. Executes simple test query
    4. Records result in connection logs
    
    **Returns:**
    - Connection status (success/failure)
    - Response time in milliseconds
    - Error message (if failed)
    
    **Use Cases:**
    - Validate new partner configuration
    - Troubleshoot connection issues
    - Verify SSH credentials
    """
)
async def test_connection(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    result = await ssh_service.test_connection(partner)
    return result

@api_router.get(
    "/partners/{partner_id}/logs",
    response_model=List[ConnectionLog],
    tags=["Partner Management"],
    summary="Get connection logs",
    description="""
    Retrieve connection logs for a partner.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - partner_id: UUID of the partner
    - limit: Maximum number of logs to return (default: 50)
    
    **Returns:**
    - List of connection logs (most recent first)
    - Each log contains timestamp, status, and error details
    
    **Use Cases:**
    - Debug connection issues
    - Monitor connection health
    - Audit connection attempts
    """
)
async def get_partner_logs(partner_id: str, limit: int = 50, current_user: User = Depends(get_current_user)):
    logs = await db.connection_logs.find({"partnerId": partner_id}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

@api_router.delete(
    "/partners/{partner_id}/logs",
    tags=["Partner Management"],
    summary="Clear connection logs",
    description="""
    Delete all connection logs for a specific partner.
    
    **Authentication Required:** Yes
    
    **Use Cases:**
    - Clean up old logs
    - Free database space
    - Reset logging history
    
    **Returns:**
    - Count of deleted logs
    """
)
async def clear_partner_logs(partner_id: str, current_user: User = Depends(get_current_user)):
    result = await db.connection_logs.delete_many({"partnerId": partner_id})
    return {"message": f"Deleted {result.deleted_count} connection logs"}

@api_router.get(
    "/partners/{partner_id}/history",
    response_model=List[ConcurrencyHistory],
    tags=["Partner Management"],
    summary="Get concurrency change history",
    description="""
    Retrieve history of concurrency limit changes for a partner.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - partner_id: UUID of the partner
    - limit: Maximum number of history records (default: 20)
    
    **Returns:**
    - List of concurrency changes (most recent first)
    - Each record includes old/new values, reason, and who made the change
    
    **Use Cases:**
    - Audit concurrency adjustments
    - Track performance tuning
    - Review administrative changes
    """
)
async def get_concurrency_history(partner_id: str, limit: int = 20, current_user: User = Depends(get_current_user)):
    history = await db.concurrency_history.find({"partnerId": partner_id}, {"_id": 0}).sort("changedAt", -1).limit(limit).to_list(limit)
    return history

@api_router.post(
    "/partners/{partner_id}/force-sync",
    tags=["Partner Management"],
    summary="Force data sync",
    description="""
    Manually trigger immediate data fetch for a partner.
    
    **Authentication Required:** Yes
    
    **Process:**
    1. Bypasses automatic sync schedule
    2. Connects to partner database
    3. Fetches current metrics
    4. Updates dashboard snapshot
    
    **Use Cases:**
    - Get latest data immediately
    - Verify recent changes
    - Troubleshoot sync issues
    
    **Note:** Respects connection timeout settings
    """
)
async def force_sync(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    await data_fetch_service.fetch_partner_data(partner)
    return {"message": "Sync initiated successfully"}

# ============= Dashboard Routes =============
@api_router.get(
    "/dashboard/overview",
    response_model=DashboardOverview,
    tags=["Dashboard"],
    summary="Get dashboard overview",
    description="""
    Retrieve aggregated metrics across all partners.
    
    **Authentication Required:** Yes
    
    **Metrics Included:**
    - Total campaigns today
    - Running campaigns
    - Active calls
    - Queued calls
    - Completed calls today
    - Remaining calls
    - Total and active partner count
    - Average utilization percentage
    
    **Data Source:**
    - Aggregates latest snapshots from all partners
    - Real-time calculation from most recent sync
    
    **Use Cases:**
    - Main dashboard view
    - High-level monitoring
    - Quick health check
    """
)
async def get_dashboard_overview(current_user: User = Depends(get_current_user)):
    # Get all partners
    partners = await db.partner_configs.find({}, {"_id": 0}).to_list(1000)
    
    # Get latest snapshots
    pipeline = [
        {"$sort": {"snapshotTime": -1}},
        {"$group": {
            "_id": "$partnerId",
            "latest": {"$first": "$$ROOT"}
        }}
    ]
    snapshots = await db.dashboard_snapshots.aggregate(pipeline).to_list(1000)
    
    total_campaigns_today = sum(s['latest']['campaignsToday'] for s in snapshots)
    total_running_campaigns = sum(s['latest']['runningCampaigns'] for s in snapshots)
    total_active_calls = sum(s['latest']['activeCalls'] for s in snapshots)
    total_queued_calls = sum(s['latest']['queuedCalls'] for s in snapshots)
    total_completed_calls_today = sum(s['latest'].get('completedCallsToday', 0) for s in snapshots)
    total_remaining_calls = sum(s['latest'].get('remainingCalls', 0) for s in snapshots)
    
    active_partners = sum(1 for p in partners if p.get('isActive', True))
    avg_utilization = sum(s['latest']['utilizationPercent'] for s in snapshots) / len(snapshots) if snapshots else 0
    
    return DashboardOverview(
        campaignsToday=total_campaigns_today,
        runningCampaigns=total_running_campaigns,
        activeCalls=total_active_calls,
        queuedCalls=total_queued_calls,
        completedCallsToday=total_completed_calls_today,
        remainingCalls=total_remaining_calls,
        totalPartners=len(partners),
        activePartners=active_partners,
        avgUtilization=avg_utilization,
        lastUpdated=datetime.now(timezone.utc)
    )

@api_router.get(
    "/dashboard/partners",
    response_model=List[PartnerDashboardData],
    tags=["Dashboard"],
    summary="Get partner dashboard data",
    description="""
    Retrieve dashboard data for all partners with their latest metrics.
    
    **Authentication Required:** Yes
    
    **Returns:**
    - List of partners with their latest snapshot data
    - Partner configuration details
    - Current metrics (calls, campaigns, utilization)
    - Alert levels and messages
    
    **Data Structure:**
    Each entry contains:
    - partner: Complete partner configuration
    - snapshot: Latest metrics snapshot (null if no data yet)
    
    **Use Cases:**
    - Display partner list on dashboard
    - Show per-partner metrics
    - Monitor individual partner health
    """
)
async def get_dashboard_partners(current_user: User = Depends(get_current_user)):
    partners = await db.partner_configs.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for partner in partners:
        snapshot = await db.dashboard_snapshots.find_one(
            {"partnerId": partner['id']},
            {"_id": 0}
        , sort=[("snapshotTime", -1)])
        
        result.append(PartnerDashboardData(
            partner=PartnerConfig(**partner),
            snapshot=DashboardSnapshot(**snapshot) if snapshot else None
        ))
    
    return result

@api_router.post(
    "/dashboard/refresh",
    tags=["Dashboard"],
    summary="Refresh all dashboard data",
    description="""
    Trigger immediate data refresh for all active partners.
    
    **Authentication Required:** Yes
    
    **Process:**
    1. Iterates through all active partners
    2. Fetches latest metrics from each partner database
    3. Updates dashboard snapshots
    4. Processes alerts if thresholds exceeded
    
    **Performance:**
    - Executes partners in batches (respects concurrentPartnerLimit setting)
    - May take several seconds for multiple partners
    
    **Use Cases:**
    - Manual refresh button
    - On-demand data update
    - After configuration changes
    """
)
async def refresh_dashboard(current_user: User = Depends(get_current_user)):
    await data_fetch_service.fetch_all_partners()
    return {"message": "Dashboard refresh completed"}

# ============= Concurrency Management Routes =============
@api_router.post(
    "/partners/{partner_id}/concurrency",
    tags=["Concurrency Management"],
    summary="Update partner concurrency",
    description="""
    Update call concurrency limit for a specific partner (dashboard inline edit).
    
    **Authentication Required:** Yes
    
    **Request Body:**
    ```json
    {
        "newLimit": 50,
        "reason": "Increased due to high queue volume"
    }
    ```
    
    **Process:**
    1. Validates new limit
    2. Updates MongoDB admin database
    3. Updates partner's MySQL database settings table
    4. Records change in concurrency history
    5. Creates audit log in partner database
    
    **Returns:**
    - Success status
    - Old and new limit values
    - Sync status (whether partner DB was updated)
    
    **Use Cases:**
    - Quick concurrency adjustment from dashboard
    - Performance tuning
    - Managing call capacity
    """
)
async def update_partner_concurrency(partner_id: str, update: ConcurrencyUpdate, current_user: User = Depends(get_current_user)):
    result = await concurrency_service.update_concurrency(
        partner_id,
        update.newLimit,
        update.reason,
        current_user.id
    )
    return result

@api_router.post(
    "/partners/{partner_id}/pause-non-priority",
    tags=["Concurrency Management"],
    summary="Toggle pause non-priority campaigns",
    description="""
    Enable or disable pausing of non-priority campaigns for a partner.
    
    **Authentication Required:** Yes
    
    **Request Body:**
    ```json
    {
        "enabled": true
    }
    ```
    
    **Process:**
    1. Updates MongoDB admin database
    2. Updates partner's MySQL settings table
    3. Records change in settings_auditlogs table
    
    **Returns:**
    - Success status
    - Sync status (whether partner DB was updated)
    - Error details (if sync failed)
    
    **Use Cases:**
    - Prioritize high-value campaigns
    - Manage system load
    - Emergency capacity management
    
    **Note:** If partner database sync fails, setting is still saved in admin DB.
    """
)
async def toggle_pause_non_priority(partner_id: str, toggle: dict, current_user: User = Depends(get_current_user)):
    enabled = toggle.get('enabled', False)
    
    # Get partner
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    
    # Update in admin MongoDB
    await db.partner_configs.update_one(
        {"id": partner_id},
        {"$set": {"pauseNonPriorityCampaigns": enabled, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Update in partner's MySQL database and add audit log
    try:
        # Get old value for audit
        get_old_query = "SELECT value FROM settings WHERE name = 'pauseNonPriorityCampaigns'"
        old_result = await ssh_service.execute_query(partner, get_old_query)
        old_value = old_result[0]['value'] if old_result and len(old_result) > 0 else 'false'
        
        # Update setting in partner database
        update_query = "UPDATE settings SET value = %s WHERE name = 'pauseNonPriorityCampaigns'"
        await ssh_service.execute_update(partner, update_query, ('true' if enabled else 'false',))
        
        # Insert audit log
        audit_query = """
            INSERT INTO settings_auditlogs (userid, oldvalue, newvalue, createdat)
            VALUES (9999999999, %s, %s, NOW())
        """
        await ssh_service.execute_update(partner, audit_query, (old_value, 'true' if enabled else 'false'))
        
        return {
            "success": True,
            "message": f"pauseNonPriorityCampaigns {'enabled' if enabled else 'disabled'}",
            "syncedToPartner": True
        }
    except Exception as e:
        logger.error(f"Error syncing pauseNonPriorityCampaigns to partner database: {str(e)}")
        return {
            "success": True,
            "message": f"pauseNonPriorityCampaigns {'enabled' if enabled else 'disabled'} in admin only",
            "syncedToPartner": False,
            "syncError": str(e)
        }

@api_router.put(
    "/concurrency/{partner_id}",
    tags=["Concurrency Management"],
    summary="Update concurrency (alternative endpoint)",
    description="""
    Update call concurrency limit for a partner (alternative PUT endpoint).
    
    **Authentication Required:** Yes
    
    **Note:** This is an alternative to POST /partners/{partner_id}/concurrency.
    Functionality is identical.
    
    See POST /partners/{partner_id}/concurrency for detailed documentation.
    """
)
async def update_concurrency(partner_id: str, update: ConcurrencyUpdate, current_user: User = Depends(get_current_user)):
    result = await concurrency_service.update_concurrency(
        partner_id,
        update.newLimit,
        update.reason,
        current_user.id
    )
    return result

@api_router.put(
    "/concurrency/bulk",
    tags=["Concurrency Management"],
    summary="Bulk update concurrency",
    description="""
    Update concurrency limit for multiple partners at once.
    
    **Authentication Required:** Yes
    
    **Request Body:**
    ```json
    {
        "partnerIds": ["uuid1", "uuid2", "uuid3"],
        "newLimit": 50,
        "reason": "Bulk adjustment for system optimization"
    }
    ```
    
    **Process:**
    - Applies same limit to all specified partners
    - Updates both admin and partner databases
    - Records individual history for each partner
    
    **Returns:**
    - Array of results (one per partner)
    - Each result contains success/failure status
    
    **Use Cases:**
    - System-wide capacity adjustment
    - Emergency scaling
    - Batch configuration updates
    """
)
async def bulk_update_concurrency(update: BulkConcurrencyUpdate, current_user: User = Depends(get_current_user)):
    results = []
    for partner_id in update.partnerIds:
        result = await concurrency_service.update_concurrency(
            partner_id,
            update.newLimit,
            update.reason,
            current_user.id
        )
        results.append(result)
    return {"results": results}

@api_router.post(
    "/concurrency/calculate",
    tags=["Concurrency Management"],
    summary="Calculate suggested concurrency",
    description="""
    Calculate AI-suggested concurrency limit based on current metrics.
    
    **Authentication Required:** Yes
    
    **Algorithm:**
    - Analyzes queued calls, running campaigns, and active calls
    - Calculates multiple suggestions using different formulas
    - Returns the maximum (capped between 5-100)
    
    **Formulas:**
    1. queued_calls / 20
    2. running_campaigns / 3
    3. active_calls + (queued_calls / 50)
    
    **Returns:**
    - Suggested limit value
    - Reasoning explanation
    
    **Use Cases:**
    - Smart concurrency optimization
    - Decision support for admins
    - Automated scaling recommendations
    
    **Note:** Returns default of 10 if no data available.
    """
)
async def calculate_suggested_concurrency(partner_id: str, current_user: User = Depends(get_current_user)):
    snapshot = await db.dashboard_snapshots.find_one(
        {"partnerId": partner_id},
        {"_id": 0},
        sort=[("snapshotTime", -1)]
    )
    
    if not snapshot:
        return {"suggested": 10, "reason": "No data available, using default"}
    
    queued = snapshot['queuedCalls']
    running = snapshot['runningCampaigns']
    active = snapshot['activeCalls']
    
    suggestions = [
        queued // 20,
        running // 3,
        active + (queued // 50)
    ]
    
    suggested = max(suggestions)
    suggested = max(5, min(100, suggested))
    
    return {
        "suggested": suggested,
        "reason": f"Based on {queued} queued calls, {running} running campaigns, {active} active calls"
    }

# ============= Alert Routes =============
@api_router.get(
    "/alerts",
    response_model=List[AlertLog],
    tags=["Alerts"],
    summary="Get alerts",
    description="""
    Retrieve alert logs filtered by resolution status.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - resolved: Filter by resolution status (default: false = active alerts)
    
    **Returns:**
    - List of alerts (most recent first, max 100)
    - Each alert includes level, message, partner info, and timestamps
    
    **Alert Levels:**
    - CRITICAL: Immediate attention required
    - HIGH: Important issues
    - MEDIUM: Moderate concerns
    - ERROR: Connection or system errors
    - NORMAL: Informational
    """
)
async def get_alerts(resolved: Optional[bool] = False, current_user: User = Depends(get_current_user)):
    query = {"isResolved": resolved}
    alerts = await db.alert_logs.find(query, {"_id": 0}).sort("createdAt", -1).limit(100).to_list(100)
    return alerts

@api_router.get(
    "/alerts/summary",
    response_model=AlertSummary,
    tags=["Alerts"],
    summary="Get alert summary",
    description="""
    Get quick summary count of active alerts by level.
    
    **Authentication Required:** Yes
    
    **Returns:**
    - critical: Count of CRITICAL alerts
    - high: Count of HIGH alerts
    - medium: Count of MEDIUM alerts
    - offline: Count of ERROR alerts (partner connectivity issues)
    
    **Use Cases:**
    - Dashboard alert badge
    - Quick health indicator
    - Alert notification count
    
    **Note:** Only includes active (not dismissed and not resolved) alerts.
    """
)
async def get_alert_summary(current_user: User = Depends(get_current_user)):
    active_alerts = await db.alert_logs.find({"isResolved": False, "isDismissed": False}, {"_id": 0}).to_list(1000)
    
    critical = sum(1 for a in active_alerts if a['alertLevel'] == 'CRITICAL')
    high = sum(1 for a in active_alerts if a['alertLevel'] == 'HIGH')
    medium = sum(1 for a in active_alerts if a['alertLevel'] == 'MEDIUM')
    offline = sum(1 for a in active_alerts if a['alertLevel'] == 'ERROR')
    
    return AlertSummary(critical=critical, high=high, medium=medium, offline=offline)

@api_router.put(
    "/alerts/{alert_id}/dismiss",
    tags=["Alerts"],
    summary="Dismiss alert",
    description="""
    Dismiss an alert for a specified duration.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - alert_id: UUID of the alert
    - hours: Duration to dismiss (default: 24 hours)
    
    **Process:**
    - Marks alert as dismissed
    - Records who dismissed it and when
    - Sets dismissedUntil timestamp
    - Alert may reappear after dismissal period
    
    **Use Cases:**
    - Acknowledge known issues
    - Temporarily hide alerts during maintenance
    - Manage alert fatigue
    """
)
async def dismiss_alert(alert_id: str, hours: int = 24, current_user: User = Depends(get_current_user)):
    await db.alert_logs.update_one(
        {"id": alert_id},
        {"$set": {
            "isDismissed": True,
            "dismissedBy": current_user.id,
            "dismissedAt": datetime.now(timezone.utc).isoformat(),
            "dismissedUntil": (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        }}
    )
    return {"message": "Alert dismissed"}

# ============= Settings Routes =============
@api_router.get(
    "/settings",
    response_model=List[SystemSetting],
    tags=["System Settings"],
    summary="Get all system settings",
    description="""
    Retrieve all system configuration settings.
    
    **Authentication Required:** Yes
    
    **Returns:**
    - List of all system settings with keys, values, and descriptions
    
    **Common Settings:**
    - refreshInterval: Dashboard auto-refresh interval (seconds)
    - autoRefreshEnabled: Enable/disable auto-refresh
    - queryTimeout: Database query timeout (seconds)
    - connectionTimeout: SSH connection timeout (seconds)
    - concurrentPartnerLimit: Max parallel partner queries
    - criticalQueuedThreshold: Alert threshold for queued calls
    - criticalUtilizationThreshold: Alert threshold for utilization %
    """
)
async def get_settings(current_user: User = Depends(get_current_user)):
    settings = await db.system_settings.find({}, {"_id": 0}).to_list(1000)
    return settings

@api_router.put(
    "/settings",
    tags=["System Settings"],
    summary="Update system settings",
    description="""
    Update one or more system settings.
    
    **Authentication Required:** Yes
    
    **Request Body:**
    Array of settings to update:
    ```json
    [
        {
            "settingKey": "refreshInterval",
            "settingValue": 180,
            "description": "Dashboard refresh interval in seconds"
        }
    ]
    ```
    
    **Process:**
    - Updates or creates settings (upsert)
    - Records who made the change
    - Updates timestamp
    
    **Use Cases:**
    - Configure system behavior
    - Tune performance parameters
    - Adjust alert thresholds
    """
)
async def update_settings(settings: List[SystemSetting], current_user: User = Depends(get_current_user)):
    for setting in settings:
        setting.updatedBy = current_user.id
        setting.updatedAt = datetime.now(timezone.utc)
        
        setting_dict = setting.model_dump()
        setting_dict['updatedAt'] = setting_dict['updatedAt'].isoformat()
        
        await db.system_settings.update_one(
            {"settingKey": setting.settingKey},
            {"$set": setting_dict},
            upsert=True
        )
    
    return {"message": "Settings updated successfully"}

@api_router.get(
    "/settings/{key}",
    response_model=SystemSetting,
    tags=["System Settings"],
    summary="Get specific setting",
    description="""
    Retrieve a single system setting by key.
    
    **Authentication Required:** Yes
    
    **Parameters:**
    - key: Setting key (e.g., "refreshInterval")
    
    **Returns:**
    - Setting object with key, value, and description
    
    **Errors:**
    - 404: Setting not found
    """
)
async def get_setting(key: str, current_user: User = Depends(get_current_user)):
    setting = await db.system_settings.find_one({"settingKey": key}, {"_id": 0})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return SystemSetting(**setting)

# ============= Partner Detail Routes =============
@api_router.get("/partners/{partner_id}/metrics", response_model=DashboardSnapshot)
async def get_partner_metrics(partner_id: str, current_user: User = Depends(get_current_user)):
    snapshot = await db.dashboard_snapshots.find_one(
        {"partnerId": partner_id},
        {"_id": 0},
        sort=[("snapshotTime", -1)]
    )
    if not snapshot:
        # Return empty snapshot instead of 404
        return DashboardSnapshot(
            partnerId=partner_id,
            campaignsToday=0,
            runningCampaigns=0,
            activeCalls=0,
            queuedCalls=0,
            completedCallsToday=0,
            voicemailCount=0,
            customerEndedCount=0,
            remainingCalls=0,
            concurrencyLimit=0,
            utilizationPercent=0.0,
            alertLevel=AlertLevel.NORMAL,
            alertMessage="No data available",
            snapshotTime=datetime.now(timezone.utc),
            dataFetchTimeMs=0
        )
    return DashboardSnapshot(**snapshot)

@api_router.get("/partners/{partner_id}/campaigns")
async def get_partner_campaigns(partner_id: str, page: int = 1, pageSize: int = 20, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # This would query the partner's database via SSH
    # For now, return mock data
    return {
        "campaigns": [],
        "total": 0,
        "page": page,
        "pageSize": pageSize
    }

@api_router.get("/partners/{partner_id}/period-stats")
async def get_period_statistics(
    partner_id: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get total calls and submitted candidates for a given time period
    
    Parameters:
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    
    Returns:
    - totalCalls: Total number of calls in the period
    - totalSubmittedCandidates: Total number of submitted candidates in the period
    - callsByStatus: Breakdown of calls by status
    - period: The queried time period
    """
    # Get partner configuration
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    
    try:
        # Prepare queries for batch execution
        queries = [
            # Query 1: Total calls in period
            {
                'query': """
                    SELECT COUNT(*) as total_calls
                    FROM calls
                    WHERE DATE(createdAt) BETWEEN %s AND %s
                """,
                'params': (start_date, end_date)
            },
            # Query 2: Calls by status breakdown
            {
                'query': """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM calls
                    WHERE DATE(createdAt) BETWEEN %s AND %s
                    GROUP BY status
                """,
                'params': (start_date, end_date)
            },
            # Query 3: Total submitted candidates
            {
                'query': """
                    SELECT COUNT(*) as total_submittals
                    FROM ats_submittals
                    WHERE DATE(createdAt) BETWEEN %s AND %s
                """,
                'params': (start_date, end_date)
            },
            # Query 4: Submitted candidates by status (if status column exists)
            {
                'query': """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM ats_submittals
                    WHERE DATE(createdAt) BETWEEN %s AND %s
                    GROUP BY status
                """,
                'params': (start_date, end_date)
            }
        ]
        
        # Execute all queries through single SSH connection
        results = await ssh_service.execute_batch_queries(partner, queries)
        
        # Extract total calls
        total_calls = results[0][0]['total_calls'] if results[0] and len(results[0]) > 0 else 0
        
        # Extract calls by status
        calls_by_status = {}
        if results[1] and len(results[1]) > 0:
            for row in results[1]:
                calls_by_status[row['status']] = row['count']
        
        # Extract total submittals
        total_submittals = results[2][0]['total_submittals'] if results[2] and len(results[2]) > 0 else 0
        
        # Extract submittals by status
        submittals_by_status = {}
        if results[3] and len(results[3]) > 0:
            for row in results[3]:
                submittals_by_status[row['status']] = row['count']
        
        return {
            "success": True,
            "period": {
                "startDate": start_date,
                "endDate": end_date
            },
            "calls": {
                "total": total_calls,
                "byStatus": calls_by_status
            },
            "submittals": {
                "total": total_submittals,
                "byStatus": submittals_by_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching period statistics: {str(e)}")
        # Return empty data instead of error
        return {
            "success": False,
            "error": str(e),
            "period": {
                "startDate": start_date,
                "endDate": end_date
            },
            "calls": {
                "total": 0,
                "byStatus": {}
            },
            "submittals": {
                "total": 0,
                "byStatus": {}
            }
        }

@api_router.get("/all-partners/period-stats")
async def get_all_partners_period_statistics(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated statistics across ALL partners for a given time period
    
    Parameters:
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    
    Returns:
    - Aggregated total calls and submittals across all partners
    - Per-partner breakdown
    - Overall totals and status breakdowns
    """
    try:
        # Get all active partners
        partners = await db.partner_configs.find({"isActive": True}, {"_id": 0}).to_list(None)
        
        if not partners:
            return {
                "success": True,
                "period": {
                    "startDate": start_date,
                    "endDate": end_date
                },
                "totalPartners": 0,
                "aggregated": {
                    "calls": {"total": 0, "byStatus": {}},
                    "submittals": {"total": 0, "byStatus": {}}
                },
                "partnerBreakdown": []
            }
        
        partner_breakdown = []
        total_calls = 0
        total_submittals = 0
        aggregated_calls_by_status = {}
        aggregated_submittals_by_status = {}
        
        # Fetch data for each partner
        for partner_data in partners:
            partner = PartnerConfig(**partner_data)
            
            try:
                queries = [
                    # Total calls
                    {
                        'query': """
                            SELECT COUNT(*) as total_calls
                            FROM calls
                            WHERE DATE(createdAt) BETWEEN %s AND %s
                        """,
                        'params': (start_date, end_date)
                    },
                    # Calls by status
                    {
                        'query': """
                            SELECT status, COUNT(*) as count
                            FROM calls
                            WHERE DATE(createdAt) BETWEEN %s AND %s
                            GROUP BY status
                        """,
                        'params': (start_date, end_date)
                    },
                    # Total submittals
                    {
                        'query': """
                            SELECT COUNT(*) as total_submittals
                            FROM ats_submittals
                            WHERE DATE(createdAt) BETWEEN %s AND %s
                        """,
                        'params': (start_date, end_date)
                    },
                    # Submittals by status
                    {
                        'query': """
                            SELECT status, COUNT(*) as count
                            FROM ats_submittals
                            WHERE DATE(createdAt) BETWEEN %s AND %s
                            GROUP BY status
                        """,
                        'params': (start_date, end_date)
                    }
                ]
                
                results = await ssh_service.execute_batch_queries(partner, queries)
                
                # Extract partner data
                partner_calls = results[0][0]['total_calls'] if results[0] and len(results[0]) > 0 else 0
                partner_submittals = results[2][0]['total_submittals'] if results[2] and len(results[2]) > 0 else 0
                
                calls_by_status = {}
                if results[1] and len(results[1]) > 0:
                    for row in results[1]:
                        status = row['status']
                        count = row['count']
                        calls_by_status[status] = count
                        aggregated_calls_by_status[status] = aggregated_calls_by_status.get(status, 0) + count
                
                submittals_by_status = {}
                if results[3] and len(results[3]) > 0:
                    for row in results[3]:
                        status = row['status']
                        count = row['count']
                        submittals_by_status[status] = count
                        aggregated_submittals_by_status[status] = aggregated_submittals_by_status.get(status, 0) + count
                
                # Add to totals
                total_calls += partner_calls
                total_submittals += partner_submittals
                
                # Add partner breakdown
                partner_breakdown.append({
                    "partnerId": partner.id,
                    "partnerName": partner.partnerName,
                    "calls": {
                        "total": partner_calls,
                        "byStatus": calls_by_status
                    },
                    "submittals": {
                        "total": partner_submittals,
                        "byStatus": submittals_by_status
                    }
                })
                
            except Exception as e:
                logger.error(f"Error fetching data for partner {partner.partnerName}: {str(e)}")
                # Add partner with error status
                partner_breakdown.append({
                    "partnerId": partner.id,
                    "partnerName": partner.partnerName,
                    "error": str(e),
                    "calls": {"total": 0, "byStatus": {}},
                    "submittals": {"total": 0, "byStatus": {}}
                })
        
        return {
            "success": True,
            "period": {
                "startDate": start_date,
                "endDate": end_date
            },
            "totalPartners": len(partners),
            "aggregated": {
                "calls": {
                    "total": total_calls,
                    "byStatus": aggregated_calls_by_status
                },
                "submittals": {
                    "total": total_submittals,
                    "byStatus": aggregated_submittals_by_status
                }
            },
            "partnerBreakdown": partner_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error fetching all partners period statistics: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "period": {
                "startDate": start_date,
                "endDate": end_date
            },
            "totalPartners": 0,
            "aggregated": {
                "calls": {"total": 0, "byStatus": {}},
                "submittals": {"total": 0, "byStatus": {}}
            },
            "partnerBreakdown": []
        }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    
    # Create default admin user if not exists
    admin_exists = await db.users.find_one({"username": "admin"})
    if not admin_exists:
        admin = User(
            username="admin",
            email="admin@jobtalk.com",
            role=UserRole.ADMIN
        )
        admin_dict = admin.model_dump()
        admin_dict['passwordHash'] = hash_password("Admin@2024")
        admin_dict['createdAt'] = admin_dict['createdAt'].isoformat()
        admin_dict['updatedAt'] = admin_dict['updatedAt'].isoformat()
        await db.users.insert_one(admin_dict)
        logger.info("Created default admin user: admin / Admin@2024")
    
    # Initialize default settings
    default_settings = [
        {"settingKey": "refreshInterval", "settingValue": 120, "description": "Dashboard refresh interval in seconds"},
        {"settingKey": "autoRefreshEnabled", "settingValue": True, "description": "Enable auto-refresh"},
        {"settingKey": "queryTimeout", "settingValue": 60, "description": "Query timeout in seconds"},
        {"settingKey": "connectionTimeout", "settingValue": 30, "description": "Connection timeout in seconds"},
        {"settingKey": "concurrentPartnerLimit", "settingValue": 5, "description": "Concurrent partner query limit"},
        {"settingKey": "criticalQueuedThreshold", "settingValue": 200, "description": "Critical alert queued calls threshold"},
        {"settingKey": "criticalUtilizationThreshold", "settingValue": 30, "description": "Critical alert utilization threshold"},
        {"settingKey": "highQueuedMin", "settingValue": 100, "description": "High priority queued min"},
        {"settingKey": "highQueuedMax", "settingValue": 200, "description": "High priority queued max"},
    ]
    
    for setting in default_settings:
        exists = await db.system_settings.find_one({"settingKey": setting['settingKey']})
        if not exists:
            setting['id'] = str(uuid.uuid4())
            setting['updatedAt'] = datetime.now(timezone.utc).isoformat()
            await db.system_settings.insert_one(setting)
    
    # Start data fetch scheduler
    data_fetch_service.start_scheduler()
    logger.info("Data fetch scheduler started")

@app.on_event("shutdown")
async def shutdown_db_client():
    data_fetch_service.stop_scheduler()
    client.close()
