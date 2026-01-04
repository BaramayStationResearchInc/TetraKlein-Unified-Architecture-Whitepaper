import oqs
import json
import os

# Define the High-Security Tier
sig_alg = 'ML-DSA-87' 
os.makedirs('identity', exist_ok=True)

print(f"--- TetraKlein Genesis: Regenerating {sig_alg} ---")

with oqs.Signature(sig_alg) as signer:
    public_key = signer.generate_keypair()
    secret_key = signer.export_secret_key()

    # Define Node Metadata
    node_identity = {
        "node_name": "BaramayStation1",
        "pqc_alg": sig_alg,
        "public_key_hex": public_key.hex(),
        "status": "Active_Genesis_V2"
    }

    # Save Public Identity
    with open('identity/node_id.json', 'w') as f:
        json.dump(node_identity, f, indent=4)
    
    # Save Master Secret Key
    with open('identity/node_sk.bin', 'wb') as f:
        f.write(secret_key)

print(f"[✓] Master Key stored at: {os.path.abspath('identity/node_sk.bin')}")
print(f"[✓] Node ID stored at: {os.path.abspath('identity/node_id.json')}")
