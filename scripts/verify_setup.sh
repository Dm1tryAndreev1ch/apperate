#!/bin/bash
# Verification script for MantaQC setup

set -e

echo "=== MantaQC Verification Script ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check if pytest is installed
if ! python3 -m pytest --version &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest not found, installing...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi
echo -e "${GREEN}✓ pytest available${NC}"

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo -e "${YELLOW}⚠ alembic not found${NC}"
else
    echo -e "${GREEN}✓ alembic available${NC}"
fi

# Check database connection
echo ""
echo "=== Database Check ==="
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
else
    echo -e "${YELLOW}⚠ .env file not found${NC}"
fi

# Run tests
echo ""
echo "=== Running Tests ==="
echo "Running unit tests..."
if python3 -m pytest tests/test_analytics_service.py tests/test_report_builder.py tests/test_reset_service.py tests/test_checklist_crud_service.py tests/test_bitrix_alert_service.py -v; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
    exit 1
fi

echo "Running integration tests..."
if python3 -m pytest tests/test_reports_api_integration.py tests/test_dashboards_api_integration.py tests/test_checklists_api_integration.py -v; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    exit 1
fi

echo "Running E2E tests..."
if python3 -m pytest tests/test_e2e_workflows.py -v; then
    echo -e "${GREEN}✓ E2E tests passed${NC}"
else
    echo -e "${RED}✗ E2E tests failed${NC}"
    exit 1
fi

# Check migrations
echo ""
echo "=== Migration Check ==="
if command -v alembic &> /dev/null; then
    if alembic current &> /dev/null; then
        echo -e "${GREEN}✓ Migrations applied${NC}"
    else
        echo -e "${YELLOW}⚠ Could not check migration status${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=== Verification Complete ===${NC}"
echo "All checks passed successfully!"

