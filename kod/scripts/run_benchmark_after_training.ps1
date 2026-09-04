param(
    [Parameter(Mandatory = $true)]
    [int]$TrainingProcessId,

    [string]$CorefSegRoot = 'C:\Users\Kamil\Desktop\mg',

    [string]$Mg2Root = 'C:\Users\Kamil\mg2'
)

$ErrorActionPreference = 'Stop'
$outputDirectory = Join-Path $Mg2Root 'wyniki\benchmark-inference'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

$training = Get-Process -Id $TrainingProcessId -ErrorAction SilentlyContinue
if ($null -ne $training) {
    Wait-Process -Id $TrainingProcessId
}

Set-Location -LiteralPath $Mg2Root
& python -u 'kod\scripts\benchmark_inference_runtime.py' `
    --corefseg-root $CorefSegRoot `
    --documents 60 `
    --repeats 3 `
    --segment 1024 `
    --output $outputDirectory

$exitCode = $LASTEXITCODE
$status = [ordered]@{
    finished_at = (Get-Date).ToUniversalTime().ToString('o')
    exit_code = $exitCode
    report = (Join-Path $outputDirectory 'RAPORT.md')
    results = (Join-Path $outputDirectory 'results.json')
}
$status | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $outputDirectory 'status.json')
exit $exitCode
