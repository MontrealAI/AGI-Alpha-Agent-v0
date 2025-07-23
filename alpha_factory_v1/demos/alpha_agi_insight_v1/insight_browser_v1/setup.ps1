#!/usr/bin/env pwsh
# SPDX-License-Identifier: Apache-2.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Ensure Node.js 22+
node build/version_check.js

if (Test-Path 'node_modules') {
    Write-Host 'node_modules already present'
    exit 0
}

Write-Host 'Installing npm dependencies...'
npm ci --no-progress
if ($LASTEXITCODE -ne 0) {
    Write-Error 'ERROR: npm ci failed'
    exit 1
}

