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

from models import PartnerConfig
from services.ssh_connection import SSHConnectionService
from services.email_service import EmailService
from services.qa_service import parse_messages_to_transcript

logger = logging.getLogger(__name__)

OPENROUTER_MODEL = "google/gemini-2.5-flash:nitro"
MAX_AUDIO_SIZE_MB = 20
TRANSCRIPTION_TIMEOUT = 300  # 5 minutes
ANALYSIS_TIMEOUT = 120  # 2 minutes
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
SAVE_BATCH_SIZE = 10


class QAAnalysisService:
    def __init__(self, db, ssh_service: SSHConnectionService, email_service: EmailService):
        self.db = db
        self.ssh_service = ssh_service
        self.email_service = email_service

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.openrouter = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://jobtalk.ai/",
                "X-Title": "qaAnalysis",
            },
        )

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

    async def _process_single_call(
        self, call_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Score a single call using LLM. Uses call data provided directly (no SSH fetch).
        Returns scores without saving to partner DB — batch_analyze handles batched saves.
        """
        call_id = call_data["id"]

        try:
            transcript = call_data.get("transcript")
            summary = call_data.get("summary")
            recording_url = call_data.get("recordingUrl")

            # Transcribe if no transcript exists
            if not transcript and recording_url:
                logger.info(f"Transcribing call {call_id}...")
                transcript = await self.transcribe_audio(recording_url)

            # Analyze with retries
            scores = None
            last_error = None
            for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                try:
                    scores = await self.analyze_call(
                        transcript, summary, call_data.get("duration"), call_data.get("endReason")
                    )
                    if scores:
                        break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Analysis attempt {attempt}/{MAX_RETRY_ATTEMPTS} failed for call {call_id}: {e}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

            if not scores:
                scores = {
                    "voiceQuality": 0,
                    "latency": 0,
                    "conversationQuality": 0,
                    "notes": f"Analysis failed: {last_error or 'No transcript/summary available'}",
                }

            return {
                "callId": call_id,
                "status": "completed",
                "scores": scores,
                "tenantId": call_data.get("tenantId"),
                "call": call_data,
            }

        except Exception as e:
            logger.error(f"Error processing call {call_id}: {str(e)}")
            return {"callId": call_id, "status": "failed", "error": str(e)}

    async def _flush_batch_save(
        self, partner: PartnerConfig, pending_saves: List[Dict[str, Any]]
    ):
        """Save scores for a batch of calls in a single SSH tunnel."""
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

        queries = []
        for item in pending_saves:
            scores = item["scores"]
            queries.append({
                "query": upsert_query,
                "params": (
                    item["callId"],
                    item.get("tenantId"),
                    scores.get("voiceQuality"),
                    scores.get("latency"),
                    scores.get("conversationQuality"),
                    scores.get("notes", ""),
                ),
            })

        try:
            await self.ssh_service.execute_batch_updates(partner, queries)
            logger.info(f"Batch saved {len(queries)} call scores in single tunnel")
        except Exception as e:
            logger.error(f"Batch save failed for {len(queries)} calls: {e}")

    async def batch_analyze(
        self, partner: PartnerConfig, calls_data: List[Dict[str, Any]], partner_name: str,
        report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process multiple calls: LLM scoring with batched DB saves via single SSH tunnels."""
        total = len(calls_data)
        logger.info(f"Starting batch analysis for {partner_name}: {total} calls")

        # Process calls sequentially (LLM scoring) and collect results for batched saves
        results = []
        pending_saves = []
        completed = 0
        failed = 0

        for call_data in calls_data:
            result = await self._process_single_call(call_data)
            results.append(result)

            if result["status"] == "completed":
                completed += 1
                pending_saves.append(result)
            else:
                failed += 1

            # Flush batch saves when batch is full
            if len(pending_saves) >= SAVE_BATCH_SIZE:
                await self._flush_batch_save(partner, pending_saves)
                pending_saves = []

        # Flush remaining saves
        if pending_saves:
            await self._flush_batch_save(partner, pending_saves)

        logger.info(f"Batch analysis complete for {partner_name}: {completed} completed, {failed} failed")

        # Send final summary email with all analyzed calls
        await self._send_analysis_summary_email(results, partner_name, report_date)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "results": results,
        }

    async def batch_analyze_legacy(
        self, partner: PartnerConfig, call_ids: List[int], partner_name: str,
        report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Legacy path: fetch data via SSH per call. Used when frontend sends only call IDs."""
        total = len(call_ids)
        logger.info(f"Starting legacy batch analysis for {partner_name}: {total} calls")

        results = []
        completed = 0
        failed = 0
        for cid in call_ids:
            result = await self._process_single_call_legacy(partner, cid)
            results.append(result)
            if result["status"] == "completed":
                completed += 1
            else:
                failed += 1

        logger.info(f"Legacy batch analysis complete for {partner_name}: {completed} completed, {failed} failed")

        # Send final summary email with all analyzed calls
        await self._send_analysis_summary_email(results, partner_name, report_date)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "results": results,
        }

    async def _process_single_call_legacy(
        self, partner: PartnerConfig, call_id: int
    ) -> Dict[str, Any]:
        """Legacy: fetch data via SSH, analyze, save via SSH. One tunnel per operation."""
        try:
            query = """
                SELECT c.id, c.tenantId, c.duration, c.endReason, c.recordingUrl,
                       c.messages, c.summary,
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
            transcript = parse_messages_to_transcript(call.get("messages"))
            summary = call.get("summary")
            recording_url = call.get("recordingUrl")

            if not transcript and recording_url:
                logger.info(f"Transcribing call {call_id}...")
                transcript = await self.transcribe_audio(recording_url)

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
                scores = {
                    "voiceQuality": 0,
                    "latency": 0,
                    "conversationQuality": 0,
                    "notes": f"Analysis failed: {last_error or 'No transcript/summary available'}",
                }

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
                partner, upsert_query,
                (call_id, tenant_id, scores.get("voiceQuality"), scores.get("latency"),
                 scores.get("conversationQuality"), scores.get("notes", "")),
            )

            return {"callId": call_id, "status": "completed", "scores": scores, "call": call}

        except Exception as e:
            logger.error(f"Error processing call {call_id}: {str(e)}")
            return {"callId": call_id, "status": "failed", "error": str(e)}

    async def _get_qa_report_recipients(self) -> List[str]:
        """Fetch QA report email recipients from system settings."""
        try:
            setting = await self.db.system_settings.find_one(
                {"settingKey": "qaReportRecipients"}, {"_id": 0}
            )
            if setting and setting.get("settingValue"):
                recipients = [e.strip() for e in str(setting["settingValue"]).split(",") if e.strip()]
                if recipients:
                    return recipients
        except Exception as e:
            logger.warning(f"Failed to fetch QA report recipients setting: {e}")
        return None

    async def _send_analysis_summary_email(
        self, results: List[Dict[str, Any]], partner_name: str,
        report_date: Optional[str] = None
    ):
        """Send a final summary email after all calls in a batch have been analyzed."""
        try:
            email_date = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            recipients = await self._get_qa_report_recipients()

            # Build call list in the format send_qa_report_email expects
            email_calls = []
            for r in results:
                call = r.get("call") or {}
                scores = r.get("scores") or {}
                email_calls.append({
                    "id": r.get("callId"),
                    "duration": call.get("duration"),
                    "campaignName": call.get("campaignName"),
                    "contactFirstName": call.get("contactFirstName"),
                    "contactLastName": call.get("contactLastName"),
                    "contactPhone": call.get("contactPhone"),
                    "qaAnalysis": {
                        "aiVoiceQuality": scores.get("voiceQuality"),
                        "aiLatency": scores.get("latency"),
                        "aiConversationQuality": scores.get("conversationQuality"),
                        "aiNotes": scores.get("notes", ""),
                    },
                })

            completed_count = sum(1 for r in results if r.get("status") == "completed")
            failed_count = sum(1 for r in results if r.get("status") == "failed")
            summary_msg = f"AI analysis complete: {completed_count} scored, {failed_count} failed out of {len(results)} total calls."

            await self.email_service.send_qa_report_email(
                calls=email_calls,
                date=email_date,
                to_addresses=recipients,
                partner_name=partner_name,
                custom_message=summary_msg,
            )
            logger.info(f"QA analysis summary email sent for {partner_name} ({len(email_calls)} calls)")

        except Exception as e:
            logger.error(f"Failed to send QA analysis summary email: {str(e)}")
