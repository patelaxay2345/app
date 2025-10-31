from datetime import datetime, timezone, timedelta
import logging
from models import PartnerConfig, DashboardSnapshot, AlertLog, AlertLevel
from services.email_service import EmailService

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db, email_service: EmailService):
        self.db = db
        self.email_service = email_service
    
    async def generate_alert(self, partner: PartnerConfig, snapshot: DashboardSnapshot):
        """Generate alert based on snapshot metrics"""
        try:
            # Check if there's an existing active alert for this partner
            existing_alert = await self.db.alert_logs.find_one(
                {
                    "partnerId": partner.id,
                    "isResolved": False,
                    "isDismissed": False
                },
                {"_id": 0}
            )
            
            # If alert level is NORMAL or IDLE, resolve existing alerts
            if snapshot.alertLevel in [AlertLevel.NORMAL, AlertLevel.IDLE]:
                if existing_alert:
                    await self.db.alert_logs.update_one(
                        {"id": existing_alert['id']},
                        {"$set": {
                            "isResolved": True,
                            "resolvedAt": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    logger.info(f"Resolved alert for {partner.partnerName}")
                return
            
            # Create new alert if level changed or no existing alert
            if not existing_alert or existing_alert['alertLevel'] != snapshot.alertLevel.value:
                # Resolve old alert if exists
                if existing_alert:
                    await self.db.alert_logs.update_one(
                        {"id": existing_alert['id']},
                        {"$set": {
                            "isResolved": True,
                            "resolvedAt": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                
                # Create new alert
                alert = AlertLog(
                    partnerId=partner.id,
                    alertLevel=snapshot.alertLevel,
                    alertMessage=snapshot.alertMessage or "Alert triggered"
                )
                
                alert_dict = alert.model_dump()
                alert_dict['createdAt'] = alert_dict['createdAt'].isoformat()
                
                await self.db.alert_logs.insert_one(alert_dict)
                
                logger.info(f"Created {snapshot.alertLevel.value} alert for {partner.partnerName}")
                
                # Send email for critical alerts
                if snapshot.alertLevel == AlertLevel.CRITICAL:
                    # Check if email was sent recently (within 1 hour)
                    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                    recent_email = await self.db.alert_logs.find_one({
                        "partnerId": partner.id,
                        "emailSent": True,
                        "lastEmailSentAt": {"$gte": one_hour_ago.isoformat()}
                    })
                    
                    if not recent_email:
                        # Send email
                        email_sent = await self.email_service.send_alert_email(
                            partner.partnerName,
                            snapshot.alertLevel.value,
                            snapshot.alertMessage or "Critical alert",
                            {
                                "queuedCalls": snapshot.queuedCalls,
                                "activeCalls": snapshot.activeCalls,
                                "utilization": snapshot.utilizationPercent,
                                "runningCampaigns": snapshot.runningCampaigns
                            }
                        )
                        
                        if email_sent:
                            await self.db.alert_logs.update_one(
                                {"id": alert_dict['id']},
                                {"$set": {
                                    "emailSent": True,
                                    "lastEmailSentAt": datetime.now(timezone.utc).isoformat()
                                }}
                            )
        
        except Exception as e:
            logger.error(f"Error generating alert for {partner.partnerName}: {str(e)}")
