#!/usr/bin/env python3
"""
Test SSH tunnel and MySQL connection with sshtunnel library
"""

from sshtunnel import SSHTunnelForwarder
import pymysql
import tempfile

# Test credentials
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

MYSQL_HOST = "a348714-akamai-prod-4134270-default.g2a.akamaidb.net"
MYSQL_PORT = 25960
MYSQL_USER = "akmadmin"
MYSQL_PASS = "AVNS_ME4QjhAtv17LviPV32D"
MYSQL_DB = "defaultdb"

print("Testing SSH Tunnel + MySQL Connection with sshtunnel library")
print("=" * 70)

try:
    # Write SSH key to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
        key_file.write(SSH_PRIVATE_KEY)
        key_file_path = key_file.name
    
    print(f"✓ SSH key written to temp file: {key_file_path}")
    
    # Create SSH tunnel
    print(f"\n[1/3] Creating SSH tunnel to {SSH_HOST}:{SSH_PORT}...")
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=key_file_path,
        remote_bind_address=(MYSQL_HOST, MYSQL_PORT),
        local_bind_address=('127.0.0.1', 0)
    )
    
    tunnel.start()
    print(f"✓ SSH tunnel started")
    print(f"  Local port: {tunnel.local_bind_port}")
    print(f"  Remote: {MYSQL_HOST}:{MYSQL_PORT}")
    
    # Connect to MySQL through tunnel
    print(f"\n[2/3] Connecting to MySQL through tunnel...")
    connection = pymysql.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        connect_timeout=30,
        cursorclass=pymysql.cursors.DictCursor
    )
    print(f"✓ MySQL connected")
    
    # Test queries
    print(f"\n[3/3] Testing real data queries...")
    cursor = connection.cursor()
    
    # Query 1: Running campaigns
    cursor.execute("SELECT COUNT(*) as count FROM campaigns WHERE status = 'RUNNING' AND deleted = 0")
    result = cursor.fetchone()
    print(f"✓ Running campaigns: {result['count']}")
    
    # Query 2: Campaigns today
    cursor.execute("SELECT COUNT(*) as count FROM campaigns WHERE DATE(createdAt) = CURDATE() AND deleted = 0")
    result = cursor.fetchone()
    print(f"✓ Campaigns today: {result['count']}")
    
    # Query 3: Active calls
    cursor.execute("SELECT COUNT(*) as count FROM calls WHERE status = 'INPROGRESS'")
    result = cursor.fetchone()
    print(f"✓ Active calls: {result['count']}")
    
    # Query 4: Queued calls
    cursor.execute("SELECT COUNT(*) as count FROM calls WHERE status = 'QUEUED'")
    result = cursor.fetchone()
    print(f"✓ Queued calls: {result['count']}")
    
    cursor.close()
    connection.close()
    tunnel.stop()
    
    # Clean up
    import os
    os.remove(key_file_path)
    
    print("\n" + "=" * 70)
    print("✅ SUCCESS! SSH tunnel + MySQL connection working perfectly!")
    print("=" * 70)
    print("\nThe backend is ready to fetch real data from ApTask partner database.")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
