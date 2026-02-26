#!/bin/bash

# ========================================================
# TECHNICAL VALIDATION SCRIPT - PHASE 4 PRE-FLIGHT CHECK
# ========================================================
# Purpose: Automated validation of all prerequisites
# Usage: bash technical_validation.sh
# Output: validation_report.txt
# Date: 26/02/2026
# ========================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Report file
REPORT_FILE="technical_validation_report.txt"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Initialize report
echo "========================================================" > $REPORT_FILE
echo "TECHNICAL VALIDATION REPORT - PHASE 4" >> $REPORT_FILE
echo "========================================================" >> $REPORT_FILE
echo "Timestamp: $TIMESTAMP" >> $REPORT_FILE
echo "System: $(uname -a)" >> $REPORT_FILE
echo "========================================================" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Function to log results
log_result() {
    local check_name=$1
    local status=$2
    local details=$3
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $check_name: $status"
        echo "✓ $check_name: $status - $details" >> $REPORT_FILE
    else
        echo -e "${RED}✗${NC} $check_name: $status"
        echo "✗ $check_name: $status - $details" >> $REPORT_FILE
    fi
}

echo -e "${BLUE}=== PHASE 4 TECHNICAL VALIDATION ===${NC}"
echo "" >> $REPORT_FILE
echo "=== PHASE 4 TECHNICAL VALIDATION ===" >> $REPORT_FILE

# ========================================================
# 1. SYSTEM REQUIREMENTS
# ========================================================
echo -e "${BLUE}[1/6] SYSTEM REQUIREMENTS${NC}"
echo "" >> $REPORT_FILE
echo "--- SYSTEM REQUIREMENTS ---" >> $REPORT_FILE

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE=$(uname -s)
    log_result "Operating System" "PASS" "$OS_TYPE (Linux/Mac compatible)"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS_TYPE="Windows (WSL or compatibility layer required)"
    log_result "Operating System" "WARN" "$OS_TYPE"
else
    log_result "Operating System" "FAIL" "Unknown OS: $OSTYPE"
fi

# Check disk space (need at least 5GB)
disk_available=$(df / | awk 'NR==2 {print $4}')
if [ "$disk_available" -gt 5242880 ]; then
    log_result "Disk Space" "PASS" "${disk_available}K available (≥5GB)"
else
    log_result "Disk Space" "FAIL" "${disk_available}K available (need ≥5GB)"
fi

# Check RAM (need at least 4GB)
if command -v free &> /dev/null; then
    ram_available=$(free -m | awk 'NR==2 {print $7}')
    if [ "$ram_available" -gt 2048 ]; then
        log_result "RAM Available" "PASS" "${ram_available}MB available (≥2GB)"
    else
        log_result "RAM Available" "WARN" "${ram_available}MB available (recommend ≥4GB)"
    fi
fi

# ========================================================
# 2. GIT CONFIGURATION
# ========================================================
echo ""
echo -e "${BLUE}[2/6] GIT CONFIGURATION${NC}"
echo "" >> $REPORT_FILE
echo "--- GIT CONFIGURATION ---" >> $REPORT_FILE

if command -v git &> /dev/null; then
    git_version=$(git --version)
    log_result "Git Installation" "PASS" "$git_version"
else
    log_result "Git Installation" "FAIL" "Git not found. Install: https://git-scm.com/"
fi

if git config --get user.name > /dev/null 2>&1; then
    git_user=$(git config --get user.name)
    log_result "Git User Config" "PASS" "User: $git_user"
else
    log_result "Git User Config" "FAIL" "Run: git config --global user.name 'Your Name'"
fi

if git config --get user.email > /dev/null 2>&1; then
    git_email=$(git config --get user.email)
    log_result "Git Email Config" "PASS" "Email: $git_email"
else
    log_result "Git Email Config" "FAIL" "Run: git config --global user.email 'your@email.com'"
fi

