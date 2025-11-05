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
            # First, get the old value for audit trail
            get_old_value_query = """
                SELECT value FROM settings WHERE name = 'callConcurrency'
            """
            
            old_value_result = await self.ssh_service.execute_query(partner, get_old_value_query)
            old_value = old_value_result[0]['value'] if old_value_result and len(old_value_result) > 0 else None
            
            # Update settings table
            update_query = """
                UPDATE settings 
                SET value = %s 
                WHERE name = 'callConcurrency'
            """
            
            # Execute update query via SSH tunnel
            affected_rows = await self.ssh_service.execute_update(partner, update_query, (new_limit,))
            
            if affected_rows > 0:
                # Try to insert audit log - handle different table structures
                try:
                    # Try with 'name' column first (some tables might have it)
                    audit_query = """
                        INSERT INTO settings_auditlogs (userid, oldvalue, newvalue, createdat)
                        VALUES (9999999999, %s, %s, NOW())
                    """
                    audit_affected = await self.ssh_service.execute_update(
                        partner, 
                        audit_query, 
                        (old_value, new_limit)
                    )
                    
                    if audit_affected > 0:
                        logger.info(f"Successfully synced concurrency {new_limit} to partner {partner.partnerName} with audit log")
                        return {"success": True, "message": "Synced to partner database with audit log"}
                    else:
                        logger.warning(f"Concurrency updated but audit log returned 0 rows for partner {partner.partnerName}")
                        return {"success": True, "message": "Concurrency updated (audit log warning)"}
                        
                except Exception as audit_error:
                    logger.warning(f"Concurrency updated but audit log failed for partner {partner.partnerName}: {str(audit_error)}")
                    return {"success": True, "message": f"Concurrency updated (audit log failed: {str(audit_error)})"}
            else:
                return {"success": False, "error": "No rows updated - callConcurrency setting might not exist"}
        
        except Exception as e:
            logger.error(f"Error syncing to partner database: {str(e)}")
            return {"success": False, "error": str(e)}
        
        except Exception as e:
            logger.error(f"Error syncing to partner database: {str(e)}")
            return {"success": False, "error": str(e)}
