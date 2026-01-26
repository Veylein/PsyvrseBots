# Redeploy Ludus Docker image (Windows PowerShell)
# Usage: Set your DISCORD_TOKEN env var, then run this script as Administrator or with Docker access.

param(
    [string]$ImageName = "ludus:latest",
    [string]$ContainerName = "ludus",
    [string]$DockerfilePath = ".",
    [switch]$UseCompose
n)

if ($UseCompose) {
    Write-Host "Rebuilding with docker-compose..."
    docker compose down --remove-orphans
    docker compose build --pull
    docker compose up -d
    exit $LASTEXITCODE
}

Write-Host "Building image: $ImageName"
docker build -t $ImageName $DockerfilePath

Write-Host "Stopping existing container (if any): $ContainerName"
try { docker rm -f $ContainerName } catch { }

# Ensure DISCORD_TOKEN is set in environment before running
if (-not $env:DISCORD_TOKEN) {
    Write-Warning "DISCORD_TOKEN environment variable is not set. The container will start but will fail to login without a valid token."
}

Write-Host "Starting container: $ContainerName"
# Example run mapping common files; adjust ports/volumes as needed for your host
docker run -d --name $ContainerName \
  -e DISCORD_TOKEN="$env:DISCORD_TOKEN" \
  -v "$PWD/data":/app/data \
  -v "$PWD/Ludus/data":/app/Ludus/data \
  --restart unless-stopped $ImageName

if ($LASTEXITCODE -eq 0) { Write-Host "Redeploy script completed." } else { Write-Error "Redeploy script failed with exit code $LASTEXITCODE" }
