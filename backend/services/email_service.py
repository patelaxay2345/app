import smtplib
import ssl
import asyncio
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'email-smtp.us-east-1.amazonaws.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 465))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('SMTP_FROM_EMAIL', 'noreply@jobtalk.com')
        self.app_name = os.environ.get('APP_NAME', 'JobTalk')

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        text_body: str,
        cc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
    ) -> bool:
        """Send email via SES SMTP.

        attachments: list of (filename, content_bytes, mime_type) tuples, e.g.
                     [("report.csv", b"id,name\\n1,John", "text/csv")]
        """
        t_start = time.time()
        logger.info(f"[QA-EMAIL] ====== send_email START ======")
        logger.info(f"[QA-EMAIL] To: {to_addresses}, CC: {cc_addresses}, Subject: {subject[:80]}")
        logger.info(f"[QA-EMAIL] SMTP config: host={self.smtp_host}, port={self.smtp_port}, from={self.from_email}")
        try:
            t0 = time.time()

            if attachments:
                # mixed: body + attachments at top level
                msg = MIMEMultipart('mixed')
                body_part = MIMEMultipart('alternative')
                body_part.attach(MIMEText(text_body, 'plain'))
                body_part.attach(MIMEText(html_body, 'html'))
                msg.attach(body_part)

                for filename, content, mime_type in attachments:
                    maintype, subtype = mime_type.split('/', 1)
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(part)
            else:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(text_body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))

            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_addresses)
            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)

            all_recipients = list(to_addresses)
            if cc_addresses:
                all_recipients.extend(cc_addresses)
            logger.info(f"[QA-EMAIL] Message built in {time.time() - t0:.3f}s | HTML size: {len(html_body)} chars")

            context = ssl.create_default_context()

            t1 = time.time()
            if self.smtp_port == 465:
                logger.info(f"[QA-EMAIL] Connecting via SMTP_SSL (port 465) to {self.smtp_host} ...")
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context)
                logger.info(f"[QA-EMAIL] SMTP_SSL connect done in {time.time() - t1:.3f}s")
            else:
                logger.info(f"[QA-EMAIL] Connecting via SMTP + STARTTLS (port {self.smtp_port}) to {self.smtp_host} ...")
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                logger.info(f"[QA-EMAIL] SMTP connect done in {time.time() - t1:.3f}s")

                t2 = time.time()
                server.starttls(context=context)
                logger.info(f"[QA-EMAIL] STARTTLS done in {time.time() - t2:.3f}s")

            t3 = time.time()
            server.login(self.smtp_username, self.smtp_password)
            logger.info(f"[QA-EMAIL] Login done in {time.time() - t3:.3f}s")

            t4 = time.time()
            server.sendmail(self.from_email, all_recipients, msg.as_string())
            logger.info(f"[QA-EMAIL] sendmail done in {time.time() - t4:.3f}s | recipients: {len(all_recipients)}")

            t5 = time.time()
            server.quit()
            logger.info(f"[QA-EMAIL] SMTP quit done in {time.time() - t5:.3f}s")

            total = time.time() - t_start
            logger.info(f"[QA-EMAIL] ====== send_email SUCCESS in {total:.3f}s ======")
            return True

        except Exception as e:
            total = time.time() - t_start
            logger.error(f"[QA-EMAIL] ====== send_email FAILED after {total:.3f}s ======")
            logger.error(f"[QA-EMAIL] Error: {type(e).__name__}: {str(e)}")
            return False

    async def send_alert_email(self, partner_name: str, alert_level: str, message: str, metrics: Dict[str, Any]) -> bool:
        """Send alert email via SES SMTP"""
        try:
            subject = f"[{self.app_name}] {alert_level} Alert: {partner_name}"
            
            html_body = f"""
            <html>
            <head></head>
            <body>
                <h2 style="color: #DC2626;">{alert_level} Alert</h2>
                <p><strong>Partner:</strong> {partner_name}</p>
                <p><strong>Alert Message:</strong> {message}</p>
                
                <h3>Current Metrics:</h3>
                <ul>
                    <li><strong>Queued Calls:</strong> {metrics.get('queuedCalls', 0)}</li>
                    <li><strong>Active Calls:</strong> {metrics.get('activeCalls', 0)}</li>
                    <li><strong>Utilization:</strong> {metrics.get('utilization', 0):.1f}%</li>
                    <li><strong>Running Campaigns:</strong> {metrics.get('runningCampaigns', 0)}</li>
                </ul>
                
                <p><em>This is an automated alert from {self.app_name} Admin Dashboard.</em></p>
            </body>
            </html>
            """
            
            text_body = f"""
            {alert_level} Alert for {partner_name}
            
            Alert Message: {message}
            
            Current Metrics:
            - Queued Calls: {metrics.get('queuedCalls', 0)}
            - Active Calls: {metrics.get('activeCalls', 0)}
            - Utilization: {metrics.get('utilization', 0):.1f}%
            - Running Campaigns: {metrics.get('runningCampaigns', 0)}
            
            This is an automated alert from {self.app_name} Admin Dashboard.
            """
            
            # For now, send to admin email
            # In production, fetch recipient list from settings
            to_email = "admin@jobtalk.com"

            return await asyncio.to_thread(
                self.send_email, [to_email], subject, html_body, text_body
            )

        except Exception as e:
            logger.error(f"Error sending alert email: {str(e)}")
            return False

    async def send_qa_report_email(
        self,
        calls: List[Dict[str, Any]],
        date: str,
        to_addresses: Optional[List[str]] = None,
        partner_name: Optional[str] = None,
        score_filter: Optional[int] = None,
        cc: Optional[List[str]] = None,
        custom_message: Optional[str] = None,
    ) -> bool:
        """Send QA report email with call scores as CSV attachment via SES SMTP."""
        import csv
        import io

        t_start = time.time()
        logger.info(f"[QA-EMAIL] ====== send_qa_report_email START ======")
        logger.info(f"[QA-EMAIL] Partner: {partner_name}, Date: {date}, Calls: {len(calls)}, ScoreFilter: {score_filter}, CC: {cc}")
        try:
            label = partner_name or "All Partners"
            subject = f"QA Report — {label} — {date} ({len(calls)} calls)"

            def _format_duration(seconds):
                if not seconds:
                    return "0:00"
                m, s = divmod(int(seconds), 60)
                return f"{m}:{s:02d}"

            # Build CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow([
                "Call ID", "Contact", "Phone", "Campaign", "Duration",
                "AI Voice Quality", "AI Latency", "AI Conversation Quality",
                "Human Voice Quality", "Human Latency", "Human Conversation Quality",
                "Notes",
            ])
            for call in calls:
                qa = call.get("qaAnalysis") or {}
                contact_name = f"{call.get('contactFirstName', '') or ''} {call.get('contactLastName', '') or ''}".strip()
                writer.writerow([
                    call.get("id", ""),
                    contact_name,
                    call.get("contactPhone", "") or "",
                    call.get("campaignName", "") or "",
                    _format_duration(call.get("duration")),
                    qa.get("aiVoiceQuality", ""),
                    qa.get("aiLatency", ""),
                    qa.get("aiConversationQuality", ""),
                    qa.get("humanVoiceQuality", ""),
                    qa.get("humanLatency", ""),
                    qa.get("humanConversationQuality", ""),
                    qa.get("aiNotes", "") or "",
                ])

            csv_bytes = csv_buffer.getvalue().encode("utf-8")
            safe_partner = (partner_name or "all").replace(" ", "_").lower()
            csv_filename = f"qa_report_{safe_partner}_{date}.csv"

            # Build email body (summary only, details in CSV)
            filter_label = f" (scores ≤ {score_filter})" if score_filter else ""
            message_block = ""
            if custom_message:
                message_block = f'<p style="margin-bottom:16px; padding:12px; background:#f0f4ff; border-radius:6px;">{custom_message}</p>'

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #2c3e50;">QA Report — {label} — {date}</h2>
                {message_block}
                <p>Please find the detailed call scores in the attached CSV file.</p>
            </body>
            </html>
            """

            text_body = f"QA Report — {label} — {date} ({len(calls)} calls)\n\n"
            if custom_message:
                text_body += f"{custom_message}\n\n"
            text_body += "Please find the detailed call scores in the attached CSV file.\n"

            recipients = to_addresses or ["bhavdipm@aptask.com"]

            logger.info(f"[QA-EMAIL] CSV built: {len(calls)} rows, {len(csv_bytes)} bytes | file: {csv_filename}")
            logger.info(f"[QA-EMAIL] Recipients: {recipients}")
            logger.info(f"[QA-EMAIL] Handing off to send_email via thread ...")

            result = await asyncio.to_thread(
                self.send_email,
                recipients, subject, html_body, text_body, cc,
                attachments=[(csv_filename, csv_bytes, "text/csv")],
            )

            total = time.time() - t_start
            logger.info(f"[QA-EMAIL] ====== send_qa_report_email {'SUCCESS' if result else 'FAILED'} in {total:.3f}s ======")
            return result

        except Exception as e:
            total = time.time() - t_start
            logger.error(f"[QA-EMAIL] ====== send_qa_report_email EXCEPTION after {total:.3f}s ======")
            logger.error(f"[QA-EMAIL] Error: {type(e).__name__}: {str(e)}")
            return False
