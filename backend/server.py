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
app = FastAPI(title="JobTalk Admin Dashboard")

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
@api_router.post("/auth/register", response_model=User)
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

@api_router.post("/auth/login", response_model=Token)
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

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

# ============= Partner Management Routes =============
@api_router.get("/partners", response_model=List[PartnerConfig])
async def get_partners(current_user: User = Depends(get_current_user)):
    partners = await db.partner_configs.find({}, {"_id": 0}).to_list(1000)
    return partners

@api_router.post("/partners", response_model=PartnerConfig)
async def create_partner(partner_input: PartnerConfigCreate, current_user: User = Depends(get_current_user)):
    # Check if partner name exists
    existing = await db.partner_configs.find_one({"partnerName": partner_input.partnerName}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Partner name already exists")
    
    # Create partner
    partner = PartnerConfig(**partner_input.model_dump())
    
    # Encrypt sensitive data
    partner_dict = partner.model_dump()
    partner_dict['dbPassword'] = encryption_service.encrypt(partner_input.dbPassword)
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

@api_router.get("/partners/{partner_id}", response_model=PartnerConfig)
async def get_partner(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerConfig(**partner_data)

@api_router.put("/partners/{partner_id}", response_model=PartnerConfig)
async def update_partner(partner_id: str, partner_update: PartnerConfigUpdate, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    update_dict = partner_update.model_dump(exclude_unset=True)
    
    # Encrypt sensitive fields if provided
    if 'dbPassword' in update_dict and update_dict['dbPassword']:
        update_dict['dbPassword'] = encryption_service.encrypt(update_dict['dbPassword'])
    
    if 'sshConfig' in update_dict:
        if update_dict['sshConfig'].get('privateKey'):
            update_dict['sshConfig']['privateKey'] = encryption_service.encrypt(update_dict['sshConfig']['privateKey'])
        if update_dict['sshConfig'].get('passphrase'):
            update_dict['sshConfig']['passphrase'] = encryption_service.encrypt(update_dict['sshConfig']['passphrase'])
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.partner_configs.update_one({"id": partner_id}, {"$set": update_dict})
    
    updated_partner = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    return PartnerConfig(**updated_partner)

@api_router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str, current_user: User = Depends(get_current_user)):
    result = await db.partner_configs.delete_one({"id": partner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"message": "Partner deleted successfully"}

@api_router.post("/partners/{partner_id}/test", response_model=TestConnectionResponse)
async def test_connection(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    result = await ssh_service.test_connection(partner)
    return result

@api_router.get("/partners/{partner_id}/logs", response_model=List[ConnectionLog])
async def get_partner_logs(partner_id: str, limit: int = 50, current_user: User = Depends(get_current_user)):
    logs = await db.connection_logs.find({"partnerId": partner_id}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

@api_router.get("/partners/{partner_id}/history", response_model=List[ConcurrencyHistory])
async def get_concurrency_history(partner_id: str, limit: int = 20, current_user: User = Depends(get_current_user)):
    history = await db.concurrency_history.find({"partnerId": partner_id}, {"_id": 0}).sort("changedAt", -1).limit(limit).to_list(limit)
    return history

@api_router.post("/partners/{partner_id}/force-sync")
async def force_sync(partner_id: str, current_user: User = Depends(get_current_user)):
    partner_data = await db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
    if not partner_data:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = PartnerConfig(**partner_data)
    await data_fetch_service.fetch_partner_data(partner)
    return {"message": "Sync initiated successfully"}

# ============= Dashboard Routes =============
@api_router.get("/dashboard/overview", response_model=DashboardOverview)
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
    
    active_partners = sum(1 for p in partners if p.get('isActive', True))
    avg_utilization = sum(s['latest']['utilizationPercent'] for s in snapshots) / len(snapshots) if snapshots else 0
    
    return DashboardOverview(
        campaignsToday=total_campaigns_today,
        runningCampaigns=total_running_campaigns,
        activeCalls=total_active_calls,
        queuedCalls=total_queued_calls,
        totalPartners=len(partners),
        activePartners=active_partners,
        avgUtilization=avg_utilization,
        lastUpdated=datetime.now(timezone.utc)
    )

@api_router.get("/dashboard/partners", response_model=List[PartnerDashboardData])
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

@api_router.post("/dashboard/refresh")
async def refresh_dashboard(current_user: User = Depends(get_current_user)):
    await data_fetch_service.fetch_all_partners()
    return {"message": "Dashboard refresh completed"}

# ============= Concurrency Management Routes =============
@api_router.put("/concurrency/{partner_id}")
async def update_concurrency(partner_id: str, update: ConcurrencyUpdate, current_user: User = Depends(get_current_user)):
    result = await concurrency_service.update_concurrency(
        partner_id,
        update.newLimit,
        update.reason,
        current_user.id
    )
    return result

@api_router.put("/concurrency/bulk")
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

@api_router.post("/concurrency/calculate")
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
@api_router.get("/alerts", response_model=List[AlertLog])
async def get_alerts(resolved: Optional[bool] = False, current_user: User = Depends(get_current_user)):
    query = {"isResolved": resolved}
    alerts = await db.alert_logs.find(query, {"_id": 0}).sort("createdAt", -1).limit(100).to_list(100)
    return alerts

@api_router.get("/alerts/summary", response_model=AlertSummary)
async def get_alert_summary(current_user: User = Depends(get_current_user)):
    active_alerts = await db.alert_logs.find({"isResolved": False, "isDismissed": False}, {"_id": 0}).to_list(1000)
    
    critical = sum(1 for a in active_alerts if a['alertLevel'] == 'CRITICAL')
    high = sum(1 for a in active_alerts if a['alertLevel'] == 'HIGH')
    medium = sum(1 for a in active_alerts if a['alertLevel'] == 'MEDIUM')
    offline = sum(1 for a in active_alerts if a['alertLevel'] == 'ERROR')
    
    return AlertSummary(critical=critical, high=high, medium=medium, offline=offline)

@api_router.put("/alerts/{alert_id}/dismiss")
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
@api_router.get("/settings", response_model=List[SystemSetting])
async def get_settings(current_user: User = Depends(get_current_user)):
    settings = await db.system_settings.find({}, {"_id": 0}).to_list(1000)
    return settings

@api_router.put("/settings")
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

@api_router.get("/settings/{key}", response_model=SystemSetting)
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
        raise HTTPException(status_code=404, detail="No metrics found")
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
