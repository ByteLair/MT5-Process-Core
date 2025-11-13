# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
All rights reserved. | Todos os direitos reservados.
Private License: This code is the exclusive property of Felipe Petracco Carmo.
Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

#!/usr/bin/env bash
# Quick start guide for pre-commit
# Run this to see a visual guide

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║              🔧 PRE-COMMIT QUICK START GUIDE 🔧                    ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

✅ Pre-commit is now ACTIVE in this repository!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 BASIC WORKFLOW

1. Make your changes:
   $ vim api/app/main.py

2. Stage your files:
   $ git add api/app/main.py

3. Commit (hooks run automatically):
   $ git commit -m "feat: add new endpoint"

   → 30+ checks run automatically!
   → Auto-fixes applied when possible
   → You'll see results immediately

4. If hooks fail and make changes:
   $ git add api/app/main.py
   $ git commit -m "feat: add new endpoint"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 USEFUL COMMANDS

Status and Info:
  $ ./scripts/precommit-helper.sh status
  $ ./scripts/precommit-helper.sh help

Run Hooks:
  $ ./scripts/precommit-helper.sh run-all     # All files
  $ ./scripts/precommit-helper.sh format      # Formatters only
  $ ./scripts/precommit-helper.sh security    # Security only
  $ ./scripts/precommit-helper.sh lint        # Linters only

Maintenance:
  $ ./scripts/precommit-helper.sh update      # Update hooks
  $ ./scripts/precommit-helper.sh clean       # Clean cache
  $ ./scripts/precommit-helper.sh test        # Test setup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 WHAT'S BEING CHECKED?

Python:
  • Ruff           → Fast linting
  • Black          → Code formatting
  • isort          → Import sorting
  • mypy           → Type checking
  • interrogate    → Docstring coverage

Security:
  • Bandit         → Python vulnerabilities
  • Detect Secrets → Leaked credentials
  • Safety         → Known CVEs

Infrastructure:
  • Hadolint       → Dockerfile linting
  • ShellCheck     → Shell script linting
  • SQLFluff       → SQL formatting

Documentation:
  • Markdownlint   → Markdown formatting

General:
  • Trailing whitespace, EOL, YAML/JSON syntax
  • Large files, merge conflicts, private keys
  • And 14+ more checks...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION

Full Guide:
  $ cat docs/PRE_COMMIT_GUIDE.md

Quick Reference:
  $ cat PRE_COMMIT_SETUP.md

Detailed Summary:
  $ cat PRECOMMIT_SUMMARY.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 BENEFITS

✨ Code Quality      → Consistent formatting & clean code
🔒 Security          → Early vulnerability detection
🚀 Productivity      → Auto-fixes & instant feedback
📚 Documentation     → Well-documented codebase
🏗️  Infrastructure   → Validated configs & scripts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 PRO TIPS

• Let hooks fix things automatically (Black, isort, ruff)
• Run "format" before committing for quick fixes
• Use "security" before pull requests
• Update hooks monthly with "update"
• Don't skip hooks unless absolutely necessary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 NEED HELP?

In emergency (not recommended):
  $ git commit --no-verify -m "msg"

Hook too slow:
  $ SKIP=mypy,bandit git commit -m "msg"

Hook failing always:
  $ pre-commit clean
  $ pre-commit install --install-hooks

More help:
  $ ./scripts/precommit-helper.sh help
  $ cat docs/PRE_COMMIT_GUIDE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ YOU'RE ALL SET!

Pre-commit will now run automatically on every commit.
Write code, commit, and let the hooks ensure quality! 🚀

For more info: docs/PRE_COMMIT_GUIDE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
