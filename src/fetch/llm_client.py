"""LLM 客户端封装（OpenAI 协议兼容）。

- 用 requests 直接打 /chat/completions，不依赖 openai/anthropic SDK（白名单内）
- 任何外部异常都捕获并返回 None（带日志），不让程序崩
- key/base_url/model 全部从 Settings 注入，便于测试 mock

适配阿里百炼 Coding Plan：
  base_url = https://coding.dashscope.aliyuncs.com/v1
  Authorization: Bearer <DASHSCOPE_API_KEY>
  POST /chat/completions
  body: {"model": "...", "messages": [...]}
"""
from __future__ import annotations

import json
from typing import List, Optional

from src.utils.config import Settings, load_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT_SEC = 60
DEFAULT_TEMPERATURE = 0.3  # 风险分析偏稳，温度低


def chat(
    messages: List[dict],
    settings: Optional[Settings] = None,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> Optional[str]:
    """调 LLM /chat/completions，返回文本内容；失败返回 None。

    入参：
        messages: OpenAI 格式 [{"role":"system|user|assistant","content":"..."}]
        settings: 可选，注入测试用；缺省 load_settings()
        model: 可选覆盖；缺省取 settings.llm_model
        temperature: 采样温度
        timeout_sec: 单次请求超时
    返回：
        模型输出的文本（assistant content），失败返回 None
    异常：
        不抛；缺 key、网络/解析异常一律 log + None
    """
    s = settings if settings is not None else load_settings()
    if not s.llm_api_key or not s.llm_base_url:
        log.error("LLM 未配置（DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL 缺失）")
        return None

    target_model = model or s.llm_model or "qwen-plus"

    try:
        import requests  # 懒导入（白名单内）
    except ImportError as e:
        log.error("requests 未安装：%s", e)
        return None

    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {s.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    except Exception as e:
        log.error("LLM 请求失败 url=%s: %s", url, e)
        return None

    if resp.status_code != 200:
        log.error("LLM 返回非 200: %s, body=%s", resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        return content.strip()
    except Exception as e:
        log.error("LLM 解析返回失败: %s, body=%s", e, resp.text[:300])
        return None
