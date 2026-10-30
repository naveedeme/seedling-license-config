#!/usr/bin/env python3
"""Authorize a short-lived Notes Pro endpoint signing key with the offline pilot root."""
import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root-key", type=Path, required=True, help="Offline Notes Pro pilot root private key")
    p.add_argument("--delegate-public", type=Path, required=True, help="PEM public key of the new online signer")
    p.add_argument("--key-id", required=True, help="Unique ID for the delegated key")
    p.add_argument("--days", type=int, default=90, help="Validity, maximum 365 days")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not (1 <= args.days <= 365):
        p.error("Delegation validity must be 1-365 days")
    if not (1 <= len(args.key_id) <= 64 and all(c.isascii() and (c.isalnum() or c in "._-") for c in args.key_id)):
        p.error("Invalid key ID")
    root = serialization.load_pem_private_key(args.root_key.read_bytes(), password=None)
    delegate = serialization.load_pem_public_key(args.delegate_public.read_bytes())
    if not isinstance(root, ec.EllipticCurvePrivateKey) or root.curve.name != "secp256r1":
        p.error("Root must be an ECDSA P-256 private key")
    if not isinstance(delegate, ec.EllipticCurvePublicKey) or delegate.curve.name != "secp256r1":
        p.error("Delegate public key must be ECDSA P-256")
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"app": "notes-pro", "keyId": args.key_id, "issuedAt": now,
               "expiresAt": now + args.days * 86400,
               "publicKey": base64.b64encode(delegate.public_bytes(
                   serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    cert = {"payload": b64(raw), "signature": b64(root.sign(raw, ec.ECDSA(hashes.SHA256())))}
    args.output.write_text(json.dumps(cert, indent=2) + "\n")
    print(f"Created root-authorized certificate for {args.key_id}, valid {args.days} days.")
    print("Keep both signing private keys offline/secure; certificate alone can be published.")

if __name__ == "__main__":
    main()
