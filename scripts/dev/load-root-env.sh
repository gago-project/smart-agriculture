#!/usr/bin/env bash
set -euo pipefail

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "请使用 source scripts/dev/load-root-env.sh"
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE="${ROOT_DIR}/.env"
EXCLUDE_PATTERN="${LOAD_ROOT_ENV_EXCLUDE_PATTERN:-}"
KEYCHAIN_SERVICE="${SMART_AGRICULTURE_KEYCHAIN_SERVICE:-smart-agriculture-local}"

load_secret_from_keychain() {
  local key_name=$1
  local key_value

  if [ -n "${!key_name:-}" ]; then
    return 0
  fi

  if ! command -v security >/dev/null 2>&1; then
    return 0
  fi

  if key_value=$(security find-generic-password -a "${key_name}" -s "${KEYCHAIN_SERVICE}" -w 2>/dev/null); then
    if [ -n "${key_value}" ]; then
      export "${key_name}=${key_value}"
    fi
  fi
}

load_secret_from_keychain "QWEN_API_KEY"
load_secret_from_keychain "SONIOX_API_KEY"

if [ ! -f "${ENV_FILE}" ]; then
  return 0
fi

while IFS= read -r export_command; do
  eval "${export_command}"
done < <(
  python3 - "${ENV_FILE}" "${EXCLUDE_PATTERN}" <<'PY'
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

env_file = Path(sys.argv[1])
exclude_pattern = sys.argv[2]
exclude_regex = re.compile(exclude_pattern) if exclude_pattern else None

for raw_line in env_file.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        continue
    if exclude_regex and exclude_regex.search(key):
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    print(f'if [ -z "${{{key}:-}}" ]; then export {key}={shlex.quote(value)}; fi')
PY
)
