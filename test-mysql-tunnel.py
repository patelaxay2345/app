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
    
    # Connect to MySQL through tunnel
    mysql_conn = pymysql.connect(
        host='127.0.0.1',
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        unix_socket=channel
    )
    
    print(f"✓ MySQL connection successful")
    print()
    
    print(f"[4/4] Exploring database schema...")
    print("="*70)
    print()
    
    cursor = mysql_conn.cursor()
    
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    print(f"Found {len(tables)} tables in '{MYSQL_DB}':")
    print()
    
    # Get row counts for each table
    table_stats = []
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            table_stats.append((table, count))
        except Exception as e:
            table_stats.append((table, f"Error: {str(e)}"))
    
    # Sort by count
    table_stats.sort(key=lambda x: x[1] if isinstance(x[1], int) else 0, reverse=True)
    
    # Display tables
    for i, (table, count) in enumerate(table_stats, 1):
        if isinstance(count, int):
            print(f"{i:3d}. {table:50s} : {count:>12,} rows")
        else:
            print(f"{i:3d}. {table:50s} : {count}")
    
    print()
    print("="*70)
    print("Exploring VICIdial tables (campaigns, calls, leads)...")
    print("="*70)
    print()
    
    # Look for VICIdial tables
    vicidial_tables = [t for t in tables if 'vicidial' in t.lower() or 'campaign' in t.lower() or 'call' in t.lower()]
    
    for table in vicidial_tables[:10]:  # First 10 VICIdial tables
        print(f"\n📊 Table: {table}")
        print("-" * 70)
        
        try:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            print(f"Total rows: {count:,}")
            
            if count > 0:
                # Get table structure
                cursor.execute(f"DESCRIBE `{table}`")
                columns = cursor.fetchall()
                
                print(f"Columns ({len(columns)}):")
                for col in columns[:15]:  # First 15 columns
                    col_name, col_type = col[0], col[1]
                    print(f"  • {col_name:30s} : {col_type}")
                
                if len(columns) > 15:
                    print(f"  ... and {len(columns) - 15} more columns")
                
                # Get sample data
                print("\nSample row:")
                cursor.execute(f"SELECT * FROM `{table}` LIMIT 1")
                sample = cursor.fetchone()
                
                if sample:
                    col_names = [col[0] for col in columns]
                    for i, (col_name, value) in enumerate(zip(col_names[:10], sample[:10])):
                        if isinstance(value, str) and len(value) > 60:
                            value = value[:60] + "..."
                        print(f"  {col_name}: {value}")
                    
                    if len(col_names) > 10:
                        print(f"  ... and {len(col_names) - 10} more fields")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print()
    print("="*70)
    print("✓ Database exploration complete!")
    print("="*70)
    print()
    
    print("Key VICIdial Tables Found:")
    for table in vicidial_tables[:20]:
        print(f"  • {table}")
    
    # Close connections
    cursor.close()
    mysql_conn.close()
    channel.close()
    ssh_client.close()
    
    print()
    print("Next Steps:")
    print("1. Identify tables with active campaign data")
    print("2. Update data_fetch_service.py to query these tables")
    print("3. Map VICIdial fields to dashboard models")
    print()
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print()
