# Windows build notes

The supplied `build_windows.bat` creates one self-contained executable with PyInstaller. The end-user PCs do not need Python or Inno Setup after the installer is built.

Build machine requirements: Windows 10/11 x64, Python 3.11+ and Inno Setup 6. These are build-time requirements only. Run `build_windows.bat`, then compile `installer.iss` with Inno Setup to produce `installer-output\Atelpix-Secure-Client-Dashboard-Setup.exe`.

The installer installs one executable and creates two shortcuts: **Atelpix Owner Dashboard** and **Atelpix Team Viewer**. The latter starts the same executable with `--team`. The installer adds a Windows Firewall inbound rule for TCP 8765 on Private networks and removes that rule on uninstall.

The current execution environment is Linux and has neither a Windows build runner nor Inno Setup. No Windows `.exe` or installer binary is included or claimed as tested in this ZIP.
