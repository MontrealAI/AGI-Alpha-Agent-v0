[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Windows Setup Guide

This page collects tips for running the project on Windows.

## Enable WSL 2
Run these commands in an elevated PowerShell window:

```powershell
wsl --install
wsl --set-default-version 2
wsl --update
```

Clone the repository inside your WSL home directory to avoid path translation issues.

## Recommended Python distribution
Install Python 3.11 or 3.13 from [python.org](https://www.python.org/downloads/). The Microsoft Store version often restricts permissions.
Create the virtual environment from PowerShell or your WSL shell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Docker Desktop configuration
Enable **Use the WSL 2 based engine** under **Settings → General** and turn on WSL integration for your distribution. If volume mounts fail, use the `\\wsl$` prefix or an absolute path with the drive letter and ensure the drive is shared under **Settings → Resources → File sharing**.

Some features, like GPU acceleration, require Windows 11 with the latest WSL build.

## Limitations
Containers may run slower when the repository resides on `/mnt/c`. Keep your working directory inside the Linux file system to reduce path translation overhead.
