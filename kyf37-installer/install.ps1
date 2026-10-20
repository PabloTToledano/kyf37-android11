# Windows launcher. Missing Python is installed privately, without changing PATH.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = $null
foreach ($name in @('py', 'python')) {
    $candidate = Get-Command $name -ErrorAction SilentlyContinue
    if ($candidate) {
        $prefix = @()
        if ($name -eq 'py') { $prefix = @('-3') }
        & $candidate.Source @prefix -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate.Source
            break
        }
    }
}
if (-not $python) {
    $prefix = @()
    $python = Join-Path $PSScriptRoot '.python\python.exe'
    if (-not (Test-Path $python)) {
        Write-Host 'Downloading a private Python runtime...'
        New-Item -ItemType Directory -Force '.downloads' | Out-Null
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $installer = Join-Path $PSScriptRoot '.downloads\python-3.12.10-amd64.exe'
        Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer -UseBasicParsing
        $signature = Get-AuthenticodeSignature $installer
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
            throw 'Python installer signature could not be verified.'
        }
        $target = Join-Path $PSScriptRoot '.python'
        $process = Start-Process -FilePath $installer -ArgumentList @('/quiet', 'InstallAllUsers=0', "TargetDir=`"$target`"", 'PrependPath=0', 'Include_launcher=0', 'Include_test=0') -Wait -PassThru
        if ($process.ExitCode -notin @(0, 3010)) { throw "Python installation failed: $($process.ExitCode)" }
    }
}
& $python @prefix bootstrap.py @args
exit $LASTEXITCODE
