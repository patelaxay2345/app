# JobTalk Admin Dashboard - Public API Documentation

## Overview

The Public API allows you to display call and submittal statistics on external websites without authentication. This is perfect for:
- Company websites
- Marketing pages
- Client portals
- Public dashboards

## Endpoint

```
GET /api/public/stats
```

**Base URL:**
```
Production: https://your-domain.com/api/public/stats
Development: https://dash-jobtalk.preview.emergentagent.com/api/public/stats
```

## Authentication

**None required!** This is a public endpoint that does not require JWT authentication.

## Query Parameters

All parameters are optional:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `partner_id` | string | none | Specific partner UUID. If omitted, returns aggregated stats for all partners |
| `start_date` | string | 30 days ago | Start date in YYYY-MM-DD format |
| `end_date` | string | today | End date in YYYY-MM-DD format |

## Response Format

```json
{
  "calls": 1234,
  "submittals": 567,
  "period": {
    "startDate": "2024-10-15",
    "endDate": "2024-11-14"
  }
}
```

### Response Fields

- `calls` (integer): Total number of calls in the specified period
- `submittals` (integer): Total number of ATS submittals in the specified period
- `period.startDate` (string): Start date of the queried period
- `period.endDate` (string): End date of the queried period

## Usage Examples

### Example 1: All Partners, Last 30 Days (Default)

**Request:**
```
GET /api/public/stats
```

**Response:**
```json
{
  "calls": 1234,
  "submittals": 567,
  "period": {
    "startDate": "2024-10-15",
    "endDate": "2024-11-14"
  }
}
```

### Example 2: All Partners, Custom Date Range

**Request:**
```
GET /api/public/stats?start_date=2024-01-01&end_date=2024-01-31
```

**Response:**
```json
{
  "calls": 3456,
  "submittals": 892,
  "period": {
    "startDate": "2024-01-01",
    "endDate": "2024-01-31"
  }
}
```

### Example 3: Specific Partner, Last 30 Days

**Request:**
```
GET /api/public/stats?partner_id=abc-123-def-456
```

**Response:**
```json
{
  "calls": 456,
  "submittals": 123,
  "period": {
    "startDate": "2024-10-15",
    "endDate": "2024-11-14"
  }
}
```

### Example 4: Specific Partner, Custom Date Range

**Request:**
```
GET /api/public/stats?partner_id=abc-123-def-456&start_date=2024-01-01&end_date=2024-12-31
```

**Response:**
```json
{
  "calls": 5678,
  "submittals": 1234,
  "period": {
    "startDate": "2024-01-01",
    "endDate": "2024-12-31"
  }
}
```

## Code Examples

### JavaScript (Vanilla)

```javascript
// All partners, last 30 days
fetch('https://dash-jobtalk.preview.emergentagent.com/api/public/stats')
  .then(response => response.json())
  .then(data => {
    document.getElementById('calls').textContent = data.calls;
    document.getElementById('submittals').textContent = data.submittals;
  })
  .catch(error => console.error('Error:', error));

// With custom parameters
const params = new URLSearchParams({
  partner_id: 'your-partner-uuid',
  start_date: '2024-01-01',
  end_date: '2024-12-31'
});

fetch(`https://dash-jobtalk.preview.emergentagent.com/api/public/stats?${params}`)
  .then(response => response.json())
  .then(data => console.log(data));
```

### JavaScript (Axios)

```javascript
import axios from 'axios';

// All partners, last 30 days
axios.get('https://dash-jobtalk.preview.emergentagent.com/api/public/stats')
  .then(response => {
    console.log('Calls:', response.data.calls);
    console.log('Submittals:', response.data.submittals);
  });

// With parameters
axios.get('https://dash-jobtalk.preview.emergentagent.com/api/public/stats', {
  params: {
    partner_id: 'your-partner-uuid',
    start_date: '2024-01-01',
    end_date: '2024-12-31'
  }
}).then(response => console.log(response.data));
```

### jQuery

```javascript
// All partners, last 30 days
$.getJSON('https://dash-jobtalk.preview.emergentagent.com/api/public/stats', function(data) {
  $('#calls').text(data.calls.toLocaleString());
  $('#submittals').text(data.submittals.toLocaleString());
});

// With parameters
$.getJSON('https://dash-jobtalk.preview.emergentagent.com/api/public/stats', {
  partner_id: 'your-partner-uuid',
  start_date: '2024-01-01',
  end_date: '2024-12-31'
}, function(data) {
  console.log(data);
});
```

### Python (requests)

```python
import requests

# All partners, last 30 days
response = requests.get('https://dash-jobtalk.preview.emergentagent.com/api/public/stats')
data = response.json()
print(f"Calls: {data['calls']}")
print(f"Submittals: {data['submittals']}")

