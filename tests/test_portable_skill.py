"""Tests for portable SKILL.md normalization."""
from skillos.skills.portable_skill import (
    build_description,
    finalize_portable_skill,
    normalize_body,
    tool_slug,
)


SAMPLE = """tool_name: contract-review
tool_description: Reviews sales contracts for risk clauses. Use when user uploads a contract.

# 技能名称：合同审核
## 核心问题
自动审核销售合同关键条款。

## S_body
1. 读取合同文件
2. 检查价格条款
3. 输出风险报告

## S_route
| 用户意图 | 执行动作 | 备注 |
| 上传合同 | 步骤1-3 | |

## S_trigger
- keywords: 合同, 审核, contract
- context: 收到销售合同需要审查时
- excludes: 起草新合同

## S_params
- contract_file: file, 必填, 合同文件
"""


def test_tool_slug_from_meta():
    assert tool_slug("合同审核", SAMPLE) == "contract-review"


def test_build_description_third_person():
    desc = build_description("合同审核", SAMPLE)
    assert "Reviews sales contracts" in desc


def test_normalize_body_adds_instructions():
    body = normalize_body("合同审核", SAMPLE)
    assert "## Instructions" in body
    assert "## When to use" in body
    assert "tool_name:" not in body


def test_finalize_portable_skill():
    out = finalize_portable_skill("合同审核", SAMPLE)
    assert out["slug"] == "contract-review"
    assert out["description"]
    assert "Instructions" in out["body"]
    assert "cursor" in out["install_paths"]


def test_finalize_twice_preserves_instructions():
    """Simulate _generate then _persist_created_skill double finalize."""
    first = finalize_portable_skill("合同审核", SAMPLE)
    second = finalize_portable_skill(first["name"], first["body"])
    assert "读取合同文件" in second["body"]
    assert "## Instructions" in second["body"]
    assert "## Decision routes" in second["body"]
    assert len(second["body"]) >= len(first["body"]) * 0.9
