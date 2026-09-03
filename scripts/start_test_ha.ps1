# PowerShell script to run local Home Assistant test container
$configPath = (Resolve-Path "$PSScriptRoot\..\test_config").Path
Write-Host "Starting Home Assistant test container using config: $configPath"

# Remove existing test container if running
docker rm -f ha-test-four-noks 2>$null

# Start container
docker run -d `
  --name ha-test-four-noks `
  -p 8123:8123 `
  -v "${configPath}:/config" `
  ghcr.io/home-assistant/home-assistant:stable

Write-Host "Container started! Logs command: docker logs -f ha-test-four-noks"
Write-Host "Home Assistant will be available at: http://localhost:8123"
