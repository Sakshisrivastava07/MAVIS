# PowerShell window for native LiveKit dev server.
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path '.\tools\livekit-server.exe') {
    .\tools\livekit-server.exe --dev
} else {
    livekit-server --dev
}
