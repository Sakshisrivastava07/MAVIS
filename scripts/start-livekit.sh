#!/usr/bin/env sh
# Start the native local LiveKit development server.
cd "$(dirname "$0")/.."
livekit-server --dev
