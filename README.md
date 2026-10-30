# Seedling endpoint discovery — Notes Pro safety pilot

This **public repository contains routing metadata only**, not licenses, entitlement checks, application secrets, Google credentials, or private signing keys. The private `notes-pro` Android repository remains private.

Current published configuration: **revision 4**, primary route `https://seedlingappstudio.pages.dev/notes-pro/`, standby route `https://raw.githubusercontent.com/naveedeme/seedling-license-config/main/pilot-health.json`. These are harmless website/test endpoints — **NOT** license servers. Revision 1 established the route; revision 2 switched to GitHub to prove migration; revision 3 restored the original route. Revision 4 adds a signed standby target for testing failover. The separate Notes Pro debug launcher discovered the first three revisions without reinstalling the app; revision 4 still needs an on-device test.

## Signature format and security model

- Format 1: base64url `payload` (UTF-8 JSON) and ECDSA P-256/SHA-256 `signature` made by the existing, pinned root key.
- Payload includes `app`, `endpoint`, `revision`, `issuedAt`, and `expiresAt`, plus optional `fallbackEndpoints` (up to three other trusted HTTPS addresses).
- Every candidate URL is **inside the signed payload**. GitHub, CDN mirrors, and a modified JSON file cannot authorize another endpoint on their own.
- Format 2: endpoint payload signed by a delegated P-256 signing key with `keyId`; `delegation` includes a certificate signed by the original trusted root, scoped to `notes-pro` with issue/expiry dates.
- A delegated signing key **cannot authorize another signing key**; new delegates must be explicitly approved by the offline root.
- The app remembers the highest accepted revision, rechecks cached signatures at startup, rejects expired routing configurations and downgrades, and uses the bundled fallback if no trusted configuration remains.
- Primary network source: `https://raw.githubusercontent.com/naveedeme/seedling-license-config/main/notes-pro.json`. Secondary source: `https://cdn.jsdelivr.net/gh/naveedeme/seedling-license-config@main/notes-pro.json`. This is a CDN mirror of the *same GitHub origin*, not an independently controlled backup. CDN caches can be stale; clients reject lower revisions.
- Debug-only simulated primary failure demonstrates candidate routing. Future license implementations must fail over **only** for temporary transport errors, HTTP 429, or 5xx. Never retry a denied license on another server after a definitive 4xx result.

## Publish format-1 revision 4 with a safe standby

The enhanced debug build supports standby candidates. For test purposes use these values while retaining the current primary route:

```bash
python -m pip install cryptography
python scripts/sign_notes_pro.py \
  --key /secure/location/pilot-routing-signing-private.pem \
  --revision 4 \
  --endpoint https://seedlingappstudio.pages.dev/notes-pro/ \
  --fallback-endpoint https://raw.githubusercontent.com/naveedeme/seedling-license-config/main/pilot-health.json
git diff -- notes-pro.json
git add notes-pro.json
git commit -m "Notes Pro: signed revision 4 with standby route"
git push
```

**Keep the root PEM outside this repository** (including commit history and GitHub Actions logs) and back it up securely. Check the `--revision` value against the current published revision before each release. Clients will reject a lower number. If you publish a bad endpoint, fix it by publishing a *higher* signed revision.

## Future delegated-key rotation

Keep the existing **format 1** public feed as long as old installed APKs require it. Format-1-only clients cannot parse format 2, so publishing format 2 prematurely would strand them on their last cached route or the built-in fallback.

After compatible app versions are distributed, authorize a shorter-lived delegate with the root key:

```bash
# Generate and secure the new delegate private key OFF the repository.
openssl ecparam -name prime256v1 -genkey -noout -out /secure/location/notespro-delegate.pem
openssl pkey -in /secure/location/notespro-delegate.pem -pubout -out /secure/location/notespro-delegate-public.pem

python scripts/issue_notes_pro_delegation.py \
  --root-key /secure/location/pilot-routing-signing-private.pem \
  --delegate-public /secure/location/notespro-delegate-public.pem \
  --key-id notespro-2027-q1 --days 90 \
  --output /secure/location/notespro-delegation.json

python scripts/sign_notes_pro.py \
  --key /secure/location/notespro-delegate.pem \
  --delegation /secure/location/notespro-delegation.json \
  --revision 5 --expires 2027-01-15 \
  --endpoint https://seedlingappstudio.pages.dev/notes-pro/
```

Choose an expiry within the delegated certificate's validity. A delegated certificate is public data; **neither private key is**. Retiring a compromised root or breaking compatibility with older format-1 builds requires an app-update and support plan. A signed configuration is not a substitute for server-side license checks.

## Testing and rollout

Build the Notes Pro feature branch `feature/signed-endpoint-discovery-pilot` and run its unit tests; the enhanced *Notes Pro · Endpoint Test* debug launcher shows current revision, source, expiry, candidate routes, and retry status. With revision 4 published, switch on **Simulate primary outage**, then run **Check endpoint and failover**. The test should reach `pilot-health.json` with HTTP 200. Toggle airplane mode, force a fetch, and verify the cached signed route remains available.

The release build does not show the test launcher or enable paid-license enforcement. No other Seedling applications have been modified.

Limitations before using this system for real premium licensing: Google Play entitlement verification must remain server-side; a signed configuration does not authenticate a customer; rollback data can be altered on a rooted/compromised device; offline-license grace periods need an independent signed entitlement policy; and GitHub/CDN availability, traffic limits, and provider terms must be reviewed before broad commercial distribution.
