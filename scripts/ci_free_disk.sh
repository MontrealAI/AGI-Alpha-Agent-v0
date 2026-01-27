#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

echo "Disk usage before cleanup:"
df -h

workspace="${GITHUB_WORKSPACE:-$(pwd)}"
if [[ -d "$workspace" ]]; then
  rm -rf \
    "$workspace/.cache" \
    "$workspace/.npm-cache" \
    "$workspace/.pytest_cache" \
    "$workspace/.mypy_cache" \
    "$workspace/.ruff_cache" \
    "$workspace/.coverage" \
    "$workspace/artifacts" \
    "$workspace/tests/contracts/node_modules" \
    "$workspace/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules" \
    "$workspace/alpha_factory_v1/core/interface/web_client/node_modules" || true
fi

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

if [[ -n "${HOME:-}" ]]; then
  rm -rf \
    "$HOME/.cache/pip" \
    "$HOME/.cache/pip-tools" \
    "$HOME/.cache/pypoetry" \
    "$HOME/.cache/huggingface" \
    "$HOME/.cache/ms-playwright" \
    "$HOME/.cache/torch" \
    "$HOME/.cache/uv" \
    "$HOME/.cache/npm" \
    "$HOME/.cache/yarn" \
    "$HOME/.cache/pnpm" \
    "$HOME/.cache/node-gyp" \
    "$HOME/.npm/_cacache" \
    "$HOME/.cache/matplotlib" || true
fi

workspace_root="${GITHUB_WORKSPACE:-$(pwd)}"
if [[ -n "${workspace_root:-}" && -d "${workspace_root}" ]]; then
  rm -rf \
    "${workspace_root}/.npm-cache" \
    "${workspace_root}/.tmp" \
    "${workspace_root}/.pytest_cache" \
    "${workspace_root}/.mypy_cache" \
    "${workspace_root}/.ruff_cache" \
    "${workspace_root}/.coverage" \
    "${workspace_root}/artifacts" || true
fi

for cache_var in FETCH_ASSETS_DIR INSIGHT_ASSET_ROOT PYODIDE_CACHE_DIR NPM_CONFIG_CACHE; do
  cache_path="${!cache_var:-}"
  if [[ -n "${cache_path}" ]]; then
    rm -rf "${cache_path}" || true
  fi
done

if [[ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ]]; then
  rm -rf "$PLAYWRIGHT_BROWSERS_PATH" || true
fi

if command -v docker >/dev/null 2>&1; then
  sudo docker image prune --all --force || true
  sudo docker builder prune --all --force || true
  sudo docker system prune --all --force --volumes || true
fi

echo "Disk usage after cleanup:"
df -h
