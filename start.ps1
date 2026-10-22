# ============================================
# 项目台账 一键启动/停止：后端 8100 + 前端 3000
# 启动：双击「启动项目台账.bat」或执行 .\start.ps1
# 停止：双击「停止项目台账.bat」或执行 .\start.ps1 -Stop
# ============================================
param([switch]$Stop)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = "D:\developTools\python\python3.14.5\python.exe"
if (-not (Test-Path $py)) { $py = "python" }   # 其他机器回退 PATH

# ---- 停止模式：只停台账进程（python/node），其他程序占用端口时跳过不误杀 ----
if ($Stop) {
  $stopped = @()
  foreach ($port in @(8100, 3000)) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
      $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
      if ($null -eq $proc) { continue }
      if ($proc.ProcessName -in @("python", "pythonw", "node")) {
        taskkill.exe /PID $procId /T /F 2>&1 | Out-Null
        $stopped += "端口 $port : PID $procId ($($proc.ProcessName))"
      } else {
        Write-Host "端口 $port 被 $($proc.ProcessName) (PID $procId) 占用，非台账进程，已跳过"
      }
    }
  }
  if ($stopped.Count -eq 0) {
    Write-Host "未发现运行中的台账服务。"
  } else {
    $stopped | ForEach-Object { Write-Host "已停止 $_" }
    Write-Host "项目台账已全部停止。"
  }
  exit 0
}

# ---- 依赖自检/安装（首次） ----
if (-not (Test-Path "$root\backend\.deps_installed")) {
  & $py -m pip install -r "$root\backend\requirements.txt"
  New-Item -ItemType File -Path "$root\backend\.deps_installed" | Out-Null
}

# ---- 后端（8100：8000 被本机 BidAlert 占用） ----
$backendRunning = $false
try {
  $h = Invoke-RestMethod http://127.0.0.1:8100/api/health -TimeoutSec 2
  if ($h.status -eq "ok") { $backendRunning = $true }
} catch {}
if (-not $backendRunning) {
  Start-Process -FilePath $py `
    -ArgumentList "-X","utf8","-m","uvicorn","app.main:app","--port","8100" `
    -WorkingDirectory "$root\backend" -WindowStyle Minimized
}

# ---- 前端（3000，代理 /api -> 8100） ----
$frontendRunning = $false
try {
  $f = Invoke-WebRequest http://127.0.0.1:3000/ -UseBasicParsing -TimeoutSec 2
  if ($f.StatusCode -eq 200) { $frontendRunning = $true }
} catch {}
if (-not $frontendRunning) {
  if (-not (Test-Path "$root\frontend\node_modules")) {
    Push-Location "$root\frontend"; npm install; Pop-Location
  }
  Start-Process -FilePath "cmd" -ArgumentList "/c","npm","run","dev" `
    -WorkingDirectory "$root\frontend" -WindowStyle Minimized
}

Start-Sleep -Seconds 4
Start-Process "http://localhost:3000"
Write-Host "项目台账已启动：前端 http://localhost:3000  后端 http://127.0.0.1:8100/docs"
