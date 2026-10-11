#!/usr/bin/env bash
# One-time per session: voice model + python deps. Safe to re-run.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q kokoro-onnx soundfile pillow numpy 2>&1 | tail -1 || true
mkdir -p .cache
B=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s .cache/kokoro-v1.0.onnx ] || curl -sSL -o .cache/kokoro-v1.0.onnx $B/kokoro-v1.0.onnx
[ -s .cache/voices-v1.0.bin ] || curl -sSL -o .cache/voices-v1.0.bin $B/voices-v1.0.bin
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
ls -la .cache
