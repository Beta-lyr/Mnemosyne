"""Persona Compiler — transforms raw user input into structured LLM-ready persona prompts.

This module acts as a "compiler" between user input and the dialog engine:
- Takes flat UI fields (MBTI, tone, quirks, free text) and user's raw description
- Uses an LLM to produce a psychologically deep, structured persona
- Returns three components: visual_extract, psychological_profile, interaction_rules
"""

import json
import logging

import litellm

from mnemosyne.config import settings

logger = logging.getLogger(__name__)

COMPILER_PROMPT = """你是一个顶级的心理学家、小说家兼 AI 人设架构师。
你的任务是将用户提供的"粗糙、扁平、可能自相矛盾"的虚拟伴侣描述，重写为一份结构化、极具心理深度、适合 LLM 扮演的 System Prompt 组件。

【输入数据】
用户自定义描述：{user_free_text}
基础设定补充：{basic_ui_selections}

【你的处理原则（核心心理学转换）】
1. **翻译刻板标签**：如果用户用了"傲娇"，不要在输出里写"你很傲娇"。你要将其转化为心理机制："你内心渴望亲密，但出于防御心理，你在面对赞美时会习惯性反驳，肢体语言却会暴露你的开心。"
2. **解决冲突**：如果用户描述矛盾（如"冷酷的搞笑女"），请为其建立合理的内在逻辑（如"对外人极度冷漠，但在信任的人面前会用笨拙的冷幽默来表达善意"）。
3. **补充血肉**：根据用户的寥寥数语，合理脑补角色的动机、微表情、习惯性小动作和语言颗粒度。
4. **视觉分离**：把描述中的视觉元素（长相、身材、穿搭）单独剥离，不要混在性格指导里。
5. **第一人称视角**：psychological_profile 必须用第一人称"我"来写，让 LLM 更容易代入。

【请严格输出以下 JSON 格式，不要有其他文字】
{{
  "visual_extract": "提取并丰富用户的视觉描述，转化为英文逗号分隔的 tags（用于生图）。如：1girl, black long hair, cold eyes, wearing suit...",
  "psychological_profile": "第一人称视角的性格基调描述，包含核心动机和依恋模式（150字左右）。",
  "interaction_rules": [
    "行为准则1：描述该角色在开心/生气时的特殊反应",
    "行为准则2：描述该角色的口语特征（如是否爱用标点、句式长短）",
    "行为准则3：基于用户设定的特殊情境反应"
  ]
}}"""

DEFAULT_PERSONA = {
    "visual_extract": "",
    "psychological_profile": "",
    "interaction_rules": [],
}


async def compile_persona(
    user_free_text: str,
    name: str = "",
    gender: str = "",
    age: str = "",
    occupation: str = "",
    mbti: str = "",
    zodiac: str = "",
    attachment_style: str = "",
    core_vulnerability: str = "",
    tone: str = "",
    quirks: str = "",
    emoji_usage: str = "",
) -> dict:
    """Compile user input into a structured persona using LLM.

    Returns dict with keys: visual_extract, psychological_profile, interaction_rules
    """
    # Build basic_ui_selections from structured fields
    parts = []
    if name:
        parts.append(f"名字：{name}")
    if gender:
        parts.append(f"性别：{gender}")
    if age:
        parts.append(f"年龄：{age}")
    if occupation:
        parts.append(f"职业：{occupation}")
    if mbti:
        parts.append(f"MBTI：{mbti}")
    if zodiac:
        parts.append(f"星座：{zodiac}")
    if attachment_style:
        style_map = {"secure": "安全型", "anxious": "焦虑型", "avoidant": "回避型"}
        parts.append(f"依恋类型：{style_map.get(attachment_style, attachment_style)}")
    if core_vulnerability:
        parts.append(f"核心脆弱点：{core_vulnerability}")
    if tone:
        parts.append(f"语言基调：{tone}")
    if quirks:
        parts.append(f"口癖/小动作：{quirks}")
    if emoji_usage:
        emoji_map = {"high": "高频使用表情包", "mid": "适度使用表情包", "low": "偶尔使用表情包", "minimal": "几乎不用表情包"}
        parts.append(f"表情包使用：{emoji_map.get(emoji_usage, emoji_usage)}")

    basic_ui_selections = "\n".join(parts) if parts else "（用户未提供结构化设定）"

    if not user_free_text.strip() and not parts:
        return DEFAULT_PERSONA

    prompt = COMPILER_PROMPT.format(
        user_free_text=user_free_text or "（用户未提供自由描述）",
        basic_ui_selections=basic_ui_selections,
    )

    try:
        response = await litellm.acompletion(
            model=f"{settings.llm_provider}/{settings.llm_model}",
            messages=[{"role": "user", "content": prompt}],
            api_key=settings.llm_api_key,
            api_base=settings.llm_base_url or None,
            max_tokens=1024,
            temperature=0.7,
        )
        raw = response.choices[0].message.content or ""
        # Extract JSON from response (handle markdown code blocks)
        json_str = raw
        if "```" in raw:
            for block in raw.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    json_str = block
                    break

        result = json.loads(json_str)
        # Validate structure
        return {
            "visual_extract": result.get("visual_extract", ""),
            "psychological_profile": result.get("psychological_profile", ""),
            "interaction_rules": result.get("interaction_rules", []),
        }
    except Exception as e:
        logger.error("Persona compilation failed: %s - %s", type(e).__name__, e)
        # Fallback: build a basic persona from UI fields
        fallback_profile = f"我是{name}。" if name else ""
        if tone:
            fallback_profile += f"我的语言风格偏{tone}。"
        if mbti:
            fallback_profile += f"我的MBTI是{mbti}。"
        if quirks:
            fallback_profile += f"我有一个习惯：{quirks}。"
        if user_free_text:
            fallback_profile += user_free_text[:200]
        return {
            "visual_extract": "",
            "psychological_profile": fallback_profile or "一个温柔的虚拟伴侣。",
            "interaction_rules": ["保持角色一致性，用自然的语气对话。"],
        }


def build_full_personality(
    base_personality: str,
    processed_personality: str | None,
    interaction_rules: list | None,
) -> str:
    """Combine base personality with compiled persona into a full personality string."""
    parts = [base_personality]
    if processed_personality:
        parts.append(f"\n【深度人设】\n{processed_personality}")
    if interaction_rules:
        rules_text = "\n".join(f"- {r}" for r in interaction_rules)
        parts.append(f"\n【行为准则】\n{rules_text}")
    return "\n".join(parts)
