<#
.SYNOPSIS
  Run ONE load test from the load generator (Machine B) against the triage service (Machine A).

.DESCRIPTION
  Tests:
    mixed   R1 + R3: 72 POST /tickets + 214 GET /search + 458 GET /stats per hour, 20 minutes
    r2      R2:      110 POST /tickets per hour, 30 minutes (no search/stats)
    stress  stress:  POST /tickets stepped up from 120/h to 480/h in 60/h steps, 8 minutes per step (about 1 hour)
  Add -Dry for a short rehearsal (2 minutes; stress = 3 steps of 1 minute). Dry runs are named dry-... and are not results.

  BEFORE running, on Machine A (the laptop) run the matching command that this script prints, so the service
  uses the right model, an empty database and the same run id:
      python scripts/prepare_run.py --model <model> --run-id <run id>

  Output (repo folder results\load\<run id>\): results.jtl, jmeter.log, jmeter_stdout.txt, run.properties, run_info.json

.EXAMPLE
  .\jmeter\run_load_test.ps1 -Test mixed -Model qwen2.5:7b -Run 1
  .\jmeter\run_load_test.ps1 -Test mixed -Model qwen2.5:1.5b -Run 1 -Dry
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('mixed', 'r2', 'stress')][string]$Test,
    [Parameter(Mandatory = $true)][string]$Model,
    [int]$Run = 1,
    [string]$TargetHost = '192.168.18.104',
    [int]$Port = 8000,
    [string]$JMeterHome = '',
    [switch]$Dry,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $JMeterHome) {
    if ($env:JMETER_HOME) { $JMeterHome = $env:JMETER_HOME } else { $JMeterHome = Join-Path (Split-Path -Parent $repo) 'apache-jmeter-5.6.3' }
}
$jmeter = Join-Path $JMeterHome 'bin\jmeter.bat'
if (-not (Test-Path $jmeter)) { throw "JMeter not found at $jmeter. Pass -JMeterHome <folder>." }
$plan = Join-Path $PSScriptRoot 'triage_load.jmx'

# ---- test definitions -------------------------------------------------------------------------------------------
$prefix = ''
if ($Dry) { $prefix = 'dry-' }
$runId = ('{0}load-{1}-{2}-r{3}' -f $prefix, $Test, ($Model -replace ':', '-'), $Run)
$props = [ordered]@{ host = $TargetHost; port = $Port; run_id = $runId }
$info = [ordered]@{ test = $Test; model = $Model; run = $Run; run_id = $runId; dry = [bool]$Dry; target = "http://${TargetHost}:$Port" }

if ($Test -eq 'mixed') {
    $dur = 20; if ($Dry) { $dur = 2 }
    $props['duration_min'] = $dur; $props['post_per_hour'] = 72; $props['search_per_hour'] = 214; $props['stats_per_hour'] = 458; $props['drain_min'] = 2
    $info['duration_min'] = $dur; $info['post_per_hour'] = 72; $info['search_per_hour'] = 214; $info['stats_per_hour'] = 458; $info['drain_min'] = 2
}
elseif ($Test -eq 'r2') {
    $dur = 30; if ($Dry) { $dur = 2 }
    $props['duration_min'] = $dur; $props['post_per_hour'] = 110; $props['search_per_hour'] = 0; $props['stats_per_hour'] = 0; $props['drain_min'] = 2
    $info['duration_min'] = $dur; $info['post_per_hour'] = 110; $info['search_per_hour'] = 0; $info['stats_per_hour'] = 0; $info['drain_min'] = 2
}
else {
    # stress: constant-rate steps joined by 10-second ramps ("random_arrivals" twice in a row keeps the rate constant)
    $stepMin = 8; $rates = @(120, 180, 240, 300, 360, 420, 480)
    if ($Dry) { $stepMin = 1; $rates = @(120, 240, 360) }
    $ramp = 10
    $sched = "rate($($rates[0])/hour)"
    $steps = @(); $t = 0
    for ($i = 0; $i -lt $rates.Count; $i++) {
        if ($i -gt 0) { $sched += " random_arrivals($ramp sec) rate($($rates[$i])/hour)"; $t += $ramp }
        $sched += " random_arrivals($stepMin min)"
        $steps += [ordered]@{ rate_per_hour = $rates[$i]; start_s = $t; end_s = $t + $stepMin * 60 }
        $t += $stepMin * 60
    }
    # a trailing pause keeps JMeter running while the queue drains; without it JMeter interrupts requests still in flight
    $drain = 12; if ($Dry) { $drain = 1 }
    $sched += " pause($drain min)"
    $props['post_schedule'] = $sched
    $props['search_schedule'] = 'rate(0) random_arrivals(1 sec)'
    $props['stats_schedule'] = 'rate(0) random_arrivals(1 sec)'
    $info['drain_min'] = $drain; $info['step_min'] = $stepMin; $info['ramp_s'] = $ramp; $info['steps'] = $steps; $info['post_schedule'] = $sched
}
$props['sample_variables'] = 'row,seq'

