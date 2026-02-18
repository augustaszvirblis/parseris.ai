from typing import Any

from unstract.sdk1.adapters.base1 import register_adapters
from unstract.sdk1.adapters.enums import AdapterTypes
from unstract.sdk1.adapters.llm1.anthropic import AnthropicLLMAdapter
from unstract.sdk1.adapters.llm1.anyscale import AnyscaleLLMAdapter
from unstract.sdk1.adapters.llm1.azure_openai import AzureOpenAILLMAdapter
from unstract.sdk1.adapters.llm1.bedrock import AWSBedrockLLMAdapter
from unstract.sdk1.adapters.llm1.ollama import OllamaLLMAdapter
from unstract.sdk1.adapters.llm1.openai import OpenAILLMAdapter
from unstract.sdk1.adapters.llm1.vertexai import VertexAILLMAdapter

adapters: dict[str, dict[str, Any]] = {}

register_adapters(adapters, AdapterTypes.LLM.name)

# Aliases for adapter_ids used by create_default_adapters / Parseris defaults
# so profiles using "openai|openai" resolve to the OpenAI adapter
_openai_canonical_id = OpenAILLMAdapter.get_id()
if _openai_canonical_id in adapters:
    adapters["openai|openai"] = adapters[_openai_canonical_id]

__all__ = [
    "adapters",
    "AnthropicLLMAdapter",
    "AnyscaleLLMAdapter",
    "AWSBedrockLLMAdapter",
    "AzureOpenAILLMAdapter",
    "OllamaLLMAdapter",
    "OpenAILLMAdapter",
    "VertexAILLMAdapter",
]
