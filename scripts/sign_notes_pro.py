#!/usr/bin/env python3
"""Sign a routing configuration. The private key MUST remain outside this repository."""
import argparse
import base64
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--endpoint", required=True, help="HTTPS endpoint (pilot: non-licensing test URL)")
    parser.add_argument("--revision", type=int, required=True)
    parser.add_argument("--expires", default="2031-10-30", help="Expiry date YYYY-MM-DD UTC")
    args = parser.parse_args()
    url = urlsplit(args.endpoint)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment or url.query or url.port not in (None, 443):
        parser.error("Only clean HTTPS endpoint URLs are allowed")
    if args.revision < 1:
        parser.error("Revision must be positive and greater than the previously published revision")
    expires = int(datetime.strptime(args.expires, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    now = int(datetime.now(timezone.utc).timestamp())
    if expires <= now:
        parser.error("Expiry must be in the future")
    payload = {"app": "notes-pro", "revision": args.revision, "endpoint": args.endpoint, "issuedAt": now, "expiresAt": expires}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    private = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    if not isinstance(private, ec.EllipticCurvePrivateKey) or private.curve.name != "secp256r1":
        parser.error("Signing key must be ECDSA P-256")
    signed = {"format": 1, "payload": b64(raw), "signature": b64(private.sign(raw, ec.ECDSA(hashes.SHA256())))}
    output = Path(__file__).resolve().parent.parent / "notes-pro.json"
    output.write_text(json.dumps(signed, indent=2) + "\n")
    print(f"Signed notes-pro revision {args.revision}: {args.endpoint} -> {output}")


if __name__ == "__main__":
    main()
