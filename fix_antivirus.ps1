# Add Windows Defender exclusions for build directories
# Run this script as Administrator before building

Write-Host "Adding Windows Defender exclusions..." -ForegroundColor Cyan
Write-Host ""

$projectDir = $PSScriptRoot

try {
    # Add dist folder
    Add-MpPreference -ExclusionPath "$projectDir\dist" -ErrorAction Stop
    Write-Host "[OK] Added exclusion: $projectDir\dist" -ForegroundColor Green
    
    # Add dist\installer folder
    Add-MpPreference -ExclusionPath "$projectDir\dist\installer" -ErrorAction Stop
    Write-Host "[OK] Added exclusion: $projectDir\dist\installer" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Exclusions added successfully!" -ForegroundColor Green
    Write-Host "You can now run: build_installer.bat" -ForegroundColor Yellow
}
catch {
    Write-Host ""
    Write-Host "Failed to add exclusions automatically." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please add manually:" -ForegroundColor Yellow
    Write-Host "1. Open Windows Security" -ForegroundColor White
    Write-Host "2. Go to 'Virus & threat protection'" -ForegroundColor White
    Write-Host "3. Click 'Manage settings' under Virus & threat protection settings" -ForegroundColor White
    Write-Host "4. Scroll down to 'Exclusions' and click 'Add or remove exclusions'" -ForegroundColor White
    Write-Host "5. Click 'Add an exclusion' > 'Folder'" -ForegroundColor White
    Write-Host "6. Add these folders:" -ForegroundColor White
    Write-Host "   - $projectDir\dist" -ForegroundColor Cyan
    Write-Host "   - $projectDir\dist\installer" -ForegroundColor Cyan
}

Write-Host ""
Read-Host "Press Enter to close"
