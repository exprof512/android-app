#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK="${1:-$ROOT/android/app/build/outputs/apk/debug/app-debug.apk}"

if ! command -v adb >/dev/null 2>&1; then
  echo "adb not found. Install Android platform-tools and retry, or install the APK manually:"
  echo "  $APK"
  exit 1
fi

if [[ ! -f "$APK" ]]; then
  echo "APK missing: $APK"
  echo "Run scripts/build_android.sh first."
  exit 1
fi

if ! adb get-state >/dev/null 2>&1; then
  echo "No adb device/emulator connected."
  exit 1
fi

adb install -r "$APK"
echo "Installed $APK"
