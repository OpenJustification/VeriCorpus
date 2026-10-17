# SPDX-License-Identifier: AGPL-3.0-or-later
# Used for the Verified Windows bundle only. Tesseract is an independent OCR witness.
# Install via Chocolatey on GitHub's Windows runner and copy binaries+traineddata.
$ErrorActionPreference = 'Stop'
$target = Join-Path $PWD 'dist\VeriCorpus\Tesseract-OCR'
$source = 'C:\Program Files\Tesseract-OCR'
if (-not (Test-Path (Join-Path $source 'tesseract.exe'))) {
  if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    throw 'Chocolatey unavailable: cannot prepare standalone Verified bundle.'
  }
  choco install tesseract --yes --no-progress
  if ($LASTEXITCODE -ne 0) { throw "Tesseract installation failed ($LASTEXITCODE)" }
}
if (-not (Test-Path (Join-Path $source 'tesseract.exe'))) { throw 'Tesseract missing after installation' }
if (-not (Test-Path (Join-Path $source 'tessdata\eng.traineddata'))) {
  throw 'English Tesseract traineddata missing; refusing incomplete Verified artifact.'
}
if (Test-Path $target) { Remove-Item $target -Recurse -Force }
Copy-Item -Path $source -Destination $target -Recurse -Force
& (Join-Path $target 'tesseract.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Bundled Tesseract executable fails to start' }
# Package Tesseract's existing license files if the installer supplies them.
$licenseFiles = @(Get-ChildItem $target -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '(?i)^(LICENSE|COPYING|NOTICE|AUTHORS)([.].*)?$' })
if ($licenseFiles.Count -eq 0) {
  throw 'Tesseract distribution has no discoverable license notice; review before distribution.'
}
Write-Host ('Bundled Tesseract at ' + $target)
