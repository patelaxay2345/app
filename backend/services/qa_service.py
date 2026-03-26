import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from models import PartnerConfig, QACallResponse, QAAnalysisData, QAReviewRequest
from services.ssh_connection import SSHConnectionService

logger = logging.getLogger(__name__)


class QAService:
    def __init__(self, ssh_service: SSHConnectionService):
        self.ssh_service = ssh_service

    async def get_qa_calls(
        self, partner: PartnerConfig, date: str, min_minutes: int = 2
    ) -> List[QACallResponse]:
        """Fetch QA calls for a given date with minimum duration filter."""
        min_seconds = min_minutes * 60

        query = """
            SELECT
                c.id,
                c.tenantId,
                c.duration,
                c.status,
                c.endReason,
                c.recordingUrl,
                c.transcript,
                c.summary,
                c.createdAt,
                c.vmBeepAt,
                c.campaignId,
                camp.name AS campaignName,
                cont.firstName AS contactFirstName,
                cont.lastName AS contactLastName,
                cont.phone AS contactPhone,
                qa.aiVoiceQuality,
                qa.aiLatency,
                qa.aiConversationQuality,
                qa.aiNotes,
                qa.humanVoiceQuality,
                qa.humanLatency,
                qa.humanConversationQuality,
                qa.humanNotes
            FROM calls c
            LEFT JOIN campaigns camp ON c.campaignId = camp.id
            LEFT JOIN contacts cont ON c.contactId = cont.id
            LEFT JOIN qa_analysis qa ON qa.callId = c.id
            WHERE DATE(c.createdAt) = %s
              AND (c.duration IS NOT NULL AND c.duration >= %s)
            ORDER BY c.createdAt DESC
        """

        results = await self.ssh_service.execute_query(
            partner, query, (date, min_seconds)
        )

        calls = []
        for row in results:
            qa_data = None
            if row.get("aiVoiceQuality") is not None or row.get("humanVoiceQuality") is not None:
                qa_data = QAAnalysisData(
                    aiVoiceQuality=row.get("aiVoiceQuality"),
                    aiLatency=row.get("aiLatency"),
                    aiConversationQuality=row.get("aiConversationQuality"),
                    aiNotes=row.get("aiNotes"),
                    humanVoiceQuality=row.get("humanVoiceQuality"),
                    humanLatency=row.get("humanLatency"),
                    humanConversationQuality=row.get("humanConversationQuality"),
                    humanNotes=row.get("humanNotes"),
                )

            created_at = row.get("createdAt")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            vm_beep_at = row.get("vmBeepAt")
            if isinstance(vm_beep_at, datetime):
                vm_beep_at = vm_beep_at.isoformat()

            calls.append(
                QACallResponse(
                    id=row["id"],
                    tenantId=row.get("tenantId"),
                    duration=row.get("duration"),
                    status=row.get("status"),
                    endReason=row.get("endReason"),
                    recordingUrl=row.get("recordingUrl"),
                    transcript=row.get("transcript"),
                    summary=row.get("summary"),
                    createdAt=created_at,
                    campaignName=row.get("campaignName"),
                    campaignId=row.get("campaignId"),
                    contactFirstName=row.get("contactFirstName"),
                    contactLastName=row.get("contactLastName"),
                    contactPhone=row.get("contactPhone"),
                    vmBeepAt=vm_beep_at,
                    qaAnalysis=qa_data,
                )
            )

        return calls

    async def get_qa_call(
        self, partner: PartnerConfig, call_id: int
    ) -> Optional[QACallResponse]:
        """Fetch a single QA call by ID."""
        query = """
            SELECT
                c.id,
                c.tenantId,
                c.duration,
                c.status,
                c.endReason,
                c.recordingUrl,
                c.transcript,
                c.summary,
                c.createdAt,
                c.vmBeepAt,
                c.campaignId,
                camp.name AS campaignName,
                cont.firstName AS contactFirstName,
                cont.lastName AS contactLastName,
                cont.phone AS contactPhone,
                qa.aiVoiceQuality,
                qa.aiLatency,
                qa.aiConversationQuality,
                qa.aiNotes,
                qa.humanVoiceQuality,
                qa.humanLatency,
                qa.humanConversationQuality,
                qa.humanNotes
            FROM calls c
            LEFT JOIN campaigns camp ON c.campaignId = camp.id
            LEFT JOIN contacts cont ON c.contactId = cont.id
            LEFT JOIN qa_analysis qa ON qa.callId = c.id
            WHERE c.id = %s
        """

        results = await self.ssh_service.execute_query(partner, query, (call_id,))

        if not results:
            return None

        row = results[0]

        qa_data = None
        if row.get("aiVoiceQuality") is not None or row.get("humanVoiceQuality") is not None:
            qa_data = QAAnalysisData(
                aiVoiceQuality=row.get("aiVoiceQuality"),
                aiLatency=row.get("aiLatency"),
                aiConversationQuality=row.get("aiConversationQuality"),
                aiNotes=row.get("aiNotes"),
                humanVoiceQuality=row.get("humanVoiceQuality"),
                humanLatency=row.get("humanLatency"),
                humanConversationQuality=row.get("humanConversationQuality"),
                humanNotes=row.get("humanNotes"),
            )

        created_at = row.get("createdAt")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        vm_beep_at = row.get("vmBeepAt")
        if isinstance(vm_beep_at, datetime):
            vm_beep_at = vm_beep_at.isoformat()

        return QACallResponse(
            id=row["id"],
            tenantId=row.get("tenantId"),
            duration=row.get("duration"),
            status=row.get("status"),
            endReason=row.get("endReason"),
            recordingUrl=row.get("recordingUrl"),
            transcript=row.get("transcript"),
            summary=row.get("summary"),
            createdAt=created_at,
            campaignName=row.get("campaignName"),
            campaignId=row.get("campaignId"),
            contactFirstName=row.get("contactFirstName"),
            contactLastName=row.get("contactLastName"),
            contactPhone=row.get("contactPhone"),
            vmBeepAt=vm_beep_at,
            qaAnalysis=qa_data,
        )

    async def update_qa_review(
        self, partner: PartnerConfig, call_id: int, review: QAReviewRequest
    ) -> bool:
        """Submit or update human QA review scores for a call."""
        # Fetch tenantId from the call record
        tenant_query = "SELECT tenantId FROM calls WHERE id = %s"
        tenant_result = await self.ssh_service.execute_query(partner, tenant_query, (call_id,))
        tenant_id = tenant_result[0].get("tenantId") if tenant_result else None

        query = """
            INSERT INTO qa_analysis (callId, tenantId, humanVoiceQuality, humanLatency, humanConversationQuality, humanNotes, createdAt, updatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                humanVoiceQuality = VALUES(humanVoiceQuality),
                humanLatency = VALUES(humanLatency),
                humanConversationQuality = VALUES(humanConversationQuality),
                humanNotes = VALUES(humanNotes),
                updatedAt = NOW()
        """

        affected = await self.ssh_service.execute_update(
            partner,
            query,
            (
                call_id,
                tenant_id,
                review.humanVoiceQuality,
                review.humanLatency,
                review.humanConversationQuality,
                review.humanNotes or "",
            ),
        )

        return affected > 0
