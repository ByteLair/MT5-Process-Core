#!/bin/bash
# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
# All rights reserved. | Todos os direitos reservados.
# Private License: This code is the exclusive property of Felipe Petracco Carmo.
# Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

# Pre-commit helper script for MT5 Trading DB
# Facilita o uso e gerenciamento dos pre-commit hooks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if venv is activated
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
        echo -e "${BLUE}Activating .venv...${NC}"
        source .venv/bin/activate
    fi
}

# Install pre-commit if not installed
ensure_precommit() {
    if ! command -v pre-commit &> /dev/null; then
        echo -e "${YELLOW}📦 Installing pre-commit...${NC}"
        pip install pre-commit
    fi
}

# Show help
show_help() {
    cat << EOF
${GREEN}🔧 Pre-commit Helper Script${NC}

${BLUE}Usage:${NC}
  ./scripts/precommit-helper.sh [command]

${BLUE}Commands:${NC}
  ${GREEN}install${NC}        - Install pre-commit hooks
  ${GREEN}uninstall${NC}      - Uninstall pre-commit hooks
  ${GREEN}run${NC}            - Run all hooks on staged files
  ${GREEN}run-all${NC}        - Run all hooks on all files
  ${GREEN}update${NC}         - Update hooks to latest versions
  ${GREEN}clean${NC}          - Clean hook cache
  ${GREEN}status${NC}         - Show hooks status
  ${GREEN}fix${NC}            - Run auto-fixable hooks only
  ${GREEN}check${NC}          - Run check-only hooks (mypy, bandit)
  ${GREEN}security${NC}       - Run security checks only
  ${GREEN}format${NC}         - Run formatters only (black, isort, ruff-format)
  ${GREEN}lint${NC}           - Run linters only (ruff, mypy)
  ${GREEN}docker${NC}         - Check Docker files only
  ${GREEN}sql${NC}            - Check SQL files only
  ${GREEN}docs${NC}           - Check documentation files only
  ${GREEN}test${NC}           - Test pre-commit setup
  ${GREEN}help${NC}           - Show this help message

${BLUE}Examples:${NC}
  ${YELLOW}# Install hooks${NC}
  ./scripts/precommit-helper.sh install

  ${YELLOW}# Run all hooks on all files${NC}
  ./scripts/precommit-helper.sh run-all

  ${YELLOW}# Run only formatters${NC}
  ./scripts/precommit-helper.sh format

  ${YELLOW}# Run security checks${NC}
  ./scripts/precommit-helper.sh security

  ${YELLOW}# Update all hooks${NC}
  ./scripts/precommit-helper.sh update

${BLUE}Environment Variables:${NC}
  ${YELLOW}SKIP${NC} - Skip specific hooks (e.g., SKIP=mypy,bandit)

EOF
}

# Install hooks
install_hooks() {
    echo -e "${GREEN}📥 Installing pre-commit hooks...${NC}"
    pre-commit install
    pre-commit install --hook-type commit-msg
    pre-commit install --hook-type pre-push
    echo -e "${GREEN}✅ Pre-commit hooks installed successfully!${NC}"
}

# Uninstall hooks
uninstall_hooks() {
    echo -e "${YELLOW}📤 Uninstalling pre-commit hooks...${NC}"
    pre-commit uninstall
    pre-commit uninstall --hook-type commit-msg
    pre-commit uninstall --hook-type pre-push
    echo -e "${GREEN}✅ Pre-commit hooks uninstalled${NC}"
}

# Run hooks on staged files
run_hooks() {
    echo -e "${BLUE}🔍 Running pre-commit on staged files...${NC}"
    pre-commit run
}

# Run hooks on all files
run_all_hooks() {
    echo -e "${BLUE}🔍 Running pre-commit on all files...${NC}"
    pre-commit run --all-files
}

# Update hooks
update_hooks() {
    echo -e "${BLUE}🔄 Updating pre-commit hooks...${NC}"
    pre-commit autoupdate
    echo -e "${GREEN}✅ Hooks updated!${NC}"
    echo -e "${YELLOW}💡 Run 'pre-commit run --all-files' to test updates${NC}"
}

# Clean cache
clean_cache() {
    echo -e "${BLUE}🧹 Cleaning pre-commit cache...${NC}"
    pre-commit clean
    echo -e "${GREEN}✅ Cache cleaned!${NC}"
}

