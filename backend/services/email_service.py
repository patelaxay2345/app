import boto3
from botocore.exceptions import ClientError
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        self.from_email = os.environ.get('SMTP_FROM_EMAIL', 'noreply@jobtalk.com')
        self.app_name = os.environ.get('APP_NAME', 'JobTalk')
    
    async def send_alert_email(self, partner_name: str, alert_level: str, message: str, metrics: Dict[str, Any]) -> bool:
        """Send alert email via AWS SES"""
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
            
            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Text': {'Data': text_body},
                        'Html': {'Data': html_body}
                    }
                }
            )
            
            logger.info(f"Alert email sent successfully for {partner_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to send email: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
