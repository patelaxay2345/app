import os
import re
import json
import base64
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from openai import OpenAI

from models import PartnerConfig, QAAnalysisJobStatus
from services.ssh_connection import SSHConnectionService
from services.email_service import EmailService

logger = logging.getLogger(__name__)

OPENROUTER_MODEL = "google/gemini-2.5-flash:nitro"
MAX_AUDIO_SIZE_MB = 20
TRANSCRIPTION_TIMEOUT = 300  # 5 minutes
ANALYSIS_TIMEOUT = 120  # 2 minutes
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
URGENT_SCORE_THRESHOLD = 3


class QAAnalysisService:
    def __init__(self, db, ssh_service: SSHConnectionService, email_service: EmailService):
        self.db = db
        self.ssh_service = ssh_service
        self.email_service = email_service
        self._event_queues: Dict[str, asyncio.Queue] = {}

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.openrouter = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://jobtalk.ai/",
                "X-Title": "qaAnalysis",
            },
        )

    def subscribe(self, partner_id: str) -> asyncio.Queue:
        if partner_id not in self._event_queues:
            self._event_queues[partner_id] = asyncio.Queue(maxsize=1000)
        return self._event_queues[partner_id]

    def unsubscribe(self, partner_id: str):
        self._event_queues.pop(partner_id, None)

    async def _emit(self, partner_id: str, event: str, data: dict):
        queue = self._event_queues.get(partner_id)
        if queue and not queue.full():
            await queue.put({"event": event, "data": data})

    async def transcribe_audio(self, recording_url: str) -> Optional[str]:
        """Download audio and transcribe using Gemini via OpenRouter."""
        if not recording_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(recording_url)
                if resp.status_code != 200:
                    logger.warning(f"Failed to download audio: HTTP {resp.status_code}")
                    return None

                audio_bytes = resp.content
                size_mb = len(audio_bytes) / (1024 * 1024)
                if size_mb > MAX_AUDIO_SIZE_MB:
                    logger.warning(f"Audio too large ({size_mb:.1f}MB), skipping transcription")
                    return None

                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            # Run blocking OpenAI call in thread pool
            def _transcribe():
                return self.openrouter.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_b64,
                                        "format": "mp3",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Transcribe this audio recording exactly as spoken. Output only the transcription text, nothing else.",
                                },
                            ],
                        }
                    ],
                    timeout=TRANSCRIPTION_TIMEOUT,
                )

            response = await asyncio.to_thread(_transcribe)
            transcript = (response.choices[0].message.content or "").strip()
            return transcript if transcript else None

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None

    async def analyze_call(
        self, transcript: Optional[str], summary: Optional[str],
        duration: Optional[int], end_reason: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Send transcript to LLM for QA scoring."""
        source_parts = []
        if transcript:
            source_parts.append("transcript")
        if summary:
            source_parts.append("summary")
        source = " + ".join(source_parts) if source_parts else "none"

        text_for_analysis = ""
        if summary:
            text_for_analysis += f"Summary: {summary[:400]}\n"
        if transcript:
            text_for_analysis += f"Transcript: {transcript[:2500]}"

        if not text_for_analysis.strip():
            logger.warning("No transcript or summary available for analysis")
            return None

        prompt = (
            "You are a QA analyst reviewing a recruitment AI voice call. "
            "Score the call on three dimensions from 1 to 10 (10 = best). "
            'Respond ONLY with valid JSON:\n'
            '{"voiceQuality": <1-10>, "latency": <1-10>, "conversationQuality": <1-10>, "notes": "<one sentence issue summary>"}\n\n'
            "Scoring:\n"
            "- voiceQuality: audio/speech clarity, coherence, absence of artifacts or garbled text\n"
            "- latency: natural pacing, absence of awkward pauses, AI responsiveness\n"
            "- conversationQuality: goal achievement, professionalism, candidate engagement\n\n"
            f"Duration: {duration or 0}s | End reason: {end_reason or 'unknown'} | Source: {source}\n"
            f"{text_for_analysis}"
        )

        try:
            def _analyze():
                return self.openrouter.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=ANALYSIS_TIMEOUT,
                )

            response = await asyncio.to_thread(_analyze)
            content = (response.choices[0].message.content or "").strip()

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                logger.error(f"No JSON in analysis response: {content[:200]}")
                return None

            scores = json.loads(json_match.group(0))
            return scores

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return None

    async def process_single_call(
        self, partner: PartnerConfig, call_id: int, partner_name: str
    ) -> Dict[str, Any]:
        """Process a single call: fetch data, transcribe if needed, analyze, save scores."""
        job_id = f"{partner.id}_{call_id}"

        # Update job status to processing
        await self.db.qa_analysis_jobs.update_one(
            {"jobId": job_id},
            {"$set": {"status": QAAnalysisJobStatus.PROCESSING, "updatedAt": datetime.now(timezone.utc).isoformat()}},
        )
        await self._emit(partner.id, "processing", {"callId": call_id})

        try:
            # Fetch call data from partner DB
            query = """
                SELECT c.id, c.tenantId, c.duration, c.endReason, c.recordingUrl,
                       c.transcript, c.summary,
                       camp.name AS campaignName,
                       cont.firstName AS contactFirstName,
                       cont.lastName AS contactLastName,
                       cont.phone AS contactPhone
                FROM calls c
                LEFT JOIN campaigns camp ON c.campaignId = camp.id
                LEFT JOIN contacts cont ON c.contactId = cont.id
                WHERE c.id = %s
            """
            results = await self.ssh_service.execute_query(partner, query, (call_id,))
            if not results:
                raise Exception(f"Call {call_id} not found in partner database")

            call = results[0]
            transcript = call.get("transcript")
            summary = call.get("summary")
            recording_url = call.get("recordingUrl")

            # Transcribe if no transcript exists
            if not transcript and recording_url:
                logger.info(f"Transcribing call {call_id}...")
                transcript = await self.transcribe_audio(recording_url)

            # Analyze
            scores = None
            last_error = None
            for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                try:
                    scores = await self.analyze_call(
                        transcript, summary, call.get("duration"), call.get("endReason")
                    )
                    if scores:
                        break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Analysis attempt {attempt}/{MAX_RETRY_ATTEMPTS} failed for call {call_id}: {e}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

            if not scores:
                # Save fallback zeros
                scores = {
                    "voiceQuality": 0,
                    "latency": 0,
                    "conversationQuality": 0,
                    "notes": f"Analysis failed: {last_error or 'No transcript/summary available'}",
                }

            # Write scores to partner DB
            tenant_id = call.get("tenantId")
            upsert_query = """
                INSERT INTO qa_analysis (callId, tenantId, aiVoiceQuality, aiLatency, aiConversationQuality, aiNotes, createdAt, updatedAt)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    aiVoiceQuality = VALUES(aiVoiceQuality),
                    aiLatency = VALUES(aiLatency),
                    aiConversationQuality = VALUES(aiConversationQuality),
                    aiNotes = VALUES(aiNotes),
                    updatedAt = NOW()
            """
            await self.ssh_service.execute_update(
                partner,
                upsert_query,
                (
                    call_id,
                    tenant_id,
                    scores.get("voiceQuality"),
                    scores.get("latency"),
                    scores.get("conversationQuality"),
                    scores.get("notes", ""),
                ),
            )

            # Check for urgent scores
            score_values = [
                scores.get("voiceQuality"),
                scores.get("latency"),
                scores.get("conversationQuality"),
            ]
            valid_scores = [s for s in score_values if s is not None and s > 0]
            if valid_scores and any(s <= URGENT_SCORE_THRESHOLD for s in valid_scores):
                await self._send_urgent_alert(call, scores, partner_name)

            # Update job status to completed
            await self.db.qa_analysis_jobs.update_one(
                {"jobId": job_id},
                {
                    "$set": {
                        "status": QAAnalysisJobStatus.COMPLETED,
                        "scores": scores,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            return {"callId": call_id, "status": "completed", "scores": scores}

        except Exception as e:
            logger.error(f"Error processing call {call_id}: {str(e)}")
            await self.db.qa_analysis_jobs.update_one(
                {"jobId": job_id},
                {
                    "$set": {
                        "status": QAAnalysisJobStatus.FAILED,
                        "error": str(e),
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            return {"callId": call_id, "status": "failed", "error": str(e)}

    async def batch_analyze(
        self, partner: PartnerConfig, call_ids: List[int], partner_name: str
    ) -> Dict[str, Any]:
        """Queue and process multiple calls for analysis."""
        now = datetime.now(timezone.utc).isoformat()

        # Create job records in MongoDB
        for cid in call_ids:
            job_id = f"{partner.id}_{cid}"
            await self.db.qa_analysis_jobs.update_one(
                {"jobId": job_id},
                {
                    "$set": {
                        "jobId": job_id,
                        "partnerId": partner.id,
                        "partnerName": partner_name,
                        "callId": cid,
                        "status": QAAnalysisJobStatus.QUEUED,
                        "error": None,
                        "scores": None,
                        "updatedAt": now,
                    },
                    "$setOnInsert": {"createdAt": now},
                },
                upsert=True,
            )

        total = len(call_ids)
        await self._emit(partner.id, "start", {"total": total, "pending": total, "callIds": call_ids})

        # Process calls sequentially (each opens an SSH tunnel)
        results = []
        completed = 0
        failed = 0
        for cid in call_ids:
            result = await self.process_single_call(partner, cid, partner_name)
            results.append(result)
            if result["status"] == "completed":
                completed += 1
            else:
                failed += 1
            pending = total - completed - failed
            await self._emit(partner.id, "progress", {
                "callId": cid,
                "callStatus": result["status"],
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "total": total,
            })

        await self._emit(partner.id, "done", {"total": total, "completed": completed, "failed": failed})
        self.unsubscribe(partner.id)

        # Clean up finished jobs so they don't pollute next run's status
        await self.db.qa_analysis_jobs.delete_many({
            "partnerId": partner.id,
            "status": {"$in": [QAAnalysisJobStatus.COMPLETED, QAAnalysisJobStatus.FAILED]},
        })

        return {
            "total": len(call_ids),
            "completed": completed,
            "failed": failed,
            "results": results,
        }

    async def get_analysis_status(self, partner_id: str) -> List[Dict[str, Any]]:
        """Get active (queued/processing) analysis jobs for a partner."""
        jobs = (
            await self.db.qa_analysis_jobs.find(
                {
                    "partnerId": partner_id,
                    "status": {"$in": [QAAnalysisJobStatus.QUEUED, QAAnalysisJobStatus.PROCESSING]},
                },
                {"_id": 0},
            )
            .sort("updatedAt", -1)
            .to_list(100)
        )
        return jobs

    async def _send_urgent_alert(
        self, call: Dict[str, Any], scores: Dict[str, Any], partner_name: str
    ):
        """Send urgent email when any score is <= 3."""
        try:
            contact_name = f"{call.get('contactFirstName', '') or ''} {call.get('contactLastName', '') or ''}".strip()
            contact_phone = call.get("contactPhone", "N/A")
            campaign_name = call.get("campaignName", "N/A")
            duration = call.get("duration", 0)
            call_id = call.get("id", "N/A")

            def score_color(s):
                if s is None:
                    return "#999"
                return "#c0392b" if s <= URGENT_SCORE_THRESHOLD else "#27ae60"

            vq = scores.get("voiceQuality")
            lat = scores.get("latency")
            cq = scores.get("conversationQuality")
            notes = scores.get("notes", "")

            subject = f"QA Alert — Call #{call_id} scored <= 3 ({partner_name})"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #c0392b;">QA Alert — Low Score Detected</h2>
                <p><strong>Partner:</strong> {partner_name}</p>
                <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Call ID</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{call_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Contact</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{contact_name} ({contact_phone})</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Campaign</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{campaign_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Duration</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{duration}s</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Voice Quality</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; color: {score_color(vq)};"><strong>{vq}</strong>/10</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Latency</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; color: {score_color(lat)};"><strong>{lat}</strong>/10</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Conversation Quality</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; color: {score_color(cq)};"><strong>{cq}</strong>/10</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Notes</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{notes}</td>
                    </tr>
                </table>
                <p style="margin-top: 16px; color: #666;"><em>This is an automated QA alert from JobTalk Admin Dashboard.</em></p>
            </body>
            </html>
            """

            text_body = (
                f"QA Alert — Call #{call_id} scored <= 3 ({partner_name})\n\n"
                f"Contact: {contact_name} ({contact_phone})\n"
                f"Campaign: {campaign_name}\n"
                f"Duration: {duration}s\n"
                f"Voice Quality: {vq}/10\n"
                f"Latency: {lat}/10\n"
                f"Conversation Quality: {cq}/10\n"
                f"Notes: {notes}\n"
            )

            to_email = "taj@aptask.com"

            self.email_service.send_email(
                to_addresses=[to_email],
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            logger.info(f"Urgent QA alert sent for call {call_id}")

        except Exception as e:
            logger.error(f"Failed to send urgent QA alert: {str(e)}")