# Show status
show_status() {
    echo -e "${BLUE}📊 Pre-commit Status:${NC}"
    echo ""

    if pre-commit --version &> /dev/null; then
        echo -e "${GREEN}✅ Pre-commit installed:${NC} $(pre-commit --version)"
    else
        echo -e "${RED}❌ Pre-commit not installed${NC}"
    fi

    echo ""
    echo -e "${BLUE}Installed hooks:${NC}"
    if [ -f .git/hooks/pre-commit ]; then
        echo -e "${GREEN}✅ pre-commit hook${NC}"
    else
        echo -e "${RED}❌ pre-commit hook${NC}"
    fi

    if [ -f .git/hooks/commit-msg ]; then
        echo -e "${GREEN}✅ commit-msg hook${NC}"
    else
        echo -e "${RED}❌ commit-msg hook${NC}"
    fi

    if [ -f .git/hooks/pre-push ]; then
        echo -e "${GREEN}✅ pre-push hook${NC}"
    else
        echo -e "${RED}❌ pre-push hook${NC}"
    fi

    echo ""
    echo -e "${BLUE}Configuration file:${NC}"
    if [ -f .pre-commit-config.yaml ]; then
        echo -e "${GREEN}✅ .pre-commit-config.yaml exists${NC}"
        echo -e "${BLUE}Configured repos:${NC} $(grep -c "repo:" .pre-commit-config.yaml)"
    else
        echo -e "${RED}❌ .pre-commit-config.yaml not found${NC}"
    fi
}

# Run auto-fixable hooks only
run_fixers() {
    echo -e "${BLUE}🔧 Running auto-fixable hooks...${NC}"
    SKIP=mypy,bandit,interrogate,detect-secrets,python-safety-dependencies-check pre-commit run --all-files
}

# Run check-only hooks
run_checkers() {
    echo -e "${BLUE}🔍 Running check-only hooks...${NC}"
    pre-commit run mypy --all-files
    pre-commit run bandit --all-files
    pre-commit run interrogate --all-files
}

# Run security checks
run_security() {
    echo -e "${BLUE}🔒 Running security checks...${NC}"
    pre-commit run bandit --all-files
    pre-commit run detect-secrets --all-files
    pre-commit run python-safety-dependencies-check --all-files
}

# Run formatters
run_formatters() {
    echo -e "${BLUE}✨ Running formatters...${NC}"
    pre-commit run black --all-files
    pre-commit run isort --all-files
    pre-commit run ruff-format --all-files
}

# Run linters
run_linters() {
    echo -e "${BLUE}🔍 Running linters...${NC}"
    pre-commit run ruff --all-files
    pre-commit run mypy --all-files
}

# Check Docker files
check_docker() {
    echo -e "${BLUE}🐳 Checking Docker files...${NC}"
    pre-commit run hadolint-docker --all-files
}

# Check SQL files
check_sql() {
    echo -e "${BLUE}💾 Checking SQL files...${NC}"
    pre-commit run sqlfluff-lint --all-files
    pre-commit run sqlfluff-fix --all-files
}

# Check documentation
check_docs() {
    echo -e "${BLUE}📚 Checking documentation...${NC}"
    pre-commit run markdownlint --all-files
    pre-commit run interrogate --all-files
}

# Test setup
test_setup() {
    echo -e "${BLUE}🧪 Testing pre-commit setup...${NC}"
    echo ""

    # Test configuration file
    echo -e "${YELLOW}1. Testing configuration file...${NC}"
    if pre-commit validate-config; then
        echo -e "${GREEN}✅ Configuration is valid${NC}"
    else
        echo -e "${RED}❌ Configuration has errors${NC}"
        exit 1
    fi
    echo ""

    # Test sample file
    echo -e "${YELLOW}2. Testing with sample Python file...${NC}"
    TMP_FILE=$(mktemp /tmp/test_precommit_XXXXXX.py)
    cat > "$TMP_FILE" << 'PYEOF'
import sys
import os

def test_function(   ):
    """Test function."""
    x=1+2
    print( "Hello World" )
    return x

PYEOF

    if pre-commit run --files "$TMP_FILE"; then
        echo -e "${GREEN}✅ Pre-commit ran successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Pre-commit made changes (this is expected)${NC}"
    fi
    rm -f "$TMP_FILE"
    echo ""

    echo -e "${GREEN}✅ Pre-commit setup is working!${NC}"
}

# Main script
main() {
    check_venv
    ensure_precommit

    case "${1:-help}" in
        install)
            install_hooks
            ;;
        uninstall)
            uninstall_hooks
            ;;
        run)
            run_hooks
            ;;
        run-all)
            run_all_hooks
            ;;
        update)
            update_hooks
            ;;
        clean)
            clean_cache
            ;;
        status)
            show_status
            ;;
        fix)
            run_fixers
            ;;
        check)
            run_checkers
            ;;
        security)
            run_security
            ;;
        format)
            run_formatters
            ;;
        lint)
            run_linters
            ;;
        docker)
            check_docker
            ;;
        sql)
            check_sql
            ;;
        docs)
            check_docs
            ;;
        test)
            test_setup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
