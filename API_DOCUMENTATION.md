# JobTalk Admin Dashboard - API Documentation

## Base URL
```
Production: https://your-domain.com/api
Development: https://dash-jobtalk.preview.emergentagent.com/api
```

## Authentication
All endpoints require JWT authentication unless specified otherwise.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Getting a Token:**
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

---

## Table of Contents
1. [Authentication](#authentication-endpoints)
2. [Dashboard](#dashboard-endpoints)
3. [Partners](#partner-endpoints)
4. [Statistics](#statistics-endpoints)
5. [Settings](#settings-endpoints)
6. [Concurrency](#concurrency-endpoints)

---

## Authentication Endpoints

### 1. Login
**Endpoint:** `POST /api/auth/login`

**Description:** Authenticate user and receive JWT token

**Request Body:**
```json
{
  "username": "admin",
  "password": "Admin@2024"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-id",
    "username": "admin",
    "email": "admin@example.com",
    "role": "ADMIN"
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### 2. Change Password
**Endpoint:** `POST /api/auth/change-password`

**Description:** Change current user's password

**Authentication:** Required

**Request Body:**
```json
{
  "currentPassword": "old_password",
  "newPassword": "new_password"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Current password is incorrect"
}
```

---

### 3. Logout
**Endpoint:** `POST /api/auth/logout`

**Description:** Logout current user

**Authentication:** Required

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

## Dashboard Endpoints

### 1. Dashboard Overview
**Endpoint:** `GET /api/dashboard/overview`

**Description:** Get aggregated metrics across all partners

**Authentication:** Required

**Response (200 OK):**
```json
{
  "campaignsToday": 42,
  "runningCampaigns": 88,
  "activeCalls": 7,
  "queuedCalls": 3,
  "completedCallsToday": 125,
  "remainingCalls": 537,
  "totalPartners": 1,
  "activePartners": 1,
  "avgUtilization": 35.5,
  "lastUpdated": "2024-11-06T20:30:00Z"
}
```

---

### 2. Dashboard Partners
**Endpoint:** `GET /api/dashboard/partners`

**Description:** Get all partners with their latest snapshots

**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "partner": {
      "id": "partner-id",
      "partnerName": "ApTask",
      "tenantId": 123,
      "concurrencyLimit": 5,
      "pauseNonPriorityCampaigns": false,
      "isActive": true
    },
    "snapshot": {
      "campaignsToday": 42,
      "runningCampaigns": 88,
      "activeCalls": 7,
      "queuedCalls": 3,
      "completedCallsToday": 125,
      "voicemailCount": 45,
      "customerEndedCount": 80,
      "remainingCalls": 537,
      "utilizationPercent": 35.5,
      "alertLevel": "NORMAL"
    }
  }
]
```

---

## Partner Endpoints

### 1. Get All Partners
**Endpoint:** `GET /api/partners`

**Description:** List all partners

**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": "partner-id",
    "partnerName": "ApTask",
    "tenantId": 123,
    "dbHost": "db.example.com",
    "dbPort": 3306,
    "dbName": "aptask_db",
    "dbType": "mysql",
    "concurrencyLimit": 5,
    "pauseNonPriorityCampaigns": false,
    "isActive": true,
    "sshConfig": {
      "enabled": true,
      "host": "ssh.example.com",
      "port": 22,
      "username": "sshuser"
    }
  }
]
```

---

### 2. Create Partner
**Endpoint:** `POST /api/partners`

**Description:** Create a new partner

**Authentication:** Required

**Request Body:**
```json
{
  "partnerName": "New Partner",
  "tenantId": 123,
  "dbHost": "db.example.com",
  "dbPort": 3306,
  "dbName": "partner_db",
  "dbUsername": "dbuser",
  "dbPassword": "dbpass123",
  "dbType": "mysql",
  "concurrencyLimit": 10,
  "pauseNonPriorityCampaigns": false,
  "isActive": true,
  "sshConfig": {
    "enabled": true,
    "host": "ssh.example.com",
    "port": 22,
    "username": "sshuser",
    "password": "sshpass123"
  }
}
```

**Response (200 OK):**
```json
{
  "message": "Partner created successfully",
  "id": "new-partner-id"
}
```

---

### 3. Update Partner
**Endpoint:** `PUT /api/partners/{partner_id}`

**Description:** Update partner configuration

**Authentication:** Required

**Request Body:** (Same as Create Partner, all fields optional)

**Response (200 OK):**
```json
{
  "message": "Partner updated successfully"
}
```

---

### 4. Delete Partner
**Endpoint:** `DELETE /api/partners/{partner_id}`

**Description:** Delete a partner

**Authentication:** Required

**Response (200 OK):**
```json
{
  "message": "Partner deleted successfully"
}
```

---

### 5. Test Connection
**Endpoint:** `POST /api/partners/{partner_id}/test-connection`

**Description:** Test SSH and database connection for a partner

**Authentication:** Required

**Response (200 OK - Success):**
```json
{
  "success": true,
  "message": "Connection successful via SSH tunnel",
  "responseTimeMs": 245,
  "details": {
    "database": "aptask_db",
    "via_ssh": true
  }
}
```

**Response (200 OK - Failed):**
```json
{
  "success": false,
  "message": "SSH connection failed: Authentication failed",
  "responseTimeMs": 1523
}
```

---

### 6. Force Sync
**Endpoint:** `POST /api/partners/{partner_id}/force-sync`

**Description:** Trigger immediate data fetch for a partner

**Authentication:** Required

**Response (200 OK):**
```json
{
  "message": "Force sync initiated for ApTask"
}
```

---

### 7. Get Partner Metrics
**Endpoint:** `GET /api/partners/{partner_id}/metrics`

**Description:** Get latest metrics snapshot for a partner

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": "snapshot-id",
  "partnerId": "partner-id",
  "campaignsToday": 42,
  "runningCampaigns": 88,
  "activeCalls": 7,
  "queuedCalls": 3,
  "completedCallsToday": 125,
  "voicemailCount": 45,
  "customerEndedCount": 80,
  "remainingCalls": 537,
  "concurrencyLimit": 5,
  "utilizationPercent": 35.5,
  "alertLevel": "NORMAL",
  "alertMessage": null,
  "snapshotTime": "2024-11-06T20:30:00Z",
  "dataFetchTimeMs": 1250
}
```

---

### 8. Get Partner Connection Logs
**Endpoint:** `GET /api/partners/{partner_id}/logs?limit=50`

**Description:** Get connection test logs for a partner

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Number of logs to return (default: 50)

**Response (200 OK):**
```json
[
  {
    "id": "log-id",
    "partnerId": "partner-id",
    "status": "SUCCESS",
    "timestamp": "2024-11-06T20:30:00Z",
    "responseTimeMs": 245,
    "errorMessage": null
  }
]
```

---

### 9. Clear Partner Logs
**Endpoint:** `DELETE /api/partners/{partner_id}/logs`

**Description:** Clear all connection logs for a partner

**Authentication:** Required

**Response (200 OK):**
```json
{
  "message": "Deleted 15 connection logs"
}
```

---

## Statistics Endpoints

### 1. Single Partner Period Statistics
**Endpoint:** `GET /api/partners/{partner_id}/period-stats`

**Description:** Get calls and submittals for a specific partner in a date range

**Authentication:** Required

**Query Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:**
```
GET /api/partners/partner-123/period-stats?start_date=2024-11-01&end_date=2024-11-30
```

**Response (200 OK):**
```json
{
  "success": true,
  "period": {
    "startDate": "2024-11-01",
    "endDate": "2024-11-30"
  },
  "calls": {
    "total": 1523,
    "byStatus": {
      "ENDED": 850,
      "INPROGRESS": 12,
      "QUEUED": 45,
      "FAILED": 516,
      "CANCELLED": 100
    }
  },
  "submittals": {
    "total": 245,
    "byStatus": {
      "submitted": 180,
      "pending": 35,
      "approved": 20,
      "rejected": 10
    }
  }
}
```

---

### 2. All Partners Aggregated Statistics
**Endpoint:** `GET /api/all-partners/period-stats`

**Description:** Get aggregated calls and submittals for ALL partners in a date range

**Authentication:** Required

**Query Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:**
```
GET /api/all-partners/period-stats?start_date=2024-11-01&end_date=2024-11-30
```

**Response (200 OK):**
```json
{
  "success": true,
  "period": {
    "startDate": "2024-11-01",
    "endDate": "2024-11-30"
  },
  "totalPartners": 3,
  "aggregated": {
    "calls": {
      "total": 4569,
      "byStatus": {
        "ENDED": 2550,
        "INPROGRESS": 37,
        "QUEUED": 135,
        "FAILED": 1547,
        "CANCELLED": 300
      }
    },
    "submittals": {
      "total": 735,
      "byStatus": {
        "submitted": 540,
        "pending": 105,
        "approved": 60,
        "rejected": 30
      }
    }
  },
  "partnerBreakdown": [
    {
      "partnerId": "partner-1",
      "partnerName": "ApTask",
      "calls": {
        "total": 1523,
        "byStatus": { "ENDED": 850, "FAILED": 516 }
      },
      "submittals": {
        "total": 245,
        "byStatus": { "submitted": 180 }
      }
    }
  ]
}
```

---

## Concurrency Endpoints

### 1. Update Partner Concurrency
**Endpoint:** `POST /api/partners/{partner_id}/concurrency`

**Description:** Update concurrency limit for a partner (updates both admin DB and partner DB)

**Authentication:** Required

**Request Body:**
```json
{
  "newLimit": 15,
  "reason": "Increased capacity"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Concurrency updated",
  "syncedToPartner": true
}
```

---

### 2. Toggle Pause Non-Priority Campaigns
**Endpoint:** `POST /api/partners/{partner_id}/pause-non-priority`

**Description:** Enable/disable pauseNonPriorityCampaigns setting

**Authentication:** Required

**Request Body:**
```json
{
  "enabled": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "pauseNonPriorityCampaigns enabled",
  "syncedToPartner": true
}
```

---

## Settings Endpoints

### 1. Get Settings
**Endpoint:** `GET /api/settings`

**Description:** Get all application settings

**Authentication:** Required

**Response (200 OK):**
```json
{
  "refreshInterval": 120,
  "dataRetentionDays": 90,
  "alertThreshold": 80
}
```

---

### 2. Update Settings
**Endpoint:** `PUT /api/settings`

**Description:** Update application settings

**Authentication:** Required

**Request Body:**
```json
{
  "refreshInterval": 180,
  "dataRetentionDays": 120
}
```

**Response (200 OK):**
```json
{
  "message": "Settings updated successfully"
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message here"
}
```

### Common Status Codes
- `200 OK` - Request successful
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## Rate Limiting
Currently no rate limiting is enforced, but recommended best practices:
- Maximum 100 requests per minute per user
- Dashboard refresh: Every 2 minutes
- Force sync: Maximum once per minute per partner

---

## Swagger/OpenAPI Documentation

Interactive API documentation is available at:
```
https://your-domain.com/docs
```

Alternative ReDoc documentation:
```
https://your-domain.com/redoc
```

---

## SDK/Client Examples

### JavaScript/TypeScript Example
```javascript
import axios from 'axios';

const API_BASE = 'https://your-domain.com/api';
let authToken = null;

// Login
async function login(username, password) {
  const response = await axios.post(`${API_BASE}/auth/login`, {
    username,
    password
  });
  authToken = response.data.access_token;
  return response.data;
}

// Get Dashboard Overview
async function getDashboard() {
  const response = await axios.get(`${API_BASE}/dashboard/overview`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
  });
  return response.data;
}

// Get Period Stats for All Partners
async function getAllPartnersStats(startDate, endDate) {
  const response = await axios.get(`${API_BASE}/all-partners/period-stats`, {
    params: { start_date: startDate, end_date: endDate },
    headers: { 'Authorization': `Bearer ${authToken}` }
  });
  return response.data;
}
```

### Python Example
```python
import requests

API_BASE = 'https://your-domain.com/api'
auth_token = None

# Login
def login(username, password):
    global auth_token
    response = requests.post(f'{API_BASE}/auth/login', json={
        'username': username,
        'password': password
    })
    auth_token = response.json()['access_token']
    return response.json()

# Get Dashboard Overview
def get_dashboard():
    response = requests.get(f'{API_BASE}/dashboard/overview', headers={
        'Authorization': f'Bearer {auth_token}'
    })
    return response.json()

# Get Period Stats for All Partners
def get_all_partners_stats(start_date, end_date):
    response = requests.get(f'{API_BASE}/all-partners/period-stats', 
        params={'start_date': start_date, 'end_date': end_date},
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    return response.json()
```

---

## WebSocket Support
Currently not implemented. All data fetching is done via REST API with polling every 2 minutes.

---

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- Dashboard overview and metrics
- Partner management (CRUD)
- Period statistics (single and aggregated)
- Concurrency management
- Password change functionality
- SSH connection testing
- Real-time data fetching via batch queries

---

## Support
For issues or questions:
- Check logs: `/var/log/supervisor/backend.err.log`
- Contact: support@your-domain.com
