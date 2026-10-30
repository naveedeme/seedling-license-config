#!/usr/bin/env python3
"""Sign Notes Pro routing (format 1 root or format 2 delegated). Never commit private keys."""
import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROOT_PUBLIC_KEY_B64 = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEudUcqJ7ASXj13/47fwf72gRQsNzFKCae3lZKzI96mh1hMQd1zPfju8OeCXriaW+twsQ9i03H1EXwR7bRjb3bDA=="
OUTPUT = Path(__file__).resolve().parent.parent / "notes-pro.json"


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decoded(encoded):
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))


def check_url(value):
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if (parts.scheme != "https" or not host or "." not in host or parts.username or parts.password
            or parts.query or parts.fragment or parts.port not in (None, 443)
            or any(not x or len(x) > 63 or not x[0].isalnum() or not x[-1].isalnum() for x in host.split("."))
            or not all(c.isascii() and (c.isalnum() or c in ".-") for c in host)
            or host.endswith((".local", ".internal")) or host == "localhost"
            or host.replace(".", "").isdigit()):
        raise ValueError("Unsafe endpoint URL: " + value)
    return value


def load_key(path):
    private = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private, ec.EllipticCurvePrivateKey) or private.curve.name != "secp256r1":
        raise ValueError("Expected ECDSA P-256 private key")
    return private


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--key", type=Path, required=True, help="Local root PEM (format 1) or delegate PEM (format 2)")
    p.add_argument("--endpoint", required=True)
    p.add_argument("--fallback-endpoint", action="append", default=[], help="Up to 3 trusted HTTPS standby endpoints")
    p.add_argument("--revision", type=int, required=True)
    p.add_argument("--expires", default="2031-10-30", help="YYYY-MM-DD UTC")
    p.add_argument("--delegation", type=Path, help="Root-signed delegate certificate; enables format 2")
    args = p.parse_args()
    if args.revision <= 0:
        p.error("Revision must be positive")
    if len(args.fallback_endpoint) > 3:
        p.error("No more than 3 fallback endpoints")
    urls = [check_url(x) for x in [args.endpoint, *args.fallback_endpoint]]
    if len(set(urls)) != len(urls):
        p.error("Duplicate endpoints")
    now = int(datetime.now(timezone.utc).timestamp())
    expiry = int(datetime.strptime(args.expires, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    if expiry <= now:
        p.error("Configuration expiry must be in the future")
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text())
        last_revision = json.loads(decoded(previous["payload"]))["revision"]
        if args.revision <= last_revision:
            p.error(f"Revision must increase beyond {last_revision}")
    payload = {"app": "notes-pro", "revision": args.revision, "endpoint": args.endpoint,
               "issuedAt": now, "expiresAt": expiry}
    if args.fallback_endpoint:
        payload["fallbackEndpoints"] = args.fallback_endpoint
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    private = load_key(args.key)
    signed = {"format": 1, "payload": b64(raw),
              "signature": b64(private.sign(raw, ec.ECDSA(hashes.SHA256())))}
    if args.delegation:
        cert = json.loads(args.delegation.read_text())
        cert_raw = decoded(cert["payload"])
        root_public = serialization.load_der_public_key(base64.b64decode(ROOT_PUBLIC_KEY_B64))
        root_public.verify(decoded(cert["signature"]), cert_raw, ec.ECDSA(hashes.SHA256()))
        grant = json.loads(cert_raw)
        if grant["app"] != "notes-pro" or grant["expiresAt"] < expiry or grant["issuedAt"] > now + 300:
            p.error("Delegation scope or validity does not cover this configuration")
        actual_public = private.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if actual_public != base64.b64decode(grant["publicKey"]):
            p.error("Delegate private key does not match root-authorized public key")
        signed = {"format": 2, "payload": b64(raw), "signature": signed["signature"],
                  "keyId": grant["keyId"], "delegation": cert}
    elif private.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    ) != base64.b64decode(ROOT_PUBLIC_KEY_B64):
        p.error("Format 1 MUST use the pinned pilot root private key")
    OUTPUT.write_text(json.dumps(signed, indent=2) + "\n")
    print(f"Published locally as revision {args.revision} format {signed['format']}: {OUTPUT}")
    print("IMPORTANT: git review and commit explicitly; private keys must never be included.")


if __name__ == "__main__":
    main()
