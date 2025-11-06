from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

# Enums
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"

class SyncStatus(str, Enum):
    NEVER_SYNCED = "NEVER_SYNCED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"

class ConnectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    SSH_FAILED = "SSH_FAILED"
    DB_FAILED = "DB_FAILED"
    QUERY_FAILED = "QUERY_FAILED"
    TIMEOUT = "TIMEOUT"
    ENCRYPTION_ERROR = "ENCRYPTION_ERROR"

class AlertLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    NORMAL = "NORMAL"
    IDLE = "IDLE"
    ERROR = "ERROR"

# User Models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole = UserRole.ADMIN

class UserCreate(UserBase):
    password: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lastLogin: Optional[datetime] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Partner Configuration Models
class SSHConfig(BaseModel):
    enabled: bool = True
    host: Optional[str] = None
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None  # SSH password authentication
    privateKey: Optional[str] = None  # SSH key authentication
    passphrase: Optional[str] = None  # Passphrase for private key

class PartnerConfigBase(BaseModel):
    partnerName: str
    tenantId: int = 0  # Made optional with default
    dbHost: str
    dbPort: int = 3306  # Default for MySQL, 27017 for MongoDB
    dbName: str
    dbUsername: str
    dbPassword: str
    dbType: str = "mysql"  # "mysql" or "mongodb"
    sshConfig: SSHConfig
    concurrencyLimit: int = 10
    isActive: bool = True

class PartnerConfigCreate(PartnerConfigBase):
    pass

class PartnerConfig(PartnerConfigBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lastSyncAt: Optional[datetime] = None
    lastSyncStatus: SyncStatus = SyncStatus.NEVER_SYNCED
    lastErrorMessage: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PartnerConfigUpdate(BaseModel):
    partnerName: Optional[str] = None
    tenantId: Optional[int] = None
    dbHost: Optional[str] = None
    dbPort: Optional[int] = None
    dbName: Optional[str] = None
    dbUsername: Optional[str] = None
    dbPassword: Optional[str] = None
    sshConfig: Optional[SSHConfig] = None
    concurrencyLimit: Optional[int] = None
    isActive: Optional[bool] = None

# System Settings Models
class SystemSetting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    settingKey: str
    settingValue: Any
    description: Optional[str] = None
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedBy: Optional[str] = None

# Dashboard Snapshot Models
class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partnerId: str
    campaignsToday: int = 0
    runningCampaigns: int = 0
    activeCalls: int = 0
    queuedCalls: int = 0
    completedCallsToday: int = 0
    remainingCalls: int = 0
    concurrencyLimit: int = 10
    utilizationPercent: float = 0.0
    alertLevel: AlertLevel = AlertLevel.NORMAL
    alertMessage: Optional[str] = None
    snapshotTime: datetime = Field(default_factory=datetime.utcnow)
    dataFetchTimeMs: int = 0

# Connection Log Models
class ConnectionLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partnerId: str
    connectionStatus: ConnectionStatus
    errorMessage: Optional[str] = None
    responseTimeMs: int = 0
    queryType: str = "dashboard_metrics"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Alert Log Models
class AlertLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partnerId: str
    alertLevel: AlertLevel
    alertMessage: str
    isDismissed: bool = False
    dismissedBy: Optional[str] = None
    dismissedAt: Optional[datetime] = None
    dismissedUntil: Optional[datetime] = None
    isResolved: bool = False
    resolvedAt: Optional[datetime] = None
    emailSent: bool = False
    lastEmailSentAt: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)

# Concurrency History Models
class ConcurrencyHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partnerId: str
    oldLimit: int
    newLimit: int
    reason: Optional[str] = None
    changedBy: str
    changedAt: datetime = Field(default_factory=datetime.utcnow)
    syncedToPartner: bool = False
    syncError: Optional[str] = None
    syncedAt: Optional[datetime] = None

class ConcurrencyUpdate(BaseModel):
    newLimit: int = Field(ge=1, le=100)
    reason: Optional[str] = None

class BulkConcurrencyUpdate(BaseModel):
    partnerIds: List[str]
    newLimit: int = Field(ge=1, le=100)
    reason: Optional[str] = None

# Dashboard Response Models
class DashboardOverview(BaseModel):
    campaignsToday: int
    runningCampaigns: int
    activeCalls: int
    queuedCalls: int
    completedCallsToday: int
    remainingCalls: int
    totalPartners: int
    activePartners: int
    avgUtilization: float
    lastUpdated: datetime

class PartnerDashboardData(BaseModel):
    partner: PartnerConfig
    snapshot: Optional[DashboardSnapshot] = None

class AlertSummary(BaseModel):
    critical: int
    high: int
    medium: int
    offline: int

# Campaign Models
class Campaign(BaseModel):
    id: int
    name: str
    status: str
    createdAt: datetime
    runningCalls: int = 0
    queuedCalls: int = 0
    jobTitle: Optional[str] = None

class CampaignListResponse(BaseModel):
    campaigns: List[Campaign]
    total: int
    page: int
    pageSize: int

# Call Statistics Models
class CallStats(BaseModel):
    totalCalls: int
    avgDuration: float
    successRate: float
    callsByStatus: Dict[str, int]

class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    responseTimeMs: int
    details: Optional[Dict[str, Any]] = None
