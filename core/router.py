# core/router.py
import json
from google import genai
from google.genai import types
from config import settings
from utils.logger import setup_logger
from core.state import StateManager

logger = setup_logger("NeuralRouter")
client = genai.Client(api_key=settings.GEMINI_KEY)

class NeuralRouter:
    def __init__(self):
        self.state_manager = StateManager()

    def _load_profile(self):
        """让小脑也能读取你的人设，否则它不知道你是 UCL 的"""
        profile_path = settings.DATA_DIR / "user_profile.json"
        try:
            if profile_path.exists():
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.dumps(json.load(f), indent=2, ensure_ascii=False)
        except Exception:
            return ""
        return ""

    def route_and_execute(self, user_text: str):
        current_state = self.state_manager.get_state()
        energy = current_state["user_physio"]["energy_level"]
        mode = current_state["strategic_mode"]["current_focus"]
        profile = self._load_profile() # 🔥 注入灵魂

        # 🔥 暴力调教 Prompt
        router_prompt = f"""
        [ROLE]
        You are the 'Subconscious' of Jarvis.
        Master Profile: {profile}
        Current State: Energy={energy}, Mode={mode}
        
        [INPUT]
        "{user_text}"
        
        [TASK]
        Classify input and react.
        
        OPTION A: CASUAL / VIBE CHECK
        - Triggers: Greetings, "tired", "boring", short emotions.
        - ACTION: Reply directly.
        - TONE: **ENTP, Cynical, Sharp.** - RULE: NO "How can I help". NO "Hope your day is good". NO cringy puns.
        - CONTENT: Reference his UCL/KCL background or ADHD if relevant. Be a smartass.
        - FORMAT: Pure text, Chinese (or English if context fits), <30 words.
        
        OPTION B: FUNCTIONAL / COMPLEX
        - Triggers: Calendar, Tasks, Analysis, Long questions.
        - ACTION: Output exactly: "[[HANDOFF_TO_CORTEX]]"
        """

        try:
            response = client.models.generate_content(
                model=settings.ROUTER_MODEL,
                contents=router_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8, # 让它更野一点
                    max_output_tokens=100
                )
            )
            
            result = response.text.strip()
            
            if "[[HANDOFF_TO_CORTEX]]" in result:
                logger.info("🚦 Intent: COMPLEX -> Routing to Cortex")
                return None 
            else:
                logger.info("🟢 Intent: CHAT -> Handled by Router")
                return result 

        except Exception as e:
            logger.error(f"Router Error: {e}")
            return None