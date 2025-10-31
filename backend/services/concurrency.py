from datetime import datetime, timezone
import logging
from models import PartnerConfig, ConcurrencyHistory
from services.ssh_connection import SSHConnectionService
import uuid

logger = logging.getLogger(__name__)

class ConcurrencyService:
    def __init__(self, db, ssh_service: SSHConnectionService):
        self.db = db
        self.ssh_service = ssh_service
    
    async def update_concurrency(self, partner_id: str, new_limit: int, reason: str, changed_by: str) -> dict:
        """Update concurrency limit for a partner"""
        try:
            # Get partner
            partner_data = await self.db.partner_configs.find_one({"id": partner_id}, {"_id": 0})
            if not partner_data:
                return {"success": False, "message": "Partner not found"}
            
            partner = PartnerConfig(**partner_data)
            old_limit = partner.concurrencyLimit
            
            # Update in admin database
            await self.db.partner_configs.update_one(
                {"id": partner_id},
                {"$set": {
                    "concurrencyLimit": new_limit,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Create history record
            history = ConcurrencyHistory(
                partnerId=partner_id,
                oldLimit=old_limit,
                newLimit=new_limit,
                reason=reason,
                changedBy=changed_by
            )
            
            history_dict = history.model_dump()
            history_dict['changedAt'] = history_dict['changedAt'].isoformat()
            
            await self.db.concurrency_history.insert_one(history_dict)
            
            # Sync to partner database
            sync_result = await self._sync_to_partner_db(partner, new_limit)
            
            # Update history with sync result
            await self.db.concurrency_history.update_one(
                {"id": history_dict['id']},
                {"$set": {
                    "syncedToPartner": sync_result['success'],
                    "syncError": sync_result.get('error'),
                    "syncedAt": datetime.now(timezone.utc).isoformat() if sync_result['success'] else None
                }}
            )
            
            return {
                "success": True,
                "message": f"Concurrency updated from {old_limit} to {new_limit}",
                "syncedToPartner": sync_result['success'],
                "syncMessage": sync_result.get('message', '')
            }
        
        except Exception as e:
            logger.error(f"Error updating concurrency for partner {partner_id}: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _sync_to_partner_db(self, partner: PartnerConfig, new_limit: int) -> dict:
        """Sync concurrency setting to partner's MySQL database"""
        try:
            # For mock implementation, just return success
            # In production, this would execute:
            # INSERT INTO settings (name, value, tenantId, createdAt, updatedAt)
            # VALUES ('CALL_CONCURRENCY', new_limit, partner.tenantId, NOW(), NOW())
            # ON DUPLICATE KEY UPDATE value = VALUES(value), updatedAt = NOW()
            
            query = """
                INSERT INTO settings (name, value, tenantId, createdAt, updatedAt)
                VALUES ('CALL_CONCURRENCY', %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE value = VALUES(value), updatedAt = NOW()
            """
            
            # Uncomment when real partner databases are available
            # result = await self.ssh_service.execute_query(partner, query, (new_limit, partner.tenantId))
            # if result is not None:
            #     return {"success": True, "message": "Synced to partner database"}
            # else:
            #     return {"success": False, "error": "Query execution failed"}
            
            # Mock response for development
            logger.info(f"Mock: Would sync concurrency {new_limit} to partner {partner.partnerName}")
            return {"success": True, "message": "Mock sync successful (no real partner DB)"}
        
        except Exception as e:
            logger.error(f"Error syncing to partner database: {str(e)}")
            return {"success": False, "error": str(e)}