# Check SSH key
if [ -f ~/.ssh/id_rsa ]; then
    log_result "SSH Key" "PASS" "Private key found (~/.ssh/id_rsa)"
else
    log_result "SSH Key" "WARN" "SSH key not found. May be needed for repo push"
fi

# Check current branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" = "main" ]; then
    log_result "Git Branch" "PASS" "On 'main' branch"
else
    log_result "Git Branch" "WARN" "On '$current_branch' branch (expected: main)"
fi

# Check git status
if git status > /dev/null 2>&1; then
    status=$(git status --porcelain | wc -l)
    if [ "$status" -eq 0 ]; then
        log_result "Git Status" "PASS" "Working directory clean"
    else
        log_result "Git Status" "WARN" "$status files with changes (commit before deployment)"
    fi
fi

# ========================================================
# 3. AZURE CLI
# ========================================================
echo ""
echo -e "${BLUE}[3/6] AZURE CLI${NC}"
echo "" >> $REPORT_FILE
echo "--- AZURE CLI ---" >> $REPORT_FILE

if command -v az &> /dev/null; then
    az_version=$(az --version | head -1)
    log_result "Azure CLI Installation" "PASS" "$az_version"
else
    log_result "Azure CLI Installation" "FAIL" "Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
fi

# Check Azure login
if az account show > /dev/null 2>&1; then
    account=$(az account show --query name -o tsv)
    log_result "Azure Authentication" "PASS" "Authenticated to: $account"
else
    log_result "Azure Authentication" "FAIL" "Not authenticated. Run: az login"
fi

# Check Bicep CLI
if command -v bicep &> /dev/null; then
    bicep_version=$(bicep --version)
    log_result "Bicep CLI" "PASS" "$bicep_version"
else
    log_result "Bicep CLI" "WARN" "Bicep not found. Install: az bicep install"
fi

# Test Bicep syntax
if [ -f "infrastructure/staging.bicep" ]; then
    if az bicep build --file infrastructure/staging.bicep > /dev/null 2>&1; then
        log_result "Bicep Syntax Validation" "PASS" "infrastructure/staging.bicep is valid"
    else
        log_result "Bicep Syntax Validation" "FAIL" "Bicep syntax errors found"
    fi
else
    log_result "Bicep File" "FAIL" "infrastructure/staging.bicep not found"
fi

# ========================================================
# 4. PYTHON & DEPENDENCIES
# ========================================================
echo ""
echo -e "${BLUE}[4/6] PYTHON & DEPENDENCIES${NC}"
echo "" >> $REPORT_FILE
echo "--- PYTHON & DEPENDENCIES ---" >> $REPORT_FILE

if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    log_result "Python Installation" "PASS" "$python_version"
else
    log_result "Python Installation" "FAIL" "Python 3 not found"
fi

# Check pip
if command -v pip3 &> /dev/null; then
    log_result "Pip Installation" "PASS" "Pip3 found"
else
    log_result "Pip Installation" "FAIL" "Pip3 not found"
fi

# Check requirements.txt
if [ -f "requirements.txt" ]; then
    log_result "Requirements.txt" "PASS" "Found"
    # Try dry-run install
    if pip3 install --dry-run -q -r requirements.txt > /dev/null 2>&1; then
        log_result "Pip Dependencies" "PASS" "All dependencies available"
    else
        log_result "Pip Dependencies" "WARN" "Some dependencies may be missing (will install during deployment)"
    fi
else
    log_result "Requirements.txt" "FAIL" "requirements.txt not found"
fi

# Check for specific packages needed
packages=("pytest" "locust" "scikit-learn" "xgboost")
for pkg in "${packages[@]}"; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
        log_result "Package: $pkg" "PASS" "Installed"
    else
        log_result "Package: $pkg" "WARN" "Not installed (will install if needed)"
    fi
done