# ---- output folder ----------------------------------------------------------------------------------------------
$out = Join-Path $repo "results\load\$runId"
if ((Test-Path $out) -and -not $Force) { throw "$out already exists. Results are never overwritten; pick another -Run or pass -Force." }

Write-Host ""
Write-Host "Run id : $runId"
Write-Host "Target : http://${TargetHost}:$Port"
Write-Host ""
Write-Host "On the LAPTOP (Machine A) this must already have been run:"
Write-Host "    python scripts/prepare_run.py --model $Model --run-id $runId" -ForegroundColor Yellow
Write-Host ""

# ---- safety checks ----------------------------------------------------------------------------------------------
try { $stats = Invoke-RestMethod -Uri "http://${TargetHost}:$Port/stats" -TimeoutSec 10 }
catch { throw "Cannot reach the service at http://${TargetHost}:$Port/stats : $($_.Exception.Message)" }
if ($stats.total -gt 1 -and -not $Force) {
    throw "The service database holds $($stats.total) tickets (expected 1: the warm-up). Run prepare_run.py on the laptop first (or pass -Force)."
}
Write-Host "Service reachable; database holds $($stats.total) ticket(s) (the excluded warm-up)."
New-Item -ItemType Directory -Force $out | Out-Null   # created only now, so a failed pre-check never leaves a blocking folder

# ---- write settings, then run -----------------------------------------------------------------------------------
$propLines = foreach ($k in $props.Keys) { "$k=$($props[$k])" }
Set-Content -Path (Join-Path $out 'run.properties') -Value $propLines -Encoding ASCII

$info['jmeter_home'] = $JMeterHome
try { $info['git_commit'] = (git -C $repo rev-parse HEAD 2>$null) } catch { $info['git_commit'] = 'unknown' }
$info['started_at_utc'] = (Get-Date).ToUniversalTime().ToString('o')
$info['started_epoch_ms'] = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())

Write-Host "Starting JMeter (non-GUI). Press Ctrl+C to abort; an aborted run must be repeated."
$jmArgs = @('-n', '-t', $plan, '-q', (Join-Path $out 'run.properties'), '-l', (Join-Path $out 'results.jtl'), '-j', (Join-Path $out 'jmeter.log'))
Push-Location $PSScriptRoot   # the plan reads its CSV data files from this folder
# Java (25 and later) prints harmless warnings on its error stream, for example "A terminally deprecated method in
# sun.misc.Unsafe has been called". Windows PowerShell would turn such text into a terminating error under
# $ErrorActionPreference = 'Stop' and kill JMeter, so errors are not fatal while JMeter runs; whether the run
# worked is decided below from the exit code and the results file.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try { & $jmeter @jmArgs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath (Join-Path $out 'jmeter_stdout.txt') }
finally { $ErrorActionPreference = $prevEap; Pop-Location }
$jmExit = $LASTEXITCODE
$jtl = Join-Path $out 'results.jtl'
$produced = (Test-Path $jtl) -and ((Get-Item $jtl).Length -gt 300)
if (-not $produced -or $jmExit -ne 0) {
    $failed = "$out-FAILED-" + (Get-Date).ToString('yyyyMMdd-HHmmss')
    Move-Item -Path $out -Destination $failed
    throw "JMeter did not complete normally (exit code $jmExit; results file produced: $produced). Output kept in $failed. Fix the cause, run prepare_run.py on the laptop again, then repeat this run."
}

$info['finished_at_utc'] = (Get-Date).ToUniversalTime().ToString('o')
$info['finished_epoch_ms'] = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$info | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $out 'run_info.json') -Encoding UTF8

Write-Host ""
Write-Host "Done. Results in $out"
Write-Host "Next: python scripts/summarise_load.py results/load/$runId   (after pulling the laptop's logs/requests.jsonl)"
