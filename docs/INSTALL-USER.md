# Atelpix Team Edition — User Installation

**Installer status:** This project contains the complete source and Windows build recipe. The current environment cannot compile a Windows installer; the `Setup.exe` is not included.

When a Windows-built installer is supplied:
1. Run `Atelpix-Secure-Client-Dashboard-Setup.exe` on each of the three Windows 10/11 PCs.
2. On Owner PC, launch **Atelpix Owner Dashboard** and create the Owner account. Save the authenticator secret and recovery codes offline.
3. On Team PCs, launch **Atelpix Team Viewer**.
4. Put all PCs on the same private Wi-Fi/LAN. Owner starts LAN access and securely shares the HTTPS URL, token, and certificate fingerprint.
5. Team enters those values. The client list refreshes every five seconds.

The Owner PC must remain on and the Owner app unlocked for new updates. If Owner goes offline, the Team app reports disconnected; it does not have a persistent offline copy in this release.
