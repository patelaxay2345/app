from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
import logging
import asyncio
from typing import List
from models import PartnerConfig, DashboardSnapshot, AlertLevel, SyncStatus
from services.ssh_connection import SSHConnectionService
from services.alert import AlertService
import time

logger = logging.getLogger(__name__)

class DataFetchService:
    def __init__(self, db, ssh_service: SSHConnectionService, alert_service: AlertService):
        self.db = db
        self.ssh_service = ssh_service
        self.alert_service = alert_service
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
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
    
    def stop_scheduler(self):
        """Stop scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Data fetch scheduler stopped")
    
    async def fetch_all_partners(self):
        """Fetch data from all active partners"""
        try:
            # Get all active partners
            partners = await self.db.partner_configs.find({"isActive": True}, {"_id": 0}).to_list(1000)
            
            logger.info(f"Fetching data for {len(partners)} partners")
            
            # Fetch data concurrently (limit to 5 at a time)
            tasks = []
            for partner in partners:
                partner_obj = PartnerConfig(**partner)
                tasks.append(self.fetch_partner_data(partner_obj))
            
            # Execute with concurrency limit
            semaphore = asyncio.Semaphore(5)
            
            async def fetch_with_limit(partner_task):
                async with semaphore:
                    return await partner_task
            
            await asyncio.gather(*[fetch_with_limit(task) for task in tasks], return_exceptions=True)
            
            logger.info("Data fetch completed for all partners")
        
        except Exception as e:
            logger.error(f"Error in fetch_all_partners: {str(e)}")
    
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
                
                # Create snapshot
                snapshot = DashboardSnapshot(
                    partnerId=partner.id,
                    campaignsToday=metrics['campaignsToday'],
                    runningCampaigns=metrics['runningCampaigns'],
                    activeCalls=metrics['activeCalls'],
                    queuedCalls=metrics['queuedCalls'],
                    completedCallsToday=metrics.get('completedCallsToday', 0),
                    remainingCalls=metrics.get('remainingCalls', 0),
                    concurrencyLimit=partner.concurrencyLimit,
                    utilizationPercent=round(utilization, 2),
                    alertLevel=alert_level,
                    alertMessage=alert_message,
                    dataFetchTimeMs=int((time.time() - start_time) * 1000)
                )
                
                # Save snapshot
                snapshot_dict = snapshot.model_dump()
                snapshot_dict['snapshotTime'] = snapshot_dict['snapshotTime'].isoformat()
                await self.db.dashboard_snapshots.insert_one(snapshot_dict)
                
                # Generate alerts
                await self.alert_service.generate_alert(partner, snapshot)
                
                # Update partner sync status
                await self.db.partner_configs.update_one(
                    {"id": partner.id},
                    {"$set": {
                        "lastSyncStatus": SyncStatus.SUCCESS.value,
                        "lastSyncAt": datetime.now(timezone.utc).isoformat(),
                        "lastErrorMessage": None
                    }}
                )
                
                logger.info(f"Successfully fetched data for {partner.partnerName}")
            else:
                raise Exception("Failed to fetch metrics")
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching data for {partner.partnerName}: {error_msg}")
            
            # Update partner sync status
            await self.db.partner_configs.update_one(
                {"id": partner.id},
                {"$set": {
                    "lastSyncStatus": SyncStatus.FAILED.value,
                    "lastErrorMessage": error_msg,
                    "lastSyncAt": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    async def _fetch_partner_metrics_real(self, partner: PartnerConfig):
        """Fetch REAL data from partner MySQL database via SSH tunnel"""
        try:
            # Query 1: Running campaigns (RUNNING status)
            result = await self.ssh_service.execute_query(
                partner,
                "SELECT COUNT(*) as count FROM campaigns WHERE status = 'RUNNING' AND deleted = 0"
            )
            running_campaigns = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 2: Campaigns created today
            result = await self.ssh_service.execute_query(
                partner,
                "SELECT COUNT(*) as count FROM campaigns WHERE DATE(createdAt) = CURDATE() AND deleted = 0"
            )
            campaigns_today = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 3: Active calls (INPROGRESS status)
            result = await self.ssh_service.execute_query(
                partner,
                "SELECT COUNT(*) as count FROM calls WHERE status = 'INPROGRESS'"
            )
            active_calls = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 4: Queued calls (QUEUED status)
            result = await self.ssh_service.execute_query(
                partner,
                "SELECT COUNT(*) as count FROM calls WHERE status = 'QUEUED'"
            )
            queued_calls = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 5: Completed calls today (COMPLETED status)
            result = await self.ssh_service.execute_query(
                partner,
                "SELECT COUNT(*) as count FROM calls WHERE status = 'COMPLETED' AND DATE(updatedAt) = CURDATE()"
            )
            completed_calls_today = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 6: Remaining calls (total contacts in running campaigns minus completed/failed calls)
            result = await self.ssh_service.execute_query(
                partner,
                """
                SELECT COUNT(DISTINCT cc.contactid) as count 
                FROM campaigncontacts cc
                INNER JOIN campaigns c ON cc.campaignid = c.id
                LEFT JOIN calls ca ON cc.contactid = ca.contactid AND cc.campaignid = ca.campaignid
                WHERE c.status = 'RUNNING' 
                AND c.deleted = 0
                AND (ca.status IS NULL OR ca.status IN ('QUEUED', 'INPROGRESS'))
                """
            )
            remaining_calls = result[0]['count'] if result and len(result) > 0 else 0
            
            # Query 7: Sync concurrency from settings table
            try:
                result = await self.ssh_service.execute_query(
                    partner,
                    "SELECT value FROM settings WHERE name = 'callConcurrency'"
                )
                if result and len(result) > 0:
                    partner_concurrency = int(result[0]['value'])
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
                'remainingCalls': remaining_calls,
            }
            
            logger.info(f"Fetched real metrics for {partner.partnerName}: {metrics}")
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
