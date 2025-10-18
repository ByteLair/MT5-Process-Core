#!/bin/bash
# Auto-commit script - Commits changes automatically with intelligent messages
# Usage: ./auto-commit.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Auto-commit script started${NC}"
echo "Time: $(date)"

# Navigate to project directory
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

echo "Working directory: $PROJECT_DIR"

# Configure git if not already done
git config user.email "autocommit@mt5-trading-db.local" 2>/dev/null || true
git config user.name "AutoCommit Bot" 2>/dev/null || true

# Check for changes
if [[ -z $(git status --porcelain) ]]; then
    echo -e "${YELLOW}✓ No changes detected. Nothing to commit.${NC}"
    exit 0
fi

echo -e "${GREEN}📝 Changes detected!${NC}"

# Get changed files summary
ADDED=$(git status --porcelain | grep "^??" | wc -l)
MODIFIED=$(git status --porcelain | grep "^ M" | wc -l)
DELETED=$(git status --porcelain | grep "^ D" | wc -l)
STAGED=$(git status --porcelain | grep "^M" | wc -l)

# Get list of changed files
CHANGED_FILES=$(git status --porcelain | awk '{print $2}' | head -10)

# Generate intelligent commit message
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
COMMIT_MSG="chore: automated commit - $TIMESTAMP

Auto-generated commit by scheduled task

Changes summary:
- Added: $ADDED file(s)
- Modified: $MODIFIED file(s)
- Deleted: $DELETED file(s)
- Staged: $STAGED file(s)

Modified files:
$(echo "$CHANGED_FILES" | sed 's/^/  - /')

[skip ci]"

echo -e "${GREEN}📋 Commit message:${NC}"
echo "$COMMIT_MSG"
echo ""

# Stage all changes (excluding large files)
git add -A

# Check if there are changes to commit (after staging)
if git diff --cached --quiet; then
    echo -e "${YELLOW}✓ No changes to commit after staging.${NC}"
    exit 0
fi

# Commit changes
git commit -m "$COMMIT_MSG"

echo -e "${GREEN}✅ Commit created successfully!${NC}"

# Push to remote
echo -e "${GREEN}🚀 Pushing to remote...${NC}"
if git push origin main; then
    echo -e "${GREEN}✅ Push successful!${NC}"
else
    echo -e "${RED}❌ Push failed! You may need to pull first.${NC}"
    exit 1
fi

echo -e "${GREEN}✨ Auto-commit completed successfully!${NC}"
