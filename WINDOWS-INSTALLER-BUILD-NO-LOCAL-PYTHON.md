# Build the Atelpix Windows installer without installing Python on your PCs

This project source has 8 automated tests passing in the development environment. The Windows desktop build itself has not yet been run or validated on Windows.

## What this does

GitHub Actions builds the Windows executable and Inno Setup installer on a temporary Windows build machine. You do **not** install Python or Inno Setup on the Owner or Team PCs. The final installer is intended to be installed on all three PCs.

## One-time build steps (GitHub account required)

1. Sign in to GitHub and create a **private** repository, for example `atelpix-team-dashboard`.
2. Upload the complete contents of this project ZIP to the repository's main branch. Include the hidden `.github` folder and its `workflows/build-windows-installer.yml` file.
3. Open the repository's **Actions** tab.
4. Select **Build Atelpix Windows Installer** in the left sidebar.
5. Click **Run workflow** and confirm **Run workflow**.
6. Wait for the workflow to finish successfully. Open the completed run and download the artifact named **Atelpix-Windows-Installer**.
7. Extract the artifact ZIP. It contains `Atelpix-Secure-Client-Dashboard-Setup.exe`.

## Install

Run the Setup `.exe` on the Owner PC and both Team PCs. Choose the Owner Dashboard shortcut only on the Owner PC; use the Team Viewer shortcut on the two Team PCs.

## Important limitations

- This workflow creates the installer; it does not mean the installer has already been built.
- The build must complete successfully before an `.exe` exists.
- Windows 10/11, LAN connectivity, firewall behavior, and the packaged executable must be tested on the actual PCs before entering real client information.
- This app's current LAN design requires Owner PC to remain powered on and connected for fresh Team updates. Team PCs do not receive new changes while Owner PC is off.
- Keep the GitHub repository private because it contains application source code. Do not upload client database files, access tokens, recovery codes, or private certificates.
