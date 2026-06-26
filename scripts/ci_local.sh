#!/bin/bash
# SkillOS CI local runner — replicates GitHub Actions ci.yml pipeline
# Usage: bash scripts/ci_local.sh
# Requires: pip install -e ".[all]" && pip install pytest ruff

set -e
cd "$(dirname "$0")/.."

echo "========================================"
echo "  SkillOS CI Pipeline (local)"
echo "========================================"
echo ""

# Stage 1: Lint (ruff)
echo "=== [1/6] Lint (ruff) ==="
python -m ruff check skillos/ --select E,F --exit-zero
echo ""

# Stage 2: Phase A — core loop
echo "=== [2/6] Phase A — core loop ==="
python -m pytest tests/test_phase_a.py tests/test_production_extraction.py tests/test_moe_evaluation.py tests/test_skill_routing.py tests/test_domain_templates.py -v --tb=short
echo ""

# Stage 3: Knowledge closure verification
echo "=== [3/6] SD knowledge closure verification ==="
python scripts/verify_knowledge_closure.py
echo ""

# Stage 4: Skill bench gates (offline)
echo "=== [4/6] Skill bench gates ==="
python scripts/verify_skill_bench_gates.py
echo ""

# Stage 5: Official SkillsBench unit tests (offline)
echo "=== [5/6] SkillsBench unit tests ==="
python -m pytest tests/test_official_skillsbench.py tests/test_official_bench_api.py tests/test_benchmark_local.py tests/test_skillsbench_cache.py tests/test_workflow064_grader.py tests/test_task_skill_injection.py -v --tb=short
echo ""

# Stage 6: Full test suite + import verification
echo "=== [6/6] Full test suite ==="
python -m pytest tests/ -v --tb=short
echo ""

echo "=== Import verification ==="
python -c "
from skillos.skills.agent import SkillExtractionAgent
from skillos.skills.agent_learning import run_learning_pipeline, diffuse_knowledge, _extract_claims_from_skill
from skillos.skills.resource_capture import classify_resource_type, extract_script, extract_reference, extract_asset
from skillos.skills.portable_skill import to_agent_skills_format, finalize_portable_skill
from skillos.skills.metaskill import parse_metaskill, PipelineStep, MetaSkill, ROLE_TEMPLATES
from skillos.evolution.description_optimizer import optimize_description, generate_eval_queries
from skillos.evolution.skill_tester import run_test_loop, generate_test_cases
from skillos.knowledge.epistemology import get_store, record_claim
from skillos.knowledge.graph import KnowledgeGraph
from skillos.evolution.engine import run_evolution_check
from skillos.skills.dispatcher import dispatch
from skillos.api.skills import router
from skillos.api.skills_extract import router as extract_router
from skillos.api._skills_shared import DispatchRequest, CreateSkillRequest
from skillos.skills.agent_generation import run_skill_generation
from skillos.config import get_config
print('All critical imports OK')
"

echo ""
echo "========================================"
echo "  CI Pipeline Complete"
echo "========================================"
echo "Note: bench regression stage skipped (requires DEEPSEEK_API_KEY)"
echo "Run manually: python scripts/run_bench_regression.py"
