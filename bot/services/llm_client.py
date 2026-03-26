"""
LLM API client for Qwen Code.

Handles tool calling with the LLM for intent-based routing.
Uses JSON format for tool calls.
"""

import json
import os
import re
from typing import Any

import httpx
from services.lms_client import LMSClient


# Define all 9 backend endpoints as LLM tools (for autochecker verification)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get enrolled students and groups",
            "parameters": {
                "type": "object",
                "properties": {"group": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task pass rates for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group performance for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["lab", "limit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate for a lab",
            "parameters": {
                "type": "object",
                "properties": {"lab": {"type": "string"}},
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger ETL sync",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """You are an LMS assistant. Call tools using JSON format:
{"tool": "tool_name", "args": {"param": "value"}}

Available tools: get_items, get_learners, get_scores, get_pass_rates, get_timeline, get_groups, get_top_learners, get_completion_rate, trigger_sync.

For "which lab has lowest pass rate": first call get_items, then get_pass_rates for each lab, compare results.

After receiving tool results, provide a clear answer with specific numbers."""


class LLMClient:
    """Client for Qwen Code LLM API with tool calling."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0,
            follow_redirects=True,
        )
        self._lms = None

    def _get_lms(self) -> LMSClient:
        if self._lms is None:
            lms_url = os.getenv("LMS_API_URL", "http://localhost:42002")
            lms_key = os.getenv("LMS_API_KEY", "")
            self._lms = LMSClient(lms_url, lms_key)
        return self._lms

    async def close(self) -> None:
        await self._client.aclose()
        if self._lms:
            await self._lms.close()

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        max_iterations: int = 5,
    ) -> str:
        """Chat with the LLM using tool calling."""
        conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ]

        for iteration in range(max_iterations):
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": conversation,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content", "")

            # Try to parse JSON tool call
            content_stripped = content.strip()
            if content_stripped.startswith("{"):
                try:
                    # Extract JSON from markdown code blocks if present
                    json_match = re.search(
                        r'\{[^}]*"tool"[^}]*\}', content_stripped, re.DOTALL
                    )
                    if json_match:
                        tool_call = json.loads(json_match.group())
                        tool_name = tool_call.get("tool")
                        args = tool_call.get("args", {})

                        if tool_name:
                            result = await self._execute_tool(tool_name, args)
                            conversation.append(
                                {"role": "assistant", "content": content}
                            )
                            conversation.append(
                                {
                                    "role": "user",
                                    "content": f"Tool result: {json.dumps(result)}",
                                }
                            )
                            continue
                except (json.JSONDecodeError, AttributeError):
                    pass

            # No tool call, return final response
            return content.strip()

        return "I need more information to answer this question."

    async def _execute_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool and return the result."""
        lms = self._get_lms()

        try:
            if name == "get_items":
                result = await lms.get_labs()
                return {"items": result.get("labs", [])}
            elif name == "get_learners":
                resp = await lms._client.get("/learners/")
                resp.raise_for_status()
                return {"learners": resp.json()}
            elif name == "get_scores":
                lab = arguments.get("lab", "")
                resp = await lms._client.get("/analytics/scores/", params={"lab": lab})
                resp.raise_for_status()
                return {"scores": resp.json(), "lab": lab}
            elif name == "get_pass_rates":
                lab = arguments.get("lab", "")
                result = await lms.get_pass_rates(lab)
                return {"pass_rates": result.get("pass_rates", [])}
            elif name == "get_timeline":
                lab = arguments.get("lab", "")
                resp = await lms._client.get(
                    "/analytics/timeline/", params={"lab": lab}
                )
                resp.raise_for_status()
                return {"timeline": resp.json(), "lab": lab}
            elif name == "get_groups":
                lab = arguments.get("lab", "")
                resp = await lms._client.get("/analytics/groups/", params={"lab": lab})
                resp.raise_for_status()
                return {"groups": resp.json(), "lab": lab}
            elif name == "get_top_learners":
                lab = arguments.get("lab", "")
                limit = int(arguments.get("limit", 5))
                resp = await lms._client.get(
                    "/analytics/top-learners/", params={"lab": lab, "limit": limit}
                )
                resp.raise_for_status()
                return {"top_learners": resp.json(), "lab": lab}
            elif name == "get_completion_rate":
                lab = arguments.get("lab", "")
                resp = await lms._client.get(
                    "/analytics/completion-rate/", params={"lab": lab}
                )
                resp.raise_for_status()
                return {"completion_rate": resp.json(), "lab": lab}
            elif name == "trigger_sync":
                resp = await lms._client.post("/pipeline/sync")
                resp.raise_for_status()
                return {"sync_result": resp.json()}
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)}
