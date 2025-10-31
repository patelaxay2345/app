#!/usr/bin/env python3
"""
Test SSH tunnel connection to ApTask partner MongoDB database using paramiko
"""

import paramiko
import pymongo
from io import StringIO
import select
import socket

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

# MongoDB credentials
MONGO_HOST = "a348714-akamai-prod-4134270-default.g2a.akamaidb.net"
MONGO_PORT = 25960
MONGO_USER = "akmadmin"
MONGO_PASS = "AVNS_ME4QjhAtv17LviPV32D"
MONGO_DB = "defaultdb"

print("="*70)
print("  ApTask Partner Database Connection Test (via SSH Tunnel)")
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
    
    print(f"[2/4] Creating SSH tunnel to MongoDB...")
    
    # Create tunnel to MongoDB
    transport = ssh_client.get_transport()
    
    # Open channel for port forwarding
    local_port = 27018  # Local port to forward to
    
    # Create channel
    channel = transport.open_channel(
        'direct-tcpip',
        (MONGO_HOST, MONGO_PORT),
        ('127.0.0.1', local_port)
    )
    
    if channel is None:
        raise Exception("Could not establish SSH tunnel")
    
    print(f"✓ SSH tunnel created")
    print(f"  Remote: {MONGO_HOST}:{MONGO_PORT}")
    print(f"  Local: 127.0.0.1:{local_port}")
    print()
    
    print(f"[3/4] Connecting to MongoDB...")
    
    # Use different approach - execute mongosh command via SSH
    print("  Executing database commands via SSH...")
    
    # List collections command
    cmd = f"mongosh 'mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin&tls=true&tlsAllowInvalidCertificates=true' --quiet --eval 'db.getCollectionNames()'"
    
    stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=30)
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    if error and "Error" in error:
        print(f"✗ MongoDB command error: {error}")
    else:
        print(f"✓ MongoDB connection successful")
        print()
        
        # Parse collections
        if output:
            print(f"[4/4] Database collections:")
            print("-" * 70)
            
            # Try to parse as JSON array
            try:
                import json
                collections = json.loads(output.strip())
                print(f"Found {len(collections)} collections:")
                print()
                
                for i, coll in enumerate(collections, 1):
                    print(f"{i:2d}. {coll}")
                
                print()
                print("="*70)
                
                # Sample a few collections
                print("Sampling collections...")
                print("="*70)
                
                for coll in collections[:10]:  # First 10 collections
                    print(f"\n📊 Collection: {coll}")
                    print("-" * 70)
                    
                    # Count documents
                    count_cmd = f"mongosh 'mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin&tls=true&tlsAllowInvalidCertificates=true' --quiet --eval 'db.{coll}.countDocuments()'"
                    stdin, stdout, stderr = ssh_client.exec_command(count_cmd, timeout=10)
                    count_output = stdout.read().decode().strip()
                    
                    try:
                        count = int(count_output)
                        print(f"Documents: {count:,}")
                        
                        if count > 0:
                            # Get sample document
                            sample_cmd = f"mongosh 'mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin&tls=true&tlsAllowInvalidCertificates=true' --quiet --eval 'printjson(db.{coll}.findOne())'"
                            stdin, stdout, stderr = ssh_client.exec_command(sample_cmd, timeout=10)
                            sample_output = stdout.read().decode()
                            
                            if sample_output:
                                print("Sample document:")
                                lines = sample_output.strip().split('\n')[:15]  # First 15 lines
                                for line in lines:
                                    print(f"  {line}")
                                if len(sample_output.split('\n')) > 15:
                                    print("  ...")
                    except:
                        print(f"Count: {count_output}")
                
            except json.JSONDecodeError:
                print("Raw output:")
                print(output)
    
    print()
    print("="*70)
    print("✓ Database exploration complete!")
    print("="*70)
    
    # Close SSH connection
    ssh_client.close()
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print()
