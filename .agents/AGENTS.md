# Kumiho Bot & Web Dashboard Rules

## Server Connection and Modifying Remote
1. **NO UNAUTHORIZED CONNECTIONS**: Do NOT connect to the VPS via SSH (e.g. `scp`, `ssh ubuntu@144.24.243.224`) without EXPLICIT permission from the USER for that specific operation.
2. **NO REMOTE BUILDS**: Never run `npm run build` or similar build commands on the server. The application is configured to run differently, and running build commands manually on the server will cause folder permission issues and crashes (e.g., EACCES errors on the `dist` folder).

## Local Environment & PM2
1. **WSL Environment**: The project relies on Linux environments. Whenever possible, terminal processes and server startups should be executed using WSL. 
2. **PM2 Process Manager**: If starting or managing the app, you MUST use `pm2` via WSL. Do not just run raw node/python unless requested.

## Project details
- Server IP: 144.24.243.224 (Ubuntu)
- Local Project Path: `C:\Users\kIrik\OneDrive - ABDULLAH GUL UNIVERSITESI\Masaüstü\kumiho`

Follow these instructions strictly whenever you load this project.
