#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

echo "::group::Disk usage before cleanup"
df -h
echo "::endgroup::"

sudo rm -rf \
  /usr/share/dotnet \
  /opt/ghc \
  /usr/local/lib/android \
  /usr/local/share/boost \
  /usr/local/share/powershell \
  /usr/share/swift \
  /opt/hostedtoolcache/CodeQL \
  /opt/hostedtoolcache/Java \
  /opt/hostedtoolcache/Perl \
  /opt/hostedtoolcache/Ruby \
  || true

sudo apt-get clean || true
sudo rm -rf /var/lib/apt/lists/* /var/cache/apt/archives || true

if command -v docker >/dev/null 2>&1; then
  sudo docker image prune --all --force || true
  sudo docker builder prune --all --force || true
  sudo docker system prune --all --force --volumes || true
fi

if command -v journalctl >/dev/null 2>&1; then
  sudo journalctl --vacuum-time=1d || true
fi

echo "::group::Disk usage after cleanup"
df -h
echo "::endgroup::"
