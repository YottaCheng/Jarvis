# core/router.py
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.state import StateManager
from core.container import Container
from services.google_ops import fetch_raw_events
from utils.formatter import format_calendar_events
from core.prompts import ROUTER_SYSTEM_PROMPT
from core.memory import load_history  # 🔥 [NEW] 引入记忆

logger = setup_logger("NeuralRouter")

class NeuralRouter:
    def __init__(self):
        self.state_manager = StateManager()

    def route_and_execute(self, user_text: str):
        # 1. 获取状态
        current_state = self.state_manager.get_state()
        energy = current_state["user_physio"]["energy_level"]
        mode = current_state["strategic_mode"]["current_focus"]
        
        # 2. 获取 Profile
        profile = Container.load_user_profile()

        # 3. 获取静态日程
        raw_events = fetch_raw_events(hours=24)
        schedule_summary = format_calendar_events(raw_events)

        # 4. 🔥 [NEW] 获取短期对话历史 (关键修复)
        # 只取最近 3 条，既省 Token 又能补全上下文
        # 这样 Gemma 就能看到你上一句说了 "ADHD量表"
        chat_history = load_history(settings.OWNER_ID, limit=3)

        # 5. 填充 Prompt
        router_prompt = ROUTER_SYSTEM_PROMPT.format(
            schedule_summary=schedule_summary,
            energy=energy,
            mode=mode,
            profile=profile,
            chat_history=chat_history, # 注入历史
            user_text=user_text
        )

        try:
            # 6. 调用模型 (保持使用低功耗的 Router Model)
            client = Container.get_client()
            
            # 使用 settings.ROUTER_MODEL (Gemma 3 27B)
            # 它足够聪明，只要给它上下文
            response = client.models.generate_content(
                model=settings.ROUTER_MODEL, 
                contents=router_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, # 🔥 降温：让它更理性，别瞎聊
                    max_output_tokens=100
                )
            )
            
            result = response.text.strip()
            
            # 7. 决策分流
            if "[[HANDOFF_TO_CORTEX]]" in result:
                logger.info("🚦 Intent: SERVICE -> Routing to Cortex")
                return None  # 让 Agent 接手
            else:
                logger.info("🟢 Intent: CONVERSATION -> The Butler replies")
                return result 

        except Exception as e:
            logger.error(f"Router Malfunction: {e}")
            # 出错默认转人工(大脑)
            return None