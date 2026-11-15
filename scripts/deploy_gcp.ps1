param(
    [string]$Project = 'project-6fff6574-07af-4183-b83',
    [string]$Region = 'southamerica-west1',
    [string]$GcloudPath = 'gcloud',
    [switch]$RebuildSnapshot
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program terminó con código $LASTEXITCODE" }
}
$resolvedGcloud = (Get-Command $GcloudPath -ErrorAction Stop).Source
$env:PATH = (Split-Path -Parent $resolvedGcloud) + ';' + $env:PATH
$billing = & $resolvedGcloud billing projects describe $Project --format=json
if ($LASTEXITCODE -ne 0 -or -not ($billing | ConvertFrom-Json).billingEnabled) { throw 'Proyecto sin facturación habilitada' }
# Never upgrade billing or activate a paid account here. The owner caps all spending at US$300.
Invoke-Checked '.\.venv\Scripts\python.exe' @('-m','unittest','discover','-s','tests','-q')
Invoke-Checked '.\.venv\Scripts\python.exe' @('scripts/evaluate_assistant.py')
Push-Location web
try {
    Invoke-Checked 'npm.cmd' @('ci')
    Invoke-Checked 'npm.cmd' @('run','build')
    Invoke-Checked 'npm.cmd' @('run','lint')
} finally { Pop-Location }
if ($RebuildSnapshot) {
    Invoke-Checked 'docker' @('build','-t','sarwatch-nisar:local','.')
    Invoke-Checked 'docker' @('build','-f','Dockerfile.deploy','-t','sarwatch-nisar:demo','.')
}
$image = "$Region-docker.pkg.dev/$Project/sarwatch/app:" + (Get-Date -Format 'yyyyMMdd-HHmmss')
Invoke-Checked 'docker' @('build','-f','Dockerfile.cloud','-t',$image,'.')
Invoke-Checked $resolvedGcloud @('auth','configure-docker',"$Region-docker.pkg.dev",'--quiet')
Invoke-Checked 'docker' @('push',$image)
Invoke-Checked $resolvedGcloud @('run','deploy','sarwatch',"--project=$Project","--region=$Region","--image=$image",'--port=8080','--cpu=1','--memory=2Gi','--concurrency=4','--min-instances=0','--max-instances=2','--timeout=180','--cpu-throttling',"--service-account=sarwatch-web@$Project.iam.gserviceaccount.com",'--set-env-vars=DATA_DIR=/app/data,REMOTE_DATA_DIR=/app/remote-data/derived,ASSISTANT_LLM=none','--add-volume=mount-path=/app/remote-data,type=cloud-storage,bucket=sarwatch-525550511866-data,readonly=true','--allow-unauthenticated','--quiet')
$url = & $resolvedGcloud run services describe sarwatch "--project=$Project" "--region=$Region" '--format=value(status.url)'
if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener la URL' }
Invoke-Checked '.\.venv\Scripts\python.exe' @('scripts/check_api.py',$url.Trim())
Write-Output "SARWatch verificado: $url"
