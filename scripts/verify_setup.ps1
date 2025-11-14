# Verification script for MantaQC setup (PowerShell)

Write-Host "=== MantaQC Verification Script ===" -ForegroundColor Cyan
Write-Host ""

$errors = 0

# Check if Python is available
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "✓ Python found" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found" -ForegroundColor Red
    $errors++
}

# Check if pytest is installed
try {
    python -m pytest --version | Out-Null
    Write-Host "✓ pytest available" -ForegroundColor Green
} catch {
    Write-Host "⚠ pytest not found, installing..." -ForegroundColor Yellow
    pip install pytest pytest-asyncio pytest-cov
}

# Check if alembic is available
if (Get-Command alembic -ErrorAction SilentlyContinue) {
    Write-Host "✓ alembic available" -ForegroundColor Green
} else {
    Write-Host "⚠ alembic not found" -ForegroundColor Yellow
}

# Check .env file
Write-Host ""
Write-Host "=== Configuration Check ===" -ForegroundColor Cyan
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found" -ForegroundColor Yellow
}

# Run tests
Write-Host ""
Write-Host "=== Running Tests ===" -ForegroundColor Cyan

Write-Host "Running unit tests..." -ForegroundColor Yellow
$unitResult = python -m pytest tests/test_analytics_service.py tests/test_report_builder.py tests/test_reset_service.py tests/test_checklist_crud_service.py tests/test_bitrix_alert_service.py -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Unit tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Unit tests failed" -ForegroundColor Red
    $errors++
}

Write-Host "Running integration tests..." -ForegroundColor Yellow
$integrationResult = python -m pytest tests/test_reports_api_integration.py tests/test_dashboards_api_integration.py tests/test_checklists_api_integration.py -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Integration tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Integration tests failed" -ForegroundColor Red
    $errors++
}

Write-Host "Running E2E tests..." -ForegroundColor Yellow
$e2eResult = python -m pytest tests/test_e2e_workflows.py -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ E2E tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ E2E tests failed" -ForegroundColor Red
    $errors++
}

# Check migrations
Write-Host ""
Write-Host "=== Migration Check ===" -ForegroundColor Cyan
if (Get-Command alembic -ErrorAction SilentlyContinue) {
    try {
        alembic current | Out-Null
        Write-Host "✓ Migrations applied" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Could not check migration status" -ForegroundColor Yellow
    }
}

Write-Host ""
if ($errors -eq 0) {
    Write-Host "=== Verification Complete ===" -ForegroundColor Green
    Write-Host "All checks passed successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== Verification Failed ===" -ForegroundColor Red
    Write-Host "$errors error(s) found" -ForegroundColor Red
    exit 1
}

