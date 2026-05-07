"""LLM callable tools for the dialog agent."""

from langchain_core.tools import tool


@tool
async def generate_image(scene_prompt: str) -> str:
    """Generate an image of the character in a given scene.
    Use this when the user asks for a photo, selfie, or when a visual scene would enhance the conversation.
    The scene_prompt should be a concise English description of the scene (e.g. 'sitting in a cafe, wearing a red dress, smiling').
    """
    # This is a marker tool - actual image generation happens in the agent core
    return f"[IMAGE_GENERATION_REQUESTED]{scene_prompt}"


@tool
async def save_memory(content: str, memory_type: str = "fact") -> str:
    """Save an important piece of information to long-term memory.
    memory_type can be: 'fact' (user preference/info), 'feeling' (emotional state), 'event' (future plan).
    """
    return f"[MEMORY_SAVED]{memory_type}:{content}"


@tool
async def schedule_message(delay_minutes: int, message: str) -> str:
    """Schedule a message to be sent after a delay.
    Use this when the user asks you to remind them of something, send a message later, or set a timer.
    delay_minutes: how many minutes to wait before sending (minimum 1)
    message: the message content to send
    """
    import json
    delay = max(1, int(delay_minutes))
    return f"[SCHEDULE_MESSAGE]{json.dumps({'delay': delay, 'message': message}, ensure_ascii=False)}"


TOOLS = [generate_image, save_memory, schedule_message]
