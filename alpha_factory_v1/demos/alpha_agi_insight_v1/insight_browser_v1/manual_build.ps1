#!/usr/bin/env pwsh
# SPDX-License-Identifier: Apache-2.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Verify Node.js 22+
try {
    node build/version_check.js
} catch {
    Write-Error 'Node.js 22+ is required.'
    exit 1
}

# Verify Python >=3.11
$pyVersionOutput = & python --version
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Python is required.'
    exit 1
}
$match = [regex]::Match($pyVersionOutput, '(\d+)\.(\d+)')
if (!$match.Success -or [int]$match.Groups[1].Value -lt 3 -or ([int]$match.Groups[1].Value -eq 3 -and [int]$match.Groups[2].Value -lt 11)) {
    Write-Error "Python >=3.11 required. Current version: $pyVersionOutput"
    exit 1
}

python manual_build.py @Args
exit $LASTEXITCODE

