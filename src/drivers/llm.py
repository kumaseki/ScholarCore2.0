import time
import logging
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.config import GlobalConfig
from src.core.exceptions import LLMError, LLMParseError, ConfigurationError
from src.utils.text_utils import clean_and_parse_json

logger = logging.getLogger("driver.llm")

class DeepSeekDriver:
    def __init__(self):
        self.config = GlobalConfig
        api_key = self.config.get('llm.api_key')
        base_url = self.config.get('llm.base_url')
        
        if not api_key:
            raise ConfigurationError("DeepSeek API Key not found in .env")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = self.config.get('llm.model', 'deepseek-chat')
        # 默认参数
        self.default_temp = self.config.get('llm.temperature', 0.3)
        self.max_tokens = self.config.get('llm.max_tokens', 8000)

    def _log_usage(self, response):
        """记录 Token 消耗，哪怕是粗略的"""
        try:
            usage = response.usage
            logger.info(f"LLM Usage: In={usage.prompt_tokens}, Out={usage.completion_tokens}, Total={usage.total_tokens}")
        except AttributeError:
            logger.warning("LLM response missing usage stats.")

    # 使用 Tenacity 库进行重试 (比手写装饰器更稳健)
    # 重试条件：API错误、限流、超时
    # 策略：最多试 3 次，指数退避 (2s, 4s, 8s...)
    @retry(
        retry=retry_if_exception_type((APIError, RateLimitError, APITimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_api(self, messages, json_mode=False):
        """底层的 API 调用，包裹了重试逻辑"""
        try:
            # ✅ 新增：在请求发出前记录日志 (DEBUG级别，但在调试时很有用)
            # 如果你觉得太吵，可以把级别改成 DEBUG，但现在为了让你安心，我们用 INFO
            logger.info(f"🤖 Requesting DeepSeek... (JSON Mode: {json_mode})")
            
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.default_temp,
                max_tokens=self.max_tokens,
                stream=False,
                response_format={"type": "json_object"} if json_mode else None
            )
            duration = time.time() - start_time
            logger.info(f"✅ DeepSeek Responded in {duration:.2f}s")
            
            self._log_usage(response)
            return response.choices[0].message.content
        except Exception as e:
            # 捕获所有 OpenAI 抛出的异常，包装成我们自己的 LLMError
            # 这样上层逻辑不需要 import openai 就能处理错误
            logger.error(f"DeepSeek API Error: {str(e)}")
            raise LLMError(f"DeepSeek connection failed: {str(e)}") from e

    def chat(self, system_prompt: str, user_content: str) -> str:
        """
        普通对话模式。
        返回：字符串
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        return self._call_api(messages, json_mode=False)

    def chat_json(self, system_prompt: str, user_content: str) -> dict:
        """
        JSON 模式。
        返回：字典 (Dict)
        注意：这里包含了两层重试：
        1. _call_api 负责网络层面的重试。
        2. 这里负责解析失败的重试（手动简单的重试一次，或者直接抛出让上层决定）。
        """
        # 强制在 prompt 里加上 JSON 指令，双重保险
        if "json" not in system_prompt.lower():
            system_prompt += "\n\nIMPORTANT: Output ONLY valid JSON."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # 尝试调用
        raw_content = self._call_api(messages, json_mode=True) # DeepSeek 支持 native json mode

        # 清洗与解析
        try:
            return clean_and_parse_json(raw_content)
        except LLMParseError as e:
            logger.warning(f"JSON parse failed, retrying once... Error: {e}")
            # 简单的再试一次，有时候重试就能解决乱码问题
            # 也可以在这里加入 'Refinement Prompt' 告诉 AI 格式错了，但那是 Phase 3 的事
            time.sleep(1)
            raw_content_retry = self._call_api(messages, json_mode=True)
            return clean_and_parse_json(raw_content_retry)