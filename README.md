# Atelpix Secure Client Dashboard — LAN Team Edition

Windows desktop application with two launch modes in one executable:
- Owner Dashboard: full local client management, encrypted local database, password + TOTP/recovery authentication.
- Team Viewer (`--team` shortcut): read-only client list and world clock, polling every 5 seconds.

## Network design
- No cloud, VPN, relay, public IP, router port-forwarding, or external account.
- Owner PC hosts an HTTPS read-only API on TCP 8765 on the private LAN.
- Team PCs connect using Owner PC's private LAN URL, a random bearer token, and a SHA-256 certificate fingerprint pin.
- Owner must be powered on, unlocked, and on the same LAN for fresh updates. Team viewer keeps the last data it displayed only while the app remains open; this release does not implement durable offline cache.
- Owner can stop the LAN service to revoke all Team access. Restarting the service creates a new random token; distribute the new token to authorized Team users.
- Future personal-server migration is supported at the protocol boundary, but a separate server deployment/migration utility is not included in this build.

## Build / install
A GitHub Actions workflow is included at `.github/workflows/build-windows-installer.yml`. Upload this source to a private GitHub repository, then run **Actions → Build Atelpix Windows Installer → Run workflow**. The workflow builds the self-contained Windows app and compiles `Atelpix-Secure-Client-Dashboard-Setup.exe` on a Windows runner. See `WINDOWS-INSTALLER-BUILD-NO-LOCAL-PYTHON.md`. End-user PCs do not need Python or Inno Setup.

The current ChatGPT execution environment is Linux and has no Windows build runner or Inno Setup compiler. Therefore the actual Windows `.exe` has not been generated or validated here. The ZIP is a build package, not an installer.

## LAN setup
1. Install the same setup on Owner PC and both Team PCs.
2. Ensure all three are on the same private Wi-Fi/LAN. Set Windows network profile to Private.
3. Owner opens Owner Dashboard, unlocks it, opens Settings → START / VIEW TEAM LAN ACCESS.
4. Share the displayed URL, access token, and certificate fingerprint with authorized Team users over a trusted channel.
5. Team opens the Team Viewer shortcut and enters those three values.
6. Stop access from Owner Settings → STOP TEAM LAN ACCESS. This stops the server and invalidates current sessions. Start again to issue a fresh token.

## Security boundaries
- HTTPS TLS 1.2+; self-signed certificate pinned by SHA-256 fingerprint in Team client.
- Random 288-bit bearer token; no anonymous API endpoints except unauthenticated TCP/TLS handshake.
- API exposes only GET health/clients/clocks; all write verbs return 405.
- Team UI has no add/edit/delete/export controls. A person who can view information can still photograph, screenshot, transcribe, or inspect data available to their account; software cannot guarantee prevention of all copying.
- This LAN build has not undergone independent penetration testing or real Windows 10/11 testing. Windows Firewall behavior, Wi-Fi client isolation, antivirus false positives, and TLS behavior must be verified on target PCs before production client data is entered.
- Keep Owner PC physically secure; use a strong Owner password, keep recovery codes private, and back up encrypted database files.
