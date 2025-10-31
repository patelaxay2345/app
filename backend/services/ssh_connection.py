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
    
    async def execute_query(self, partner: PartnerConfig, query: str, params: tuple = None):
        """Execute SQL query on partner database through SSH tunnel"""
        from sshtunnel import SSHTunnelForwarder
        import tempfile
        
        try:
            if not partner.sshConfig.enabled:
                # Direct connection without SSH
                db_password = self.encryption_service.decrypt(partner.dbPassword)
                mysql_conn = pymysql.connect(
                    host=partner.dbHost,
                    port=partner.dbPort,
                    user=partner.dbUsername,
                    password=db_password,
                    database=partner.dbName,
                    connect_timeout=30,
                    cursorclass=pymysql.cursors.DictCursor
                )
            else:
                # Connection through SSH tunnel
                db_password = self.encryption_service.decrypt(partner.dbPassword)
                
                # Prepare SSH authentication
                ssh_pkey = None
                ssh_password = None
                
                if partner.sshConfig.privateKey:
                    # Use private key authentication
                    private_key_str = self.encryption_service.decrypt(partner.sshConfig.privateKey)
                    
                    # Write key to temp file for sshtunnel
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
                        key_file.write(private_key_str)
                        key_file_path = key_file.name
                    
                    ssh_pkey = key_file_path
                elif partner.sshConfig.password:
                    # Use password authentication
                    ssh_password = self.encryption_service.decrypt(partner.sshConfig.password)
                
                # Create SSH tunnel
                tunnel = SSHTunnelForwarder(
                    (partner.sshConfig.host, partner.sshConfig.port),
                    ssh_username=partner.sshConfig.username,
                    ssh_pkey=ssh_pkey if ssh_pkey else None,
                    ssh_password=ssh_password if ssh_password else None,
                    remote_bind_address=(partner.dbHost, partner.dbPort),
                    local_bind_address=('127.0.0.1', 0)  # Use random local port
                )
                
                tunnel.start()
                
                try:
                    # Connect to MySQL through tunnel
                    mysql_conn = pymysql.connect(
                        host='127.0.0.1',
                        port=tunnel.local_bind_port,
                        user=partner.dbUsername,
                        password=db_password,
                        database=partner.dbName,
                        connect_timeout=30,
                        cursorclass=pymysql.cursors.DictCursor
                    )
                    
                    # Execute query
                    cursor = mysql_conn.cursor()
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    cursor.close()
                    mysql_conn.close()
                    
                    return results
                    
                finally:
                    tunnel.stop()
                    # Clean up temp key file
                    if ssh_pkey:
                        import os
                        try:
                            os.remove(ssh_pkey)
                        except Exception:
                            pass
            
            # For direct connection (no SSH)
            cursor = mysql_conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            mysql_conn.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise
    
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
