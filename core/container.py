# core/container.py
import json
import logging
from google import genai
from google.genai import types
from config import settings
from utils.logger import setup_logger

logger = setup_logger("Container")

class Container:
    """
    全能单例容器：管理 Client、模型轮换、全局配置
    """
    _client = None
    _profile_cache = None

    @classmethod
    def get_client(cls):
        """[Singleton] 获取 Gemini Client，全局唯一"""
        if cls._client is None:
            try:
                # 只需要初始化一次，不消耗额度
                cls._client = genai.Client(api_key=settings.GEMINI_KEY)
            except Exception as e:
                logger.critical(f"❌ Client Init Failed: {e}")
                raise e
        return cls._client

    @classmethod
    def load_user_profile(cls, force_refresh=False):
        """[DRY Fix] 统一读取用户画像"""
        if cls._profile_cache and not force_refresh:
            return cls._profile_cache

        profile_path = settings.DATA_DIR / "user_profile.json"
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._profile_cache = json.dumps(data, indent=2, ensure_ascii=False)
                    return cls._profile_cache
            except Exception as e:
                logger.error(f"Profile Read Error: {e}")
                return ""
        return ""

    @classmethod
    def call_brain(cls, contents, tools=None, config=None, tier_index=0):
        """
        🔥 [Core Feature] 自动抗 RPD (Rate Limit) 的调用接口
        大脑 (Agent) 只需要调用这个函数，不需要管底层用的是哪个模型。
        """
        # 1. 递归终止条件
        if tier_index >= len(settings.MODEL_TIERS):
            logger.critical("💀 All Model Tiers Exhausted. System Offline.")
            return "⚠️ [SYSTEM CRITICAL] Google API Quota Depleted. All models unavailable."

        # 2. 选模型 (从 settings.MODEL_TIERS 读取)
        current_model = settings.MODEL_TIERS[tier_index]
        client = cls.get_client()

        # 3. 默认配置兜底
        if config is None:
            config = types.GenerateContentConfig(temperature=0.3)
        
        # 🔥 [Safety Patch] 强制关闭安全过滤器，防止误杀导致 (No output)
        # 私人管家不需要过度敏感的过滤器
        if not config.safety_settings:
            config.safety_settings = [
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")
            ]
        
        # 强制把 tools 塞进 config (如果提供了)
        if tools:
            config.tools = tools

        try:
            # logger.info(f"🧠 Linking to Cortex: {current_model} (Tier {tier_index})")
            
            response = client.models.generate_content(
                model=current_model,
                contents=contents,
                config=config
            )
            return response

        except Exception as e:
            error_str = str(e)
            # 4. 捕获 429 (配额超限) 或 503 (服务器过载)
            if "429" in error_str or "503" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.warning(f"📉 Model {current_model} Failed ({error_str[:30]}...). Switching to Tier {tier_index + 1}...")
                return cls.call_brain(contents, tools, config, tier_index + 1)
            else:
                # 其他错误 (如 Prompt 内容违规) 直接抛出
                logger.error(f"❌ Fatal Logic Error: {e}")
                raise e