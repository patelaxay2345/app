from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
import logging
import asyncio
from typing import List
from models import PartnerConfig, DashboardSnapshot, AlertLevel, SyncStatus
from services.ssh_connection import SSHConnectionService
from services.alert import AlertService
import time
import pytz

logger = logging.getLogger(__name__)

class DataFetchService:
    def __init__(self, db, ssh_service: SSHConnectionService, alert_service: AlertService):
        self.db = db
        self.ssh_service = ssh_service
        self.alert_service = alert_service
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def _convert_utc_to_est(self, utc_datetime):
        """Convert UTC datetime to EST timezone"""
        if not utc_datetime:
            return None
        
        # Ensure the datetime is timezone-aware (UTC)
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        
        # Convert to EST
        est_tz = pytz.timezone('America/New_York')
        return utc_datetime.astimezone(est_tz)
    
    def start_scheduler(self):
        """Start scheduled data fetching"""
        if not self.is_running:
            # Schedule job every 2 minutes
            self.scheduler.add_job(
                self.fetch_all_partners,
                'interval',
                seconds=120,
                id='fetch_dashboard_data',
                replace_existing=True
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("Data fetch scheduler started")
            
            # Run immediately on startup
            asyncio.create_task(self.fetch_all_partners())
            
            # Schedule stale data check every 5 minutes
            self.scheduler.add_job(
                self._check_stale_snapshots,
                'interval',
                seconds=300,
                id='stale_data_check',
                replace_existing=True
            )
    
    def stop_scheduler(self):
        """Stop scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Data fetch scheduler stopped")
    
    async def fetch_all_partners(self):
        """Fetch data from all active partners with monitoring"""
        try:
            partners = await self.db.partner_configs.find({"isActive": True}, {"_id": 0}).to_list(1000)
            logger.info(f"Fetching data for {len(partners)} partners")
            
            tasks = []
            for partner in partners:
                partner_obj = PartnerConfig(**partner)
                tasks.append(self.fetch_partner_data(partner_obj))
            
            semaphore = asyncio.Semaphore(5)
            
            async def fetch_with_limit(partner_task):
                async with semaphore:
                    return await partner_task
            
            results = await asyncio.gather(*[fetch_with_limit(task) for task in tasks], return_exceptions=True)
            
            # Monitor sync results
            successful = [r for r in results if r and not isinstance(r, Exception)]
            failed = [i for i, r in enumerate(results) if not r or isinstance(r, Exception)]
            
            if failed:
                failed_names = [partners[i]['partnerName'] for i in failed]
                await self._create_sync_summary_alert(failed_names, len(partners))
                logger.warning(f"Failed partners: {failed_names}")
            
            # Check for stale data
            await self._check_stale_snapshots()
            
            logger.info(f"Sync completed: {len(successful)} success, {len(failed)} failed")
        
        except Exception as e:
            logger.error(f"Critical sync error: {str(e)}")
            await self._create_critical_alert(str(e))
    
    async def fetch_partner_data(self, partner: PartnerConfig):
        """Fetch data from a single partner"""
        start_time = time.time()
        
        try:
            # Update sync status to IN_PROGRESS
            await self.db.partner_configs.update_one(
                {"id": partner.id},
                {"$set": {"lastSyncStatus": SyncStatus.IN_PROGRESS.value}}
            )
            
            # Query partner database for REAL metrics
            metrics = await self._fetch_partner_metrics_real(partner)

            if metrics:
                # Calculate utilization
                utilization = (metrics['activeCalls'] / partner.concurrencyLimit * 100) if partner.concurrencyLimit > 0 else 0
                
                # Determine alert level
                alert_level, alert_message = self._calculate_alert_level(metrics, partner.concurrencyLimit, utilization)
                
                # Create snapshot with EST timestamp
                utc_now = datetime.now(timezone.utc)
                est_now = self._convert_utc_to_est(utc_now)
                
                snapshot = DashboardSnapshot(
                    partnerId=partner.id,
                    campaignsToday=metrics['campaignsToday'],
                    runningCampaigns=metrics['runningCampaigns'],
                    activeCalls=metrics['activeCalls'],
                    queuedCalls=metrics['queuedCalls'],
                    completedCallsToday=metrics.get('completedCallsToday', 0) or 0,
                    voicemailCount=metrics.get('voicemailCount', 0) or 0,
                    customerEndedCount=metrics.get('customerEndedCount', 0) or 0,
                    remainingCalls=metrics.get('remainingCalls', 0),
                    concurrencyLimit=partner.concurrencyLimit,
                    utilizationPercent=round(utilization, 2),
                    alertLevel=alert_level,
                    alertMessage=alert_message,
                    snapshotTime=utc_now,
                    snapshotTimeEST=est_now,
                    dataFetchTimeMs=int((time.time() - start_time) * 1000)
                )
                
                # Save snapshot
                snapshot_dict = snapshot.model_dump()
                snapshot_dict['snapshotTime'] = snapshot_dict['snapshotTime'].isoformat()
                if snapshot_dict.get('snapshotTimeEST'):
                    snapshot_dict['snapshotTimeEST'] = snapshot_dict['snapshotTimeEST'].isoformat()
                await self.db.dashboard_snapshots.insert_one(snapshot_dict)
                
                # Generate alerts
                await self.alert_service.generate_alert(partner, snapshot)
                
                # Update partner sync status and reset failure counter
                await self.db.partner_configs.update_one(
                    {"id": partner.id},
                    {"$set": {
                        "lastSyncStatus": SyncStatus.SUCCESS.value,
                        "lastSyncAt": datetime.now(timezone.utc).isoformat(),
                        "lastErrorMessage": None,
                        "consecutiveFailures": 0
                    }}
                )
                
                logger.info(f"Successfully fetched data for {partner.partnerName}")
                
                # Return snapshot summary for logging
                return {
                    "partner": partner.partnerName,
                    "campaignsToday": metrics['campaignsToday'],
                    "runningCampaigns": metrics['runningCampaigns'],
                    "activeCalls": metrics['activeCalls'],
                    "queuedCalls": metrics['queuedCalls'],
                    "completedCallsToday": metrics.get('completedCallsToday', 0) or 0,
                    "utilizationPercent": round(utilization, 2),
                    "alertLevel": alert_level.value
                }
            else:
                raise Exception("Failed to fetch metrics")
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching data for {partner.partnerName}: {error_msg}")
            
            # Update partner sync status and track failures
            await self.db.partner_configs.update_one(
                {"id": partner.id},
                {"$set": {
                    "lastSyncStatus": SyncStatus.FAILED.value,
                    "lastErrorMessage": error_msg,
                    "lastSyncAt": datetime.now(timezone.utc).isoformat()
                },
                "$inc": {"consecutiveFailures": 1}}
            )
            
            # Create alert for persistent failures (3+ consecutive)
            partner_config = await self.db.partner_configs.find_one({"id": partner.id}, {"consecutiveFailures": 1})
            if partner_config and partner_config.get("consecutiveFailures", 0) >= 3:
                await self._create_partner_failure_alert(partner.partnerName, error_msg)
            
            return None
    
    async def _fetch_partner_metrics_real(self, partner: PartnerConfig):
        """Fetch REAL data from partner MySQL database via SSH tunnel"""
        try:
            # Prepare all queries to execute in a single batch (single SSH connection)
            queries = [
                # Query 1: Running campaigns
                {
                    'query': "SELECT COUNT(*) as count FROM campaigns WHERE status = 'RUNNING' AND deleted = 0",
                    'params': None
                },
                # Query 2: Campaigns created today (America/New_York timezone with fallback)
                {
                    'query': """
                        SELECT COUNT(*) as count FROM campaigns 
                        WHERE (
                            (CONVERT_TZ(createdAt, '+00:00', 'America/New_York') IS NOT NULL 
                             AND DATE(CONVERT_TZ(createdAt, '+00:00', 'America/New_York')) = DATE(CONVERT_TZ(NOW(), '+00:00', 'America/New_York')))
                            OR 
                            (CONVERT_TZ(createdAt, '+00:00', 'America/New_York') IS NULL 
                             AND DATE(DATE_SUB(createdAt, INTERVAL 5 HOUR)) = DATE(DATE_SUB(NOW(), INTERVAL 5 HOUR)))
                        )
                        AND deleted = 0
                    """,
                    'params': None
                },
                # Query 3: Active calls
                {
                    'query': "SELECT COUNT(*) as count FROM calls WHERE status = 'INPROGRESS'",
                    'params': None
                },
                # Query 4: Queued calls
                {
                    'query': "SELECT COUNT(*) as count FROM calls WHERE status = 'QUEUED'",
                    'params': None
                },
                # Query 5: Completed calls today (America/New_York timezone with fallback)
                {
                    'query': """
                        SELECT 
                            COUNT(*) as total_count,
                            SUM(CASE WHEN endReason = 'voicemail' THEN 1 ELSE 0 END) as voicemail_count,
                            SUM(CASE WHEN endReason = 'customer-ended-call' THEN 1 ELSE 0 END) as customer_ended_count
                        FROM calls 
                        WHERE status = 'ENDED' 
                        AND (
                            (CONVERT_TZ(updatedAt, '+00:00', 'America/New_York') IS NOT NULL 
                             AND DATE(CONVERT_TZ(updatedAt, '+00:00', 'America/New_York')) = DATE(CONVERT_TZ(NOW(), '+00:00', 'America/New_York')))
                            OR 
                            (CONVERT_TZ(updatedAt, '+00:00', 'America/New_York') IS NULL 
                             AND DATE(DATE_SUB(updatedAt, INTERVAL 5 HOUR)) = DATE(DATE_SUB(NOW(), INTERVAL 5 HOUR)))
                        )
                    """,
                    'params': None
                },
                # Query 6: Remaining calls
                {
                    'query': """
                        SELECT COUNT(DISTINCT cc.B) as count 
                        FROM _campaigntocontact cc
                        INNER JOIN campaigns c ON cc.A = c.id
                        LEFT JOIN calls ca ON cc.B = ca.contactid AND cc.A = ca.campaignid
                        WHERE c.status = 'RUNNING' 
                        AND c.deleted = 0
                        AND (ca.status IS NULL OR ca.status IN ('QUEUED', 'INPROGRESS'))
                    """,
                    'params': None
                },
                # Query 7: Concurrency setting
                {
                    'query': "SELECT value FROM settings WHERE name = 'callConcurrency'",
                    'params': None
                },
                # Query 8: Debug - Recent campaigns with dates and timezone conversion
                {
                    'query': """
                        SELECT id, name, status, createdAt, deleted,
                               DATE(createdAt) as creation_date_utc,
                               DATE(CONVERT_TZ(createdAt, '+00:00', 'America/New_York')) as creation_date_est,
                               DATE(CONVERT_TZ(NOW(), '+00:00', 'America/New_York')) as today_est,
                               NOW() as current_utc,
                               CONVERT_TZ(NOW(), '+00:00', 'America/New_York') as current_est
                        FROM campaigns 
                        WHERE createdAt >= DATE_SUB(NOW(), INTERVAL 2 DAY)
                        ORDER BY createdAt DESC 
                        LIMIT 10
                    """,
                    'params': None
                }
            ]
            
            # Execute all queries in a single SSH connection
            results = await self.ssh_service.execute_batch_queries(partner, queries)
            
            # Extract results
            running_campaigns = results[0][0]['count'] if results[0] and len(results[0]) > 0 else 0
            
            # Extract results
            campaigns_today = results[1][0]['count'] if results[1] and len(results[1]) > 0 else 0
            active_calls = results[2][0]['count'] if results[2] and len(results[2]) > 0 else 0
            queued_calls = results[3][0]['count'] if results[3] and len(results[3]) > 0 else 0
            
            # Completed calls with breakdown
            completed_data = results[4][0] if results[4] and len(results[4]) > 0 else {}
            completed_calls_today = completed_data.get('total_count', 0)
            voicemail_count = completed_data.get('voicemail_count', 0) or 0
            customer_ended_count = completed_data.get('customer_ended_count', 0) or 0
            
            remaining_calls = results[5][0]['count'] if results[5] and len(results[5]) > 0 else 0
            
            # Debug: Log recent campaigns data with timezone info
            if results[7] and len(results[7]) > 0:
                logger.info(f"Recent campaigns for {partner.partnerName}:")
                logger.info(f"  Today EST: {results[7][0]['today_est']}, Current EST: {results[7][0]['current_est']}")
                for campaign in results[7][:5]:  # Show first 5 campaigns
                    logger.info(f"  Campaign {campaign['id']}: Created UTC: {campaign['createdAt']}, Date UTC: {campaign['creation_date_utc']}, Date EST: {campaign['creation_date_est']}, Status: {campaign['status']}, Deleted: {campaign['deleted']}")
                
                # Count campaigns created today in EST
                today_est = results[7][0]['today_est']
                campaigns_today_debug = sum(1 for c in results[7] if c['creation_date_est'] == today_est and c['deleted'] == 0)
                logger.info(f"  Debug count of campaigns today (EST): {campaigns_today_debug} (vs query result: {campaigns_today})")
            else:
                logger.info(f"No recent campaigns found for {partner.partnerName}")
            
            # Handle concurrency sync
            try:
                if results[6] and len(results[6]) > 0:
                    partner_concurrency = int(results[6][0]['value'])
                    # Update our admin MongoDB with the partner's current concurrency
                    if partner_concurrency != partner.concurrencyLimit:
                        logger.info(f"Syncing concurrency for {partner.partnerName}: {partner.concurrencyLimit} -> {partner_concurrency}")
                        await self.db.partner_configs.update_one(
                            {"id": partner.id},
                            {"$set": {"concurrencyLimit": partner_concurrency}}
                        )
                        partner.concurrencyLimit = partner_concurrency
            except Exception as e:
                logger.warning(f"Could not sync concurrency from settings table for {partner.partnerName}: {str(e)}")
                # Continue with existing concurrency limit if sync fails
            
            metrics = {
                'campaignsToday': campaigns_today,
                'runningCampaigns': running_campaigns,
                'activeCalls': active_calls,
                'queuedCalls': queued_calls,
                'completedCallsToday': completed_calls_today,
                'voicemailCount': voicemail_count,
                'customerEndedCount': customer_ended_count,
                'remainingCalls': remaining_calls,
            }
            
            logger.info(f"Fetched real metrics for {partner.partnerName}: {metrics}")
            logger.info(f"  Campaigns today query result: {campaigns_today}")
            logger.info(f"  Completed calls today query result: {completed_calls_today}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error fetching real metrics for {partner.partnerName}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _calculate_alert_level(self, metrics: dict, concurrency_limit: int, utilization: float) -> tuple:
        """Calculate alert level based on metrics"""
        queued = metrics['queuedCalls']
        active = metrics['activeCalls']
        running = metrics['runningCampaigns']
        
        # Critical alerts
        if queued > 200 and utilization < 30:
            return AlertLevel.CRITICAL, f"High queue ({queued}) with low utilization ({utilization:.1f}%)"
        if active >= concurrency_limit and queued > 100:
            return AlertLevel.CRITICAL, f"At max capacity with {queued} calls queued"
        if running > 50 and concurrency_limit < 10:
            return AlertLevel.CRITICAL, f"{running} campaigns running with only {concurrency_limit} concurrent slots"
        
        # High priority alerts
        if 100 <= queued <= 200 and utilization < 40:
            return AlertLevel.HIGH, f"Growing queue ({queued}) with low utilization ({utilization:.1f}%)"
        if 30 <= running <= 50 and concurrency_limit < 15:
            return AlertLevel.HIGH, f"{running} campaigns with limited concurrency ({concurrency_limit})"
        
        # Medium priority alerts
        if 50 <= queued <= 100 and 40 <= utilization <= 60:
            return AlertLevel.MEDIUM, f"Moderate queue ({queued}) and utilization ({utilization:.1f}%)"
        if 15 <= running <= 30 and concurrency_limit < 20:
            return AlertLevel.MEDIUM, f"{running} campaigns, consider increasing concurrency"
        
        # Idle state
        if running == 0 and active == 0 and queued == 0:
            return AlertLevel.IDLE, "No active campaigns"
        
        # Normal
        if utilization > 60 or queued < 50:
            return AlertLevel.NORMAL, "Operating normally"
        
        return AlertLevel.NORMAL, "All metrics within normal range"
    
    async def _create_partner_failure_alert(self, partner_name, error_msg):
        """Create alert for persistent partner failures"""
        try:
            from models import AlertLog
            
            alert = AlertLog(
                partnerId="SYSTEM",
                partnerName=partner_name,
                alertLevel=AlertLevel.HIGH,
                alertMessage=f"Partner {partner_name} has failed 3+ consecutive sync attempts. Error: {error_msg}",
                createdAt=datetime.now(timezone.utc),
                isResolved=False,
                isDismissed=False
            )
            
            alert_dict = alert.model_dump()
            alert_dict['createdAt'] = alert_dict['createdAt'].isoformat()
            await self.db.alert_logs.insert_one(alert_dict)
            
        except Exception as e:
            logger.error(f"Failed to create partner failure alert: {e}")
    async def _create_sync_summary_alert(self, failed_partners, total_partners):
        """Create alert for sync failures"""
        try:
            from models import AlertLog
            
            failed_count = len(failed_partners)
            alert_level = AlertLevel.CRITICAL if failed_count >= total_partners // 2 else AlertLevel.HIGH
            
            alert = AlertLog(
                partnerId="SYSTEM",
                partnerName="System",
                alertLevel=alert_level,
                alertMessage=f"Data sync failed for {failed_count}/{total_partners} partners: {', '.join(failed_partners)}",
                createdAt=datetime.now(timezone.utc),
                isResolved=False,
                isDismissed=False
            )
            
            alert_dict = alert.model_dump()
            alert_dict['createdAt'] = alert_dict['createdAt'].isoformat()
            await self.db.alert_logs.insert_one(alert_dict)
            
        except Exception as e:
            logger.error(f"Failed to create sync alert: {e}")
    
    async def _create_critical_alert(self, error_message):
        """Create critical system alert"""
        try:
            from models import AlertLog
            
            alert = AlertLog(
                partnerId="SYSTEM",
                partnerName="System",
                alertLevel=AlertLevel.CRITICAL,
                alertMessage=f"Complete sync system failure: {error_message}",
                createdAt=datetime.now(timezone.utc),
                isResolved=False,
                isDismissed=False
            )
            
            alert_dict = alert.model_dump()
            alert_dict['createdAt'] = alert_dict['createdAt'].isoformat()
            await self.db.alert_logs.insert_one(alert_dict)
            
        except Exception as e:
            logger.error(f"Failed to create critical alert: {e}")
    
    async def _check_stale_snapshots(self):
        """Check for stale partner data"""
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            partners = await self.db.partner_configs.find({"isActive": True}, {"id": 1, "partnerName": 1, "_id": 0}).to_list(1000)
            
            stale_partners = []
            for partner in partners:
                snapshot = await self.db.dashboard_snapshots.find_one(
                    {"partnerId": partner["id"]},
                    {"snapshotTime": 1, "_id": 0},
                    sort=[("snapshotTime", -1)]
                )
                
                if not snapshot:
                    stale_partners.append(partner["partnerName"])
                else:
                    snapshot_time = datetime.fromisoformat(snapshot["snapshotTime"].replace('Z', '+00:00'))
                    if snapshot_time < cutoff_time:
                        stale_partners.append(partner["partnerName"])
            
            if stale_partners:
                await self._create_stale_alert(stale_partners)
        
        except Exception as e:
            logger.error(f"Error checking stale data: {e}")
    
    async def _create_stale_alert(self, stale_partners):
        """Create alert for stale data"""
        try:
            from models import AlertLog
            
            alert = AlertLog(
                partnerId="SYSTEM",
                partnerName="System",
                alertLevel=AlertLevel.MEDIUM,
                alertMessage=f"Stale data detected: {', '.join(stale_partners)} (no updates >10min)",
                createdAt=datetime.now(timezone.utc),
                isResolved=False,
                isDismissed=False
            )
            
            alert_dict = alert.model_dump()
            alert_dict['createdAt'] = alert_dict['createdAt'].isoformat()
            await self.db.alert_logs.insert_one(alert_dict)
            
        except Exception as e:
            logger.error(f"Failed to create stale alert: {e}")