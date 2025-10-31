#!/usr/bin/env python3
"""
Test SSH tunnel connection to ApTask partner MySQL database
"""

import paramiko
import pymysql
from io import StringIO

# SSH credentials
SSH_HOST = "50.116.57.177"
SSH_PORT = 22
SSH_USER = "root"
SSH_PRIVATE_KEY = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEAxpMb1S18RlJWMlWIQp2dEPJIVrw+ykGIpd5Q97DRaP32elAp75BS
zRViz31aKSP0jrb4U+HITST6oxJTiIL2B2uUASQXU+6AviOl3vjXL7Mda37nxciCXv4Q3b
03GJuh9pEGcVXptDxC1wzUOXHeEcPhrGq29kSaODv2T49jHNCaApWBAmCKuIg74zHl4z88
fXHS0ApsMnH1gKlsBrKoJUWBrFVumLSJTUvLgcL8nKHjGwI0bSTtrMGKFLFf6Tsq6n7BGD
JnhLLmQ+JVa9d7yvdKuFwMMg6+YO0syVcXL62ylOuNswhjJEf3KmcGBrBOiySQgPOaEU39
pqAf13RnlQAAA9gkbaTUJG2k1AAAAAdzc2gtcnNhAAABAQDGkxvVLXxGUlYyVYhCnZ0Q8k
hWvD7KQYil3lD3sNFo/fZ6UCnvkFLNFWLPfVopI/SOtvhT4chNJPqjElOIgvYHa5QBJBdT
7oC+I6Xe+Ncvsx1rfufFyIJe/hDdvTcYm6H2kQZxVem0PELXDNQ5cd4Rw+Gsarb2RJo4O/
ZPj2Mc0JoClYECYIq4iDvjMeXjPzx9cdLQCmwycfWAqWwGsqglRYGsVW6YtIlNS8uBwvyc
oeMbAjRtJO2swYoUsV/pOyrqfsEYMmeEsuZD4lVr13vK90q4XAwyDr5g7SzJVxcvrbKU64
2zCGMkR/cqZwYGsE6LJJCA85oRTf2moB/XdGeVAAAAAwEAAQAAAQAcoU8tAD7fwLVO0ogv
2puvus71OnTvIl26VIBmBedbdOpZnj89nBhkG0ZA1jjun5F+FiFdrrr7bG56noTOtNsWHM
udEoAOiN+lCmy65jPYW8HNIuH14T/yxDzYS5SrBp1meGhuZM2qP9n/OYlLswAqnYxnGIfC
oAeAPhz4QZsvpx68R1sWT6aJyPjIlGRzZX8kLggFJyHL86piY+CX8YiFXZSAM9IACWTTVM
KuCfKhPD2yORYj6ZCkmX96PhyEBgKKBCipgCerKwHYehmdw1RGv5rYKJ4/ZRTfvwyYgUdq
G2G3grfi/YVqzUzdjwFXxvf7z4iVaY8i6ooQErMxP3sNAAAAgQDtpMykzbgYgEahSHBe/o
pvsbkUCuNuFwmK33rN+SZYPJQwtUzrW60n7+dsd47b23T7MmgMd/dQRKk62je9hqlfYfLn
HDMOaUp9vAqdifwgvKrEbMP+ecAINNLZFA4cU50Na/5/km3Wxt1f71l2am1o4Nhk2m+6si
T7V35ORoFAlwAAAIEA7zUvk9wK45mwlD7sn4x1pCYWjrx9fmfY5TvaoisOvhsNDTaCoCNV
xYPlS2EDFBKBaEZDOlnlqJiGNFplDQnJCYMvq4SDHPkXZp6NiL1nQgIvGYdtiyeUqGh3Z3
SCy9zTkkx6RM7hqRIsP6jJjB2TheKmW0sJ63CV4gKEAmY+sWsAAACBANSDtAZoxfTkY66k
zsUcrMD2Tiy3pcY7zmZzE0CjQbefeNuwlD5h/PaluvnAxReRVkm57hTXyVHcxNsc2Ikb5x
odaGy+Y1F/26B/DPJl93HkNAFn4/Q2Tdzx4OnkQxQ01reZaUEmi3Jmx+2BkIBdVQj0lSwA
ITUheRc1VW+rmor/AAAAG0ZvciBHSVRMQUIgQ0kvQ0QgZGVwbG95bWVudAECAwQFBgc=
-----END OPENSSH PRIVATE KEY-----"""

# MySQL credentials  
MYSQL_HOST = "a348714-akamai-prod-4134270-default.g2a.akamaidb.net"
MYSQL_PORT = 25960
MYSQL_USER = "akmadmin"
MYSQL_PASS = "AVNS_ME4QjhAtv17LviPV32D"
MYSQL_DB = "defaultdb"

print("="*70)
print("  ApTask Partner MySQL Database Connection Test")
print("="*70)
print()

try:
    print(f"[1/4] Establishing SSH connection to {SSH_HOST}...")
    
    # Create SSH client
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Load private key
    key_file = StringIO(SSH_PRIVATE_KEY)
    private_key = paramiko.RSAKey.from_private_key(key_file)
    
    # Connect via SSH
    ssh_client.connect(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        pkey=private_key,
        timeout=30
    )
    
    print(f"✓ SSH connection established")
    print()
    
    print(f"[2/4] Creating SSH tunnel to MySQL database...")
    
    # Create tunnel to MySQL
    transport = ssh_client.get_transport()
    channel = transport.open_channel(
        'direct-tcpip',
        (MYSQL_HOST, MYSQL_PORT),
        ('127.0.0.1', 0)
    )
    
    if channel is None:
        raise Exception("Could not establish SSH tunnel")
    
    print(f"✓ SSH tunnel created")
    print(f"  Remote: {MYSQL_HOST}:{MYSQL_PORT}")
    print()
    
    print(f"[3/4] Connecting to MySQL database...")
    
    # PyMySQL doesn't support using channel directly
    # We need to use the existing SSH connection service approach
    # Let's use a simpler test - execute MySQL commands via SSH
    
    print(f"✓ Testing MySQL connection via SSH command...")
    print()
    
    # Test MySQL connection using command
    mysql_cmd = f"mysql -h {MYSQL_HOST} -P {MYSQL_PORT} -u {MYSQL_USER} -p'{MYSQL_PASS}' {MYSQL_DB} -e 'SHOW TABLES;' 2>&1"
    
    stdin, stdout, stderr = ssh_client.exec_command(mysql_cmd, timeout=30)
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    if 'ERROR' in error or 'ERROR' in output:
        print(f"✗ MySQL connection failed:")
        print(error if error else output)
    elif output:
        print(f"✓ MySQL connection successful!")
        print()
        
        print(f"[4/4] Database tables:")
        print("="*70)
        print()
        
        # Parse tables
        lines = output.strip().split('\n')
        tables = [line.strip() for line in lines[1:] if line.strip()]  # Skip header
        
        print(f"Found {len(tables)} tables:")
        print()
        
        # Show first 50 tables
        for i, table in enumerate(tables[:50], 1):
            print(f"{i:3d}. {table}")
        
        if len(tables) > 50:
            print(f"     ... and {len(tables) - 50} more tables")
        
        print()
        print("="*70)
        print("Analyzing VICIdial tables...")
        print("="*70)
        print()
        
        # Filter VICIdial tables
        vicidial_tables = [t for t in tables if 'vicidial' in t.lower()]
        
        print(f"Found {len(vicidial_tables)} VICIdial tables:")
        for table in vicidial_tables:
            print(f"  • {table}")
        
        print()
        
        # Get details for key tables
        key_tables = ['vicidial_campaigns', 'vicidial_list', 'vicidial_log', 
                     'vicidial_auto_calls', 'vicidial_live_agents']
        
        for table in key_tables:
            if table in tables:
                print(f"\n📊 Table: {table}")
                print("-" * 70)
                
                # Get row count
                count_cmd = f"mysql -h {MYSQL_HOST} -P {MYSQL_PORT} -u {MYSQL_USER} -p'{MYSQL_PASS}' {MYSQL_DB} -e 'SELECT COUNT(*) FROM {table};' -s -N 2>&1"
                stdin, stdout, stderr = ssh_client.exec_command(count_cmd, timeout=10)
                count_output = stdout.read().decode().strip()
                
                if count_output.isdigit():
                    print(f"Total rows: {int(count_output):,}")
                else:
                    print(f"Row count: {count_output}")
                
                # Get table structure
                desc_cmd = f"mysql -h {MYSQL_HOST} -P {MYSQL_PORT} -u {MYSQL_USER} -p'{MYSQL_PASS}' {MYSQL_DB} -e 'DESCRIBE {table};' 2>&1"
                stdin, stdout, stderr = ssh_client.exec_command(desc_cmd, timeout=10)
                desc_output = stdout.read().decode()
                
                if desc_output and 'ERROR' not in desc_output:
                    lines = desc_output.strip().split('\n')
                    print(f"\nColumns ({len(lines)-1}):")
                    for line in lines[1:11]:  # First 10 columns
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            print(f"  • {parts[0]:30s} : {parts[1]}")
                    if len(lines) > 11:
                        print(f"  ... and {len(lines) - 11} more columns")
        
        print()
        print("="*70)
        print("✓ Database exploration complete!")
        print("="*70)
    else:
        print("✗ No output from MySQL command")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print()
