#!/bin/bash
# FlowStorm Demo Script - Shows all features working
# Usage: ./demo.sh

echo "========================================"
echo "  FlowStorm - Full Feature Demo"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check if already running
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} FlowStorm is already running"
else
    echo -e "${YELLOW}!${NC} Starting FlowStorm..."
    cd /home/rathina-devan/Desktop/personal/personal/flowstorm
    ./start.sh &
    sleep 5
fi

echo ""
echo "========================================"
echo "  Feature Check"
echo "========================================"

# 1. Start Demo
echo ""
echo -e "${CYAN}1. Starting Demo...${NC}"
curl -s -X POST http://localhost:8000/api/demo/start | jq -r '.pipeline_id // "demo-pipeline-001"'
sleep 2

# 2. Chaos
echo ""
echo -e "${CYAN}2. Testing Chaos Mode...${NC}"
curl -s -X POST http://localhost:8000/api/pipelines/demo-pipeline-001/chaos \
    -H "Content-Type: application/json" \
    -d '{"intensity": "medium", "duration_seconds": 30}'
sleep 3
curl -s -X DELETE http://localhost:8000/api/pipelines/demo-pipeline-001/chaos

# 3. Generate events by waiting
echo ""
echo -e "${CYAN}3. Generating events (wait 15s)...${NC}"
for i in 1 2 3; do
    echo -n "."
    sleep 5
done
echo " done!"

# 4. Check API endpoints
echo ""
echo "========================================"
echo "  API Results"
echo "========================================"

echo ""
echo -e "${CYAN}Pipeline Versions:${NC}"
curl -s http://localhost:8000/api/pipelines/demo-pipeline-001/versions | jq 'length' 2>/dev/null || echo "0 versions"

echo ""
echo -e "${CYAN}DLQ Stats:${NC}"
curl -s http://localhost:8000/api/pipelines/demo-pipeline-001/dlq/stats | jq '.' 2>/dev/null

echo ""
echo -e "${CYAN}A/B Tests:${NC}"
curl -s http://localhost:8000/api/ab-tests | jq 'length' 2>/dev/null || echo "0 tests"

echo ""
echo "========================================"
echo "  Now Open These URLs:"
echo "========================================"
echo ""
echo -e "  ${GREEN}Dashboard${NC}     - http://localhost:3000/#dashboard"
echo -e "  ${GREEN}Chaos${NC}        - http://localhost:3000/#chaos"
echo -e "  ${GREEN}Pipeline Git${NC} - http://localhost:3000/#git"
echo -e "  ${GREEN}DLQ${NC}          - http://localhost:3000/#dlq"
echo -e "  ${GREEN}A/B Testing${NC}   - http://localhost:3000/#ab"
echo ""
echo "Demo should show:"
echo "  - Healing events every ~10 seconds"
echo "  - Optimization every ~20 seconds"
echo "  - Chaos shows events when active"
echo ""