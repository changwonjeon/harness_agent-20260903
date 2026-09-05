"""
app/agents/main_agent.py — 메인 오케스트레이터 에이전트 (실습 스타터)

교육생은 missions/ 가이드의 안내에 따라 이 파일에 하네스 기능을 순서대로 결합해 나갑니다.
- Mission 02: 자가 복구(Self-Recovery) 미들웨어 & 오케스트레이션 도구 장착
- Mission 03: 5계층 프롬프트 조립기 & 계층형 메모리(Semantic/Episodic) 결합
"""

import os
import json
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent

from app.utils import init_chat_model
from app.utils.context import AgentContext
from app.prompts import SUPERVISOR_SYSTEM_PROMPT

from app.middleware.error_control.self_recovery import (
    ModelFallbackMiddleware,
    ToolErrorHandlerMiddleware,
    ModelCallLimitMiddleware,
)

from app.tools import tools_supervisor

from app.middleware.memory import SemanticMemoryStore, EpisodicStore, MemoryMiddleware
from app.middleware.prompt import (
    PromptAssembler,
    SkillPromptBuilder,
    create_prompt_assembler_middleware,
)

from app.tools.custom_tools import roll_dice, convert_currency
from langchain.agents.middleware import HumanInTheLoopMiddleware

from app.middleware.guardrails import InputSafetyGuardrail, TopicAlignmentGuardrail

from app.middleware.observability import AgentLogTracer


# 1. 에이전트 프로필
AGENT_METADATA = {
    "name": "main_agent",
    "description": "하네스 기능을 연결할 메인 오케스트레이터 에이전트"
}


def _load_config(path: str, default: dict) -> dict:
    """설정 파일을 로드합니다. 실패 시 기본값을 반환합니다."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


async def create_agent_executor():
    # 2. LLM 초기화 (configs/model.config 기반)
    model_cfg = _load_config("./configs/model.config", {
        "model_name": "gemini-3.7-flash",
        "temperature": 0.0,
    })
    llm = init_chat_model(
        model=model_cfg.get("model_name", "gemini-3.7-flash"),
        temperature=model_cfg.get("temperature", 0.0)
    )

    # 3. L1 단기 기억 (SQLite 기반 세션 체크포인터)
    db_dir = "app/database"
    os.makedirs(db_dir, exist_ok=True)
    checkpoints_path = os.path.join(db_dir, "checkpoints.db")

    conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    # 2026-09-04: Mission 03에서 계층형 메모리 결합
    # 4. L3 Semantic Memory Store 초기화 (MEMORY.md / USER.md)
    semantic_store = SemanticMemoryStore(
        memory_dir=db_dir,
        memory_char_limit=4000,
        user_char_limit=2000,
    )
    semantic_store.load_from_disk()

    # 5. L2 Episodic Memory Store 초기화 (과거 세션 대화 + SQLite FTS5 인덱싱)
    episodic_db_dir = "artifacts/memory"
    os.makedirs(episodic_db_dir, exist_ok=True)
    episodic_db_path = os.path.join(episodic_db_dir, "episodic.db")
    episodic_store = EpisodicStore(db_path=episodic_db_path)
    await episodic_store.setup()

    # 6. MemoryMiddleware 구성 (스토어 + memory / session_recall 도구 + 훅)
    memory_mw = MemoryMiddleware(
        semantic_store=semantic_store,
        episodic_store=episodic_store,
        review_llm=llm,
    )
    memory_tools = memory_mw.get_tools()

    # # 4. 미들웨어 파이프라인 (Mission 02에서 Self-Recovery 미들웨어 추가)
    # middleware = [
    #     ModelFallbackMiddleware(
    #         max_retries=3,
    #         fallback_model_name="gemini-2.5-pro"
    #     ),
    #     ToolErrorHandlerMiddleware(max_retries=1), #
    #     ModelCallLimitMiddleware(run_limit=10),
    # ]

    # 5. 도구 바인딩 (Mission 02에서 tools_supervisor 연결)
    # active_tools = tools_supervisor + list(memory_tools) #[]
    active_tools = list(tools_supervisor) + list(memory_tools) + [roll_dice, convert_currency]

    # 8. Claude Code 표준 5-Layer Prompt Assembler 구성
    skill_builder = SkillPromptBuilder(
        skills_dirs=["./skills", "./.agents/skills", "skills", os.path.join(os.getcwd(), "skills")],
        guidelines_path="app/prompts/SKILL.md" if os.path.exists("app/prompts/SKILL.md") else None,
    )

    assembler = PromptAssembler(
        system_rules=SUPERVISOR_SYSTEM_PROMPT,
        tool_schemas=active_tools,
        skill_catalog=skill_builder.assemble,
        l4_docs={},
        agent_rules_path="app/prompts/SKILL.md" if os.path.exists("app/prompts/SKILL.md") else None,
    )
    prompt_mw = create_prompt_assembler_middleware(assembler, merge_system=True)

    # 9. 통합 미들웨어 파이프라인 (순서 중요: Memory -> Prompt -> Self-Recovery)
    backup_model = os.getenv("FALLBACK_MODEL_NAME", "gemini-2.5-flash")
    middleware = [
        memory_mw,
        prompt_mw,
        ModelFallbackMiddleware(
            max_retries=2,
            initial_delay=0.5,
            fallback_model_name=backup_model
        ),
        ToolErrorHandlerMiddleware(max_retries=0),
        ModelCallLimitMiddleware(run_limit=50, exit_behavior="end"),
    ]    

    hitl_cfg = _load_config("./configs/hitl.config", {"hitl_enabled": False})
    if hitl_cfg.get("hitl_enabled"):
        interrupt_on = hitl_cfg.get("interrupt_on", {})
        middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    guardrail_cfg = _load_config("./configs/guardrail.config", {"guardrail_enabled": False})
    if guardrail_cfg.get("guardrail_enabled"):
        guard_model = model_cfg.get("model_name", "gemini-2.5-flash")
        if guardrail_cfg.get("input_safety", {}).get("enabled", True):
            middleware.append(InputSafetyGuardrail(model=guard_model, fail_mode="open"))
        if guardrail_cfg.get("topic_alignment", {}).get("enabled", True):
            blocked = guardrail_cfg.get("topic_alignment", {}).get("blocked_topics")
            middleware.append(TopicAlignmentGuardrail(model=guard_model, blocked_topics=blocked, fail_mode="open"))

    logging_cfg = _load_config("./configs/logging.config", {"logging_enabled": False})
    if logging_cfg.get("logging_enabled"):
        log_dir = logging_cfg.get("log_dir", "./artifacts/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "agent_audit_trail.json")
        middleware.append(AgentLogTracer(log_path=log_path))

    # 6. 하네스로 결합된 최종 메인 에이전트 인스턴스 구축
    main_agent = create_agent(
        model=llm,
        tools=active_tools,
        # system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )

    main_agent.registered_tools = active_tools
    main_agent.checkpointer_conn = conn

    main_agent.episodic_store = episodic_store
    main_agent.semantic_store = semantic_store
    main_agent.assembler = assembler
    main_agent.memory_middleware = memory_mw

    return main_agent
