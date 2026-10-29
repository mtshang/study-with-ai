"""LangChain model interface over the existing bounded, private HTTP transport.

Keys and callbacks are instance-private; they are never graph state or model
serialization fields. This adapter is async-only and does not enable tracing,
response caching or retries. Streaming persistence still uses on_text.
"""
from copy import deepcopy
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langsmith import tracing_context
from pydantic import PrivateAttr

from . import model as transport


def from_wire(message):
    role = message['role']
    content = message.get('content') or ''
    if role == 'system':
        return SystemMessage(content=content)
    if role == 'user':
        return HumanMessage(content=content)
    if role == 'tool':
        return ToolMessage(content=content, tool_call_id=message['tool_call_id'])
    if role == 'assistant':
        extra = {}
        if message.get('tool_calls'):
            # Keep raw JSON, including malformed arguments, so existing tool
            # validation can return a matching error rather than lose the call.
            extra['tool_calls'] = deepcopy(message['tool_calls'])
        return AIMessage(content=content, additional_kwargs=extra)
    raise ValueError('Unsupported internal message role')


def to_wire(message):
    if isinstance(message, SystemMessage):
        return {'role': 'system', 'content': message.content}
    if isinstance(message, HumanMessage):
        return {'role': 'user', 'content': message.content}
    if isinstance(message, ToolMessage):
        return {'role': 'tool', 'content': message.content, 'tool_call_id': message.tool_call_id}
    if isinstance(message, AIMessage):
        result = {'role': 'assistant', 'content': message.content or None}
        calls = message.additional_kwargs.get('tool_calls')
        if calls:
            result['tool_calls'] = deepcopy(calls)
        return result
    raise ValueError('Unsupported internal message type')


class TeachingChatModel(BaseChatModel):
    """A request-scoped LangChain model; no global personal configuration."""

    _provider_config: dict = PrivateAttr()
    _tool_schemas: list = PrivateAttr()
    _on_text: Any = PrivateAttr()

    def __init__(self, provider_config, tools, on_text):
        super().__init__(cache=False)
        self._provider_config = dict(provider_config)
        self._tool_schemas = deepcopy(tools)
        self._on_text = on_text

    @property
    def _llm_type(self):
        return 'study-with-ai-bounded-chat'

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError('Use the async model interface')

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        if stop:
            raise ValueError('Transport stop sequences are not supported')
        response = await transport.stream_reply(
            self._provider_config, [to_wire(m) for m in messages],
            self._tool_schemas, self._on_text,
        )
        return ChatResult(generations=[ChatGeneration(message=from_wire(response))])


async def stream_reply(config, messages, tools, on_text):
    chat = TeachingChatModel(config, tools, on_text)
    # A framework install must not silently export student data through a
    # machine-wide LANGSMITH_TRACING setting. No callbacks are inherited here.
    with tracing_context(enabled=False):
        result = await chat.ainvoke([from_wire(m) for m in messages], config={'callbacks': []})
    return to_wire(result)
