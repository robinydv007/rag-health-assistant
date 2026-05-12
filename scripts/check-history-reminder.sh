#!/usr/bin/env bash
# After editing files during an active phase, remind to log to history.md

ACTIVE_PHASE_DIR=$(find specs/phases -name "history.md" | head -1 | xargs dirname 2>/dev/null)

if [ -n "$ACTIVE_PHASE_DIR" ]; then
  echo ""
  echo "⚠️  HISTORY REMINDER: Did you append a meaningful entry to ${ACTIVE_PHASE_DIR}/history.md?"
  echo "   Format: ### [TYPE] YYYY-MM-DD — Short title"
  echo "   Types: [DECISION] [SCOPE_CHANGE] [DISCOVERY] [FEATURE] [ARCH_CHANGE] [EVALUATOR] [NOTE]"
  echo ""
fi