# ========================================================
# 5. DOCKER (if used)
# ========================================================
echo ""
echo -e "${BLUE}[5/6] DOCKER (Optional)${NC}"
echo "" >> $REPORT_FILE
echo "--- DOCKER (Optional) ---" >> $REPORT_FILE

if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    log_result "Docker Installation" "PASS" "$docker_version"
    
    # Check if docker daemon running
    if docker ps > /dev/null 2>&1; then
        log_result "Docker Daemon" "PASS" "Docker daemon is running"
    else
        log_result "Docker Daemon" "WARN" "Docker daemon not running"
    fi
else
    log_result "Docker Installation" "WARN" "Docker not found (optional, only if using containers)"
fi

# ========================================================
# 6. PROJECT STRUCTURE
# ========================================================
echo ""
echo -e "${BLUE}[6/6] PROJECT STRUCTURE${NC}"
echo "" >> $REPORT_FILE
echo "--- PROJECT STRUCTURE ---" >> $REPORT_FILE

# Check critical directories
directories=(
    "docs/agente_autonomo"
    "infrastructure"
    "tests"
    "models"
    "scripts"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        log_result "Directory: $dir" "PASS" "Found"
    else
        log_result "Directory: $dir" "WARN" "Not found (may be created during deployment)"
    fi
done

# Check critical files
files=(
    "README.md"
    "requirements.txt"
    "docs/agente_autonomo/PHASE4_KICKOFF_MEETING.md"
    "docs/agente_autonomo/PHASE4_FIRST_WEEK_ACTIONS.md"
    "infrastructure/staging.bicep"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        log_result "File: $file" "PASS" "Found"
    else
        log_result "File: $file" "WARN" "Not found"
    fi
done

# ========================================================
# SUMMARY
# ========================================================
echo ""
echo -e "${BLUE}=== VALIDATION COMPLETE ===${NC}"
echo "" >> $REPORT_FILE
echo "=== VALIDATION SUMMARY ===" >> $REPORT_FILE

# Count results
pass_count=$(grep -c "✓" $REPORT_FILE || true)
fail_count=$(grep -c "✗" $REPORT_FILE || true)
warn_count=$(grep -c "WARN" $REPORT_FILE || true)

echo "" >> $REPORT_FILE
echo "Results:" >> $REPORT_FILE
echo "  Passed: $pass_count" >> $REPORT_FILE
echo "  Failed: $fail_count" >> $REPORT_FILE
echo "  Warnings: $warn_count" >> $REPORT_FILE
echo "" >> $REPORT_FILE

if [ "$fail_count" -eq 0 ]; then
    echo -e "${GREEN}✓ VALIDATION PASSED${NC}"
    echo "✓ VALIDATION PASSED - Ready for Phase 4 kick-off" >> $REPORT_FILE
    exit_code=0
else
    echo -e "${RED}✗ VALIDATION FAILED${NC} ($fail_count critical issues)"
    echo "✗ VALIDATION FAILED - Fix critical issues before kick-off" >> $REPORT_FILE
    exit_code=1
fi

if [ "$warn_count" -gt 0 ]; then
    echo -e "${YELLOW}⚠ $warn_count warnings found${NC} (review ASAP)"
    echo "⚠ $warn_count warnings found (review ASAP)" >> $REPORT_FILE
fi

echo ""
echo "Report saved to: $REPORT_FILE"
echo "Report saved: $REPORT_FILE" >> $REPORT_FILE
echo "" >> $REPORT_FILE
echo "Next Steps:" >> $REPORT_FILE
echo "1. Review $REPORT_FILE" >> $REPORT_FILE
echo "2. Fix any critical issues (exit_code != 0)" >> $REPORT_FILE
echo "3. For warnings, consult #phase4-blockers Slack" >> $REPORT_FILE
echo "4. Confirm readiness by 28/02 EOD" >> $REPORT_FILE

echo ""
echo "Edit: $REPORT_FILE"
echo "Questions? #phase4-blockers"

exit $exit_code
