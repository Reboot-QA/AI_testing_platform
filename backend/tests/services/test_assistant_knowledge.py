from app.services.assistant_knowledge import (
    build_assistant_system_prompt,
    build_knowledge_chunks,
    build_knowledge_document,
    find_guide_answer,
    parse_assistant_guides_from_ts,
    rank_chunks_for_question,
)

SAMPLE_GUIDES_TS = """
export const ASSISTANT_GUIDES = [
  {
    text: '如何创建项目',
    permissions: ['projects'],
    answer: `**如何创建项目**\\n\\n1. 打开 Hub。`,
  },
]
"""


def test_parse_assistant_guides_from_ts():
    guides = parse_assistant_guides_from_ts(SAMPLE_GUIDES_TS)
    assert len(guides) == 1
    assert guides[0]["text"] == "如何创建项目"
    assert guides[0]["permissions"] == ["projects"]
    assert "Hub" in guides[0]["answer"]


def test_build_knowledge_document_has_core_sections():
    doc = build_knowledge_document()
    sections = doc["sections"]
    assert "workspace" in sections
    assert "需求点" in sections["workspace"]
    assert "动态" in sections["workspace"]
    assert "测试场景" in sections["workspace"]
    assert len(doc["guides"]) >= 5
    assert any(item["key"] == "projects.create_btn" for item in doc["ui_actions"])


def test_rank_chunks_for_question_prefers_requirements():
    chunks = build_knowledge_chunks(build_knowledge_document())
    ranked = rank_chunks_for_question("如何导入需求点", chunks, limit=3)
    assert ranked
    joined = "\n".join(item["content"] for item in ranked)
    assert "需求" in joined


def test_find_guide_answer_exact_and_fuzzy():
    guides = parse_assistant_guides_from_ts(SAMPLE_GUIDES_TS)
    assert find_guide_answer("如何创建项目", guides) == guides[0]["answer"]
    assert find_guide_answer("请问如何创建项目？", guides) == guides[0]["answer"]


def test_build_assistant_system_prompt_includes_rules_and_context():
    prompt = build_assistant_system_prompt("如何创建需求")
    assert "AI 质量平台" in prompt
    assert "禁止" in prompt
    assert "需求" in prompt
