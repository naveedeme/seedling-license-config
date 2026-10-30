# Seedling Endpoint Discovery — Notes Pro pilot

This public repository contains **routing metadata only**. It does not hold license entitlements, private keys, Google credentials, or any license-verification code.

`notes-pro.json` is a signed envelope. `payload` is base64url of UTF-8 JSON containing `app`, `revision`, `endpoint`, `issuedAt`, and `expiresAt`. `signature` is an ECDSA P-256/SHA-256 signature over the **decoded payload bytes**. The corresponding public key is embedded in the Notes Pro pilot app. GitHub hosts the file but cannot authorize different endpoints without the private signing key.

Notes Pro started with **revision 1** pointing to `https://seedlingappstudio.pages.dev/notes-pro/`. **Revision 2** switched to `https://raw.githubusercontent.com/naveedeme/seedling-license-config/main/pilot-health.json` to test account-independent routing. The current signed **revision 3** restores `https://seedlingappstudio.pages.dev/notes-pro/`. These are website/test endpoints, not licensing Workers. The debug-only diagnostics launcher fetches and validates the signed configuration; the production Notes Pro experience is unchanged.

## Publish a new route

Keep the pilot private key **outside GitHub** and back it up securely. On your computer:

```bash
python -m pip install cryptography
python scripts/sign_notes_pro.py --key /secure/location/pilot-routing-signing-private.pem --revision 2 --endpoint https://seedlingappstudio.pages.dev/
git add notes-pro.json && git commit -m "Pilot: switch Notes Pro route" && git push
```

Install Notes Pro's debug APK, open **Notes Pro · Endpoint Test**, and tap **Fetch signed configuration** to see the new verified endpoint. Revisions must increase: clients reject lower revisions after accepting a newer one. Avoid signing an incorrect URL, because rollback protection means fixing it requires a *higher* revision. If GitHub is down, the app retains the last valid signed route, or falls back to its bundled default on a first run. This demo does not prevent use of notes.

Current URL: `https://raw.githubusercontent.com/naveedeme/seedling-license-config/main/notes-pro.json`

The route-signing key is for this pilot, **not** a Google Play license key. Before production licensing, review key custody and rotation, backend entitlement checks, license grace periods, and whether GitHub raw hosting is appropriate for your traffic.
