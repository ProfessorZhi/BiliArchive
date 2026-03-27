param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [string]$NotesFile
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

if (-not $NotesFile) {
    $NotesFile = "release-notes-$Tag.md"
}

if (-not (Test-Path $NotesFile)) {
    throw "Notes file not found: $NotesFile"
}

$raw = Get-Content -Path $NotesFile -Raw -Encoding UTF8
[System.IO.File]::WriteAllText((Resolve-Path $NotesFile), $raw, [System.Text.UTF8Encoding]::new($false))

gh release edit $Tag --notes-file $NotesFile
