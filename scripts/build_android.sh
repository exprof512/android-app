#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_DIR="$ROOT/android"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

if [[ ! -d "$ANDROID_DIR" ]]; then
  echo "android/ module missing" >&2
  exit 1
fi

if [[ ! -f "$ANDROID_DIR/local.properties" ]]; then
  if [[ -z "${ANDROID_HOME:-}" || ! -d "$ANDROID_HOME" ]]; then
    echo "Set ANDROID_HOME or create android/local.properties with sdk.dir=..." >&2
    exit 1
  fi
  echo "sdk.dir=$ANDROID_HOME" > "$ANDROID_DIR/local.properties"
fi

cd "$ANDROID_DIR"
API_BASE_URL="${FOODAI_API_BASE_URL:-http://193.32.179.108:8080/api/v1/}"
./gradlew :app:assembleDebug --no-daemon --max-workers=1 -Pfoodai.apiBaseUrl="$API_BASE_URL"
APK="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [[ ! -f "$APK" ]]; then
  echo "Debug APK not found at $APK" >&2
  exit 1
fi
echo "API_BASE_URL=$API_BASE_URL" >&2
echo "$APK"
