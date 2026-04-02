#!/bin/bash
#
# Example: How to run individual phases of the Spec Coding workflow
#
# This script demonstrates how to use the agent-based workflow
#

set -e

PROJECT_NAME="${1:-MyProject}"
PROJECT_PATH="${2:-./$PROJECT_NAME}"
LANGUAGE="${3:-cpp}"

echo "=========================================="
echo "Spec Coding Workflow - Phase Runner Example"
echo "=========================================="
echo "Project: $PROJECT_NAME"
echo "Path: $PROJECT_PATH"
echo "Language: $LANGUAGE"
echo ""

# Create project directory
mkdir -p "$PROJECT_PATH"
cd "$PROJECT_PATH"

# Initialize context directory
mkdir -p context/requirements context/framework context/tasks
mkdir -p specs/requirements specs/architecture specs/interface
mkdir -p src tests/unit tests/integration

echo "✓ Project structure created"
echo ""

# Example 1: Run Phase 1 (Clarify) directly
echo "=========================================="
echo "Example 1: Running Phase 1 - Clarify"
echo "=========================================="
echo ""
echo "To run this phase manually, use:"
echo ""
echo "Agent agent-1-clarify --input '{"
echo "  \"project_name\": \"$PROJECT_NAME\","
echo "  \"description\": \"A task queue library for C++\","
echo "  \"language\": \"$LANGUAGE\","
echo "  \"project_path\": \"$PROJECT_PATH\","
echo "  \"features\": \"async operations, thread pool, task scheduling\","
echo "  \"constraints\": \"C++17, header-only option, high performance\""
echo "}'"
echo ""

# Example 2: Run full workflow via Orchestrator
echo "=========================================="
echo "Example 2: Running Full Workflow via Orchestrator"
echo "=========================================="
echo ""
echo "To run the complete workflow, use:"
echo ""
echo "Agent spec-coding-orchestrator --input '{"
echo "  \"project_name\": \"$PROJECT_NAME\","
echo "  \"description\": \"A task queue library for C++\","
echo "  \"language\": \"$LANGUAGE\","
echo "  \"project_path\": \"$PROJECT_PATH\","
echo "  \"complexity\": \"simple\","
echo "  \"features\": \"async operations, thread pool\","
echo "  \"constraints\": \"C++17, high performance\""
echo "}'"
echo ""

# Example 3: Resume from a specific phase
echo "=========================================="
echo "Example 3: Resume from Phase 3 (Decompose)"
echo "=========================================="
echo ""
echo "To resume from a specific phase, use:"
echo ""
echo "Agent agent-3-decompose --input '{"
echo "  \"project_name\": \"$PROJECT_NAME\","
echo "  \"project_path\": \"$PROJECT_PATH\","
echo "  \"language\": \"$LANGUAGE\","
echo "  \"context_snapshot\": {"
echo "    \"project\": {"
echo "      \"name\": \"$PROJECT_NAME\","
echo "      \"current_phase\": \"decompose\""
echo "    },"
echo "    \"phases\": {"
echo "      \"clarify\": { \"status\": \"completed\" },"
echo "      \"framework\": { \"status\": \"completed\" }"
echo "    }"
echo "  }"
echo "}'"
echo ""

echo "=========================================="
echo "Directory Structure Created:"
echo "=========================================="
find . -type d | head -20

echo ""
echo "Next steps:"
echo "1. Run Phase 1 (Clarify) to generate requirements"
echo "2. Review context/requirements/clarified.md"
echo "3. Run Phase 2 (Framework) to design architecture"
echo "4. Continue through all 7 phases"
