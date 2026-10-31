# Atelpix Secure Client Dashboard — Security Test Report

**Result: 8 automated tests passed in the available Linux development environment.** This is not an independent security certification.

## Automated checks
- Existing core security/storage tests: password/account setup, TOTP/recovery-code behavior, encrypted database handling, backup/restore integrity and tamper/wrong-password rejection, client CRUD/search, timezone handling.
- LAN integration: HTTPS health endpoint returns 200 with correct bearer token.
- LAN authentication: missing/incorrect token returns 401.
- Read-only API: POST and DELETE return 405; only GET endpoints are implemented.
- TLS pinning material: Team client checks SHA-256 fingerprint of the actual peer certificate before processing response data.
- Data minimization: Team API returns only Client Name, Country, City, Email, Phone and Status; no notes, WhatsApp, website or internal audit data.

## Not tested / limitations
- No Windows 10/11 build, installer, firewall rule or SmartScreen/Defender validation was possible in this Linux environment.
- No real three-PC Wi-Fi/LAN test, router client-isolation test, sleep/resume test or high-load test was performed.
- No independent penetration test, formal cryptographic review or vulnerability scan was performed.
- Owner PC must be on, unlocked and on the same LAN for live updates. The Team Viewer does not yet maintain a durable offline cache when Owner goes offline.
- Team users can still photograph, screenshot or manually transcribe information they are permitted to view. The application does not provide a copy/export feature, but cannot prevent all forms of copying.
- Windows Firewall private-profile rule is added by the provided installer script; verify the network is marked Private. Some managed networks or Wi-Fi client isolation settings may block PC-to-PC traffic.

## Security controls implemented
- Existing encrypted local Owner database and password + TOTP/recovery login.
- LAN service uses TLS 1.2 minimum and a self-signed certificate whose SHA-256 fingerprint is pinned by the Team app.
- Random per-run bearer access token; stopping and restarting the LAN service replaces the token and revokes previous access.
- Read-only GET API; write methods are rejected.
- LAN service is stopped when Owner locks or exits the Owner app.
