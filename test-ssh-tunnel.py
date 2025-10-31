#!/usr/bin/env python3
"""
Test SSH tunnel connection to ApTask partner MongoDB database
"""

import paramiko
import pymongo
from sshtunnel import SSHTunnelForwarder
import time

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

# Save SSH key to temp file
import tempfile
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
    key_file.write(SSH_PRIVATE_KEY)
    key_file_path = key_file.name

try:
    print(f"[1/4] Creating SSH tunnel to {SSH_HOST}...")
    
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=key_file_path,
        remote_bind_address=(MONGO_HOST, MONGO_PORT),
        local_bind_address=('127.0.0.1', 0)  # Use random local port
    )
    
    tunnel.start()
    local_port = tunnel.local_bind_port
    print(f"✓ SSH tunnel established")
    print(f"  Local port: {local_port}")
    print()
    
    print(f"[2/4] Connecting to MongoDB through tunnel...")
    
    # Connect to MongoDB through tunnel
    mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@127.0.0.1:{local_port}/{MONGO_DB}?authSource=admin"
    
    client = pymongo.MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    
    # Test connection
    client.admin.command('ping')
    print(f"✓ MongoDB connection successful")
    print()
    
    # Get database
    db = client[MONGO_DB]
    
    print(f"[3/4] Exploring database schema...")
    print()
    
    # List all collections
    collections = db.list_collection_names()
    print(f"Found {len(collections)} collections:")
    print()
    
    collection_stats = []
    for coll_name in collections:
        try:
            count = db[coll_name].count_documents({})
            collection_stats.append((coll_name, count))
        except Exception as e:
            collection_stats.append((coll_name, f"Error: {str(e)}"))
    
    # Sort by document count
    collection_stats.sort(key=lambda x: x[1] if isinstance(x[1], int) else 0, reverse=True)
    
    for i, (name, count) in enumerate(collection_stats, 1):
        if isinstance(count, int):
            print(f"{i:2d}. {name:40s} : {count:>10,} documents")
        else:
            print(f"{i:2d}. {name:40s} : {count}")
    
    print()
    print(f"[4/4] Sampling data from key collections...")
    print("="*70)
    
    # Sample important collections
    important_keywords = ['campaign', 'call', 'lead', 'list', 'vicidial', 'user', 'log', 'agent']
    
    for coll_name in collections:
        # Check if collection name contains important keywords
        if any(keyword in coll_name.lower() for keyword in important_keywords):
            print(f"\n📊 Collection: {coll_name}")
            print("-" * 70)
            
            try:
                count = db[coll_name].count_documents({})
                print(f"Total documents: {count:,}")
                
                if count > 0:
                    # Get one sample document
                    sample = db[coll_name].find_one()
                    
                    if sample:
                        # Remove _id for cleaner output
                        sample.pop('_id', None)
                        
                        # Show schema
                        fields = list(sample.keys())
                        print(f"Fields ({len(fields)}): {', '.join(fields[:15])}")
                        if len(fields) > 15:
                            print(f"           ... and {len(fields) - 15} more fields")
                        
                        # Show sample data for first 5 fields
                        print("\nSample data:")
                        for key in fields[:10]:
                            value = sample[key]
                            if isinstance(value, str) and len(value) > 60:
                                value = value[:60] + "..."
                            print(f"  • {key}: {value}")
                        
                else:
                    print("  (Empty collection)")
                    
            except Exception as e:
                print(f"  Error sampling: {str(e)}")
    
    print()
    print("="*70)
    print("✓ Database exploration complete!")
    print()
    print("Next steps:")
    print("1. Identify the collections that contain campaign/call data")
    print("2. Update data_fetch.py to query these collections")
    print("3. Map the fields to our dashboard models")
    print("="*70)
    
    # Close connections
    client.close()
    tunnel.stop()
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up key file
    import os
    if os.path.exists(key_file_path):
        os.remove(key_file_path)

print()
