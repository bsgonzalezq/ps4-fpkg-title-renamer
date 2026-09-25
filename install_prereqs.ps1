# Install / verify prerequisites for ps4-pkg-title-renamer on Windows 10/11: Python 3.8+ and git.
# Run from the repo folder:  powershell -ExecutionPolicy Bypass -File .\install_prereqs.ps1
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
$MinPy = [version]'3.8'

function Find-Python {
    # "py" is the Python launcher from python.org; "python" may be the Microsoft Store stub
    foreach ($cmd in @('py', 'python')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $v = & $cmd -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) { return @{ Cmd = $cmd; Version = [version]$v } }
        }
    }
    return $null
}

function Install-WithWinget($id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Install $id manually (https://www.python.org / https://git-scm.com)."
    }
    Write-Host "Installing $id ..."
    winget install -e --id $id --accept-source-agreements --accept-package-agreements
    # pick up PATH changes made by the installer in this session
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

$py = Find-Python
if (-not $py) {
    Install-WithWinget 'Python.Python.3.12'
    $py = Find-Python
    if (-not $py) { throw 'Python installed, but not on PATH yet: open a new terminal and run this script again.' }
}
if ($py.Version -lt $MinPy) { throw "Python $MinPy+ required, found $($py.Version). Please upgrade Python." }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Install-WithWinget 'Git.Git'
}

# No third-party packages today; this keeps working if any are added later
if ((Test-Path requirements.txt) -and (Select-String -Path requirements.txt -Pattern '^\s*[^#\s]' -Quiet)) {
    & $py.Cmd -m pip install --user -r requirements.txt
}

Write-Host ''
Write-Host "OK: Python $($py.Version) ($($py.Cmd)), $(git --version)"
& $py.Cmd ps4_rename.py --help | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "OK: ps4_rename.py runs. Try: $($py.Cmd) ps4_rename.py --help" }