# With parameters
params = {
    'partner_id': 'your-partner-uuid',
    'start_date': '2024-01-01',
    'end_date': '2024-12-31'
}
response = requests.get(
    'https://dash-jobtalk.preview.emergentagent.com/api/public/stats',
    params=params
)
data = response.json()
```

### PHP (cURL)

```php
<?php
// All partners, last 30 days
$url = 'https://dash-jobtalk.preview.emergentagent.com/api/public/stats';
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
curl_close($ch);
$data = json_decode($response, true);

echo "Calls: " . $data['calls'] . "\n";
echo "Submittals: " . $data['submittals'] . "\n";

// With parameters
$params = http_build_query([
    'partner_id' => 'your-partner-uuid',
    'start_date' => '2024-01-01',
    'end_date' => '2024-12-31'
]);
$url = 'https://dash-jobtalk.preview.emergentagent.com/api/public/stats?' . $params;
// ... rest of cURL code
?>
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function JobTalkStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('https://dash-jobtalk.preview.emergentagent.com/api/public/stats')
      .then(response => response.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading statistics...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="stats-container">
      <div className="stat-card">
        <h3>Total Calls</h3>
        <p className="stat-value">{stats.calls.toLocaleString()}</p>
      </div>
      <div className="stat-card">
        <h3>Total Submittals</h3>
        <p className="stat-value">{stats.submittals.toLocaleString()}</p>
      </div>
      <div className="period">
        Period: {stats.period.startDate} to {stats.period.endDate}
      </div>
    </div>
  );
}

export default JobTalkStats;
```

## CORS Configuration

The public API supports Cross-Origin Resource Sharing (CORS) to allow requests from your website.

### Managing Allowed Domains

You can configure which domains are allowed to access the public API through the admin settings:

1. **Login to Admin Dashboard**
2. **Navigate to Settings**
3. **Find "Public API Allowed Domains" setting**
4. **Add your domains** (comma-separated):
   ```
   https://example.com,https://www.example.com,https://another-domain.com
   ```

### CORS Behavior

- **Empty setting**: Allows all origins (default)
- **With domains**: Only specified domains can access the API
- **No match**: Request will be blocked by browser

**Example Setting:**
```
https://example.com,https://www.example.com
```

This allows requests from:
- ✅ https://example.com
- ✅ https://www.example.com
- ❌ https://other-domain.com (blocked)

## Rate Limiting

Currently, there is no rate limiting on the public API. However, we recommend:

- **Cache responses** on your website for at least 5 minutes
- **Don't make requests** more than once per minute
- **Use appropriate error handling** to avoid retry storms

## Error Responses

### 404 Not Found (Specific Partner)

```json
{
  "detail": "Partner not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error fetching statistics"
}
```

## Best Practices

1. **Cache the Response**
   ```javascript
   // Cache for 5 minutes
   const CACHE_TIME = 5 * 60 * 1000;
   let cachedData = null;
   let cacheTimestamp = 0;
   
   async function getStats() {
     const now = Date.now();
     if (cachedData && (now - cacheTimestamp) < CACHE_TIME) {
       return cachedData;
     }
     
     const response = await fetch('https://dash-jobtalk.preview.emergentagent.com/api/public/stats');
     cachedData = await response.json();
     cacheTimestamp = now;
     return cachedData;
   }
   ```

2. **Handle Errors Gracefully**
   ```javascript
   fetch('https://dash-jobtalk.preview.emergentagent.com/api/public/stats')
     .then(response => {
       if (!response.ok) {
         throw new Error(`HTTP ${response.status}`);
       }
       return response.json();
     })
     .then(data => displayStats(data))
     .catch(error => {
       console.error('Stats API error:', error);
       // Show fallback content
       displayFallback();
     });
   ```

3. **Show Loading States**
   Always provide visual feedback while data is being fetched.

4. **Format Numbers**
   Use locale formatting for better readability:
   ```javascript
   const formattedCalls = data.calls.toLocaleString(); // "1,234"
   ```

## Getting Your Partner ID

To get your specific partner ID:

1. Login to the admin dashboard
2. Go to **Partners** page
3. Click on your partner
4. Copy the UUID from the URL or partner details

## Support

For issues or questions about the public API:
- Check the [full API documentation](/app/API_DOCUMENTATION.md)
- Review the [example HTML file](/app/PUBLIC_API_EXAMPLE.html)
- Contact support: support@your-domain.com

## Changelog

### Version 1.0.0 (Current)
- Initial public API release
- Support for all partners and specific partner queries
- Custom date range parameters
- Configurable CORS domains via admin settings
