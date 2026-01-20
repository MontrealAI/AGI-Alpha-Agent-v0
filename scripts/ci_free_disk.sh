#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

echo "Disk usage before cleanup:"
df -h

sudo rm -rf /usr/share/dotnet \
  /opt/ghc \
  /usr/local/lib/android \
  /usr/local/share/boost \
  /usr/share/swift \
  /opt/hostedtoolcache/CodeQL \
  /opt/hostedtoolcache/Java \
  /opt/hostedtoolcache/Ruby \
  /opt/hostedtoolcache/Perl \
  /opt/hostedtoolcache/Go \
  /opt/hostedtoolcache/Swift \
  /usr/local/share/powershell || true

sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/* /var/cache/apt/archives || true

if command -v docker >/dev/null 2>&1; then
  sudo docker image prune --all --force || true
  sudo docker builder prune --all --force || true
  sudo docker system prune --all --force --volumes || true
fi

echo "Disk usage after cleanup:"
df -h
