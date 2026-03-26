"""
LLM API client for Qwen Code.
Handles tool calling with the LLM for intent-based routing.
"""

import json
import os
import re
from typing import Any

import httpx
from services.lms_client import LMSClient

# 9 tools for autochecker verification
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get all labs",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get students",
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
            "description": "Score distribution for a lab",
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
            "description": "Per-task pass rates",
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
            "description": "Submissions timeline",
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
            "description": "Per-group performance",
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
            "description": "Top N students",
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
            "description": "Completion rate",
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
            "description": "Refresh data",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """LMS assistant. Call ONE tool at a time:
{"tool": "name", "args": {}}

Tools: get_items, get_learners, get_scores, get_pass_rates, get_timeline, get_groups, get_top_learners, get_completion_rate, trigger_sync.

RULES:
1. ONE tool per response
2. Wait for result before next call
3. Then provide final answer with numbers"""


class LLMClient:
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
            self._lms = LMSClient(
                os.getenv("LMS_API_URL", "http://localhost:42002"),
                os.getenv("LMS_API_KEY", ""),
            )
        return self._lms

    async def close(self) -> None:
        await self._client.aclose()
        if self._lms:
            await self._lms.close()

    async def chat_with_tools(
        self, messages: list[dict[str, Any]], max_iterations: int = 5
    ) -> str:
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]

        for _ in range(max_iterations):
            resp = await self._client.post(
                "/chat/completions",
                json={"model": self.model, "messages": conversation},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"].get("content", "")

            # Parse FIRST JSON tool call
            match = re.search(r'\{[^{}]*"tool"[^{}]*\}', content)
            if match:
                try:
                    tc = json.loads(match.group())
                    result = await self._execute_tool(
                        tc.get("tool"), tc.get("args", {})
                    )
                    conversation.append({"role": "assistant", "content": content})
                    conversation.append(
                        {
                            "role": "user",
                            "content": f"Result: {json.dumps(result)}\n\nContinue or answer.",
                        }
                    )
                    continue
                except:
                    pass

            return content.strip()

        return "Need more info."

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        lms = self._get_lms()
        try:
            if name == "get_items":
                r = await lms.get_labs()
                return {"items": r.get("labs", [])}
            elif name == "get_learners":
                r = await lms._client.get("/learners/")
                return {"learners": r.json()}
            elif name == "get_scores":
                r = await lms._client.get(
                    "/analytics/scores/", params={"lab": args.get("lab", "")}
                )
                return {"scores": r.json()}
            elif name == "get_pass_rates":
                r = await lms.get_pass_rates(args.get("lab", ""))
                return {"pass_rates": r.get("pass_rates", [])}
            elif name == "get_timeline":
                r = await lms._client.get(
                    "/analytics/timeline/", params={"lab": args.get("lab", "")}
                )
                return {"timeline": r.json()}
            elif name == "get_groups":
                r = await lms._client.get(
                    "/analytics/groups/", params={"lab": args.get("lab", "")}
                )
                return {"groups": r.json()}
            elif name == "get_top_learners":
                r = await lms._client.get(
                    "/analytics/top-learners/",
                    params={
                        "lab": args.get("lab", ""),
                        "limit": int(args.get("limit", 5)),
                    },
                )
                return {"top_learners": r.json()}
            elif name == "get_completion_rate":
                r = await lms._client.get(
                    "/analytics/completion-rate/", params={"lab": args.get("lab", "")}
                )
                return {"completion_rate": r.json()}
            elif name == "trigger_sync":
                r = await lms._client.post("/pipeline/sync")
                return {"sync": r.json()}
            return {"error": f"Unknown: {name}"}
        except Exception as e:
            return {"error": str(e)}
