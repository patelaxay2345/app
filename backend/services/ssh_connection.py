import paramiko
import pymysql
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
from models import PartnerConfig, ConnectionStatus, TestConnectionResponse, ConnectionLog
from services.encryption import EncryptionService
import uuid

logger = logging.getLogger(__name__)

class SSHConnectionService:
    def __init__(self, db, encryption_service: EncryptionService):
        self.db = db
        self.encryption_service = encryption_service
    
    async def test_connection(self, partner: PartnerConfig) -> TestConnectionResponse:
        """Test SSH tunnel and MySQL connection"""
        start_time = time.time()
        
        try:
            # Decrypt credentials
            db_password = self.encryption_service.decrypt(partner.dbPassword)
            
            ssh_client = None
            tunnel = None
            mysql_conn = None
            
            if partner.sshConfig.enabled:
                # Test SSH connection
                try:
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    # Prepare SSH credentials
                    ssh_kwargs = {
                        'hostname': partner.sshConfig.host,
                        'port': partner.sshConfig.port,
                        'username': partner.sshConfig.username,
                    }
                    
                    # Use private key authentication if available
                    if partner.sshConfig.privateKey:
                        # Decrypt and use private key
                        private_key_str = self.encryption_service.decrypt(partner.sshConfig.privateKey)
                        from io import StringIO
                        key_file = StringIO(private_key_str)
                        
                        if partner.sshConfig.passphrase:
                            passphrase = self.encryption_service.decrypt(partner.sshConfig.passphrase)
                            pkey = paramiko.RSAKey.from_private_key(key_file, password=passphrase)
                        else:
                            pkey = paramiko.RSAKey.from_private_key(key_file)
                        
                        ssh_kwargs['pkey'] = pkey
                    # Use password authentication if no private key
                    elif partner.sshConfig.password:
                        password = self.encryption_service.decrypt(partner.sshConfig.password)
                        ssh_kwargs['password'] = password
                    
                    ssh_client.connect(**ssh_kwargs, timeout=30)
                    logger.info(f"SSH connection successful to {partner.partnerName}")
                    
                except Exception as e:
                    response_time = int((time.time() - start_time) * 1000)
                    await self._log_connection(partner.id, ConnectionStatus.SSH_FAILED, str(e), response_time)
                    return TestConnectionResponse(
                        success=False,
                        message=f"SSH connection failed: {str(e)}",
                        responseTimeMs=response_time
                    )
            
            # Test MySQL connection
            try:
                if ssh_client and partner.sshConfig.enabled:
                    # Create SSH tunnel
                    tunnel = ssh_client.get_transport().open_channel(
                        'direct-tcpip',
                        (partner.dbHost, partner.dbPort),
                        ('127.0.0.1', 0)
                    )
                    mysql_conn = pymysql.connect(
                        host='127.0.0.1',
                        port=partner.dbPort,
                        user=partner.dbUsername,
                        password=db_password,
                        database=partner.dbName,
                        connect_timeout=30,
                        sock=tunnel
                    )
                else:
                    # Direct connection
                    mysql_conn = pymysql.connect(
                        host=partner.dbHost,
                        port=partner.dbPort,
                        user=partner.dbUsername,
                        password=db_password,
                        database=partner.dbName,
                        connect_timeout=30
                    )
                
                # Test query
                cursor = mysql_conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                
                response_time = int((time.time() - start_time) * 1000)
                await self._log_connection(partner.id, ConnectionStatus.SUCCESS, None, response_time)
                
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    responseTimeMs=response_time,
                    details={"database": partner.dbName}
                )
                
            except Exception as e:
                response_time = int((time.time() - start_time) * 1000)
                await self._log_connection(partner.id, ConnectionStatus.DB_FAILED, str(e), response_time)
                return TestConnectionResponse(
                    success=False,
                    message=f"Database connection failed: {str(e)}",
                    responseTimeMs=response_time
                )
            finally:
                if mysql_conn:
                    mysql_conn.close()
                if tunnel:
                    tunnel.close()
                if ssh_client:
                    ssh_client.close()
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test error for {partner.partnerName}: {str(e)}")
            return TestConnectionResponse(
                success=False,
                message=f"Connection error: {str(e)}",
                responseTimeMs=response_time
            )
    
    async def execute_query(self, partner: PartnerConfig, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute query on partner database via SSH tunnel"""
        start_time = time.time()
        
        try:
            db_password = self.encryption_service.decrypt(partner.dbPassword)
            
            ssh_client = None
            tunnel = None
            mysql_conn = None
            
            if partner.sshConfig.enabled:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                ssh_kwargs = {
                    'hostname': partner.sshConfig.host,
                    'port': partner.sshConfig.port,
                    'username': partner.sshConfig.username,
                }
                
                if partner.sshConfig.privateKey:
                    private_key_str = self.encryption_service.decrypt(partner.sshConfig.privateKey)
                    from io import StringIO
                    key_file = StringIO(private_key_str)
                    
                    if partner.sshConfig.passphrase:
                        passphrase = self.encryption_service.decrypt(partner.sshConfig.passphrase)
                        pkey = paramiko.RSAKey.from_private_key(key_file, password=passphrase)
                    else:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    
                    ssh_kwargs['pkey'] = pkey
                
                ssh_client.connect(**ssh_kwargs, timeout=30)
                tunnel = ssh_client.get_transport().open_channel(
                    'direct-tcpip',
                    (partner.dbHost, partner.dbPort),
                    ('127.0.0.1', 0)
                )
                mysql_conn = pymysql.connect(
                    host='127.0.0.1',
                    port=partner.dbPort,
                    user=partner.dbUsername,
                    password=db_password,
                    database=partner.dbName,
                    connect_timeout=30,
                    sock=tunnel
                )
            else:
                mysql_conn = pymysql.connect(
                    host=partner.dbHost,
                    port=partner.dbPort,
                    user=partner.dbUsername,
                    password=db_password,
                    database=partner.dbName,
                    connect_timeout=30
                )
            
            cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                mysql_conn.commit()
                result = {"affected_rows": cursor.rowcount}
            
            cursor.close()
            
            response_time = int((time.time() - start_time) * 1000)
            await self._log_connection(partner.id, ConnectionStatus.SUCCESS, None, response_time, "query")
            
            return result
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            await self._log_connection(partner.id, ConnectionStatus.QUERY_FAILED, str(e), response_time, "query")
            logger.error(f"Query execution error for {partner.partnerName}: {str(e)}")
            return None
        
        finally:
            if mysql_conn:
                mysql_conn.close()
            if tunnel:
                tunnel.close()
            if ssh_client:
                ssh_client.close()
    
    async def _log_connection(self, partner_id: str, status: ConnectionStatus, error: Optional[str], response_time: int, query_type: str = "test"):
        """Log connection attempt"""
        log = ConnectionLog(
            partnerId=partner_id,
            connectionStatus=status,
            errorMessage=error,
            responseTimeMs=response_time,
            queryType=query_type
        )
        
        log_dict = log.model_dump()
        log_dict['timestamp'] = log_dict['timestamp'].isoformat()
        
        await self.db.connection_logs.insert_one(log_dict)
