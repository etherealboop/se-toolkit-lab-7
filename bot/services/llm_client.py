"""
LLM API client for Qwen Code.

Handles tool calling with the LLM for intent-based routing.
"""

import json
import os
from typing import Any

import httpx


# Define all 9 backend endpoints as LLM tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks. Use this to discover what labs are available.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get list of enrolled students and their groups. Use this to find student counts or group information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group": {"type": "string", "description": "Optional group filter, e.g., 'A1'"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets) for a lab. Shows how many students got each score range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab. Use this to see task difficulty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab. Shows activity over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group scores and student counts for a lab. Use this to compare groups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab. Use this for leaderboards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"},
                    "limit": {"type": "integer", "description": "Number of top learners to return, e.g., 5"}
                },
                "required": ["lab", "limit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab. Shows what fraction of students completed the lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g., 'lab-01', 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger ETL sync to refresh data from autochecker. Use this when data seems outdated.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an assistant for a Learning Management System (LMS). You have access to backend data through tools.

When a user asks a question:
1. First, understand what they're asking about (which lab, what metric)
2. Call the appropriate tool(s) to get the data
3. Analyze the results
4. Provide a clear, helpful answer with specific numbers

Available tools:
- get_items: List all labs and tasks
- get_learners: Get enrolled students and groups
- get_scores: Get score distribution for a lab (4 buckets)
- get_pass_rates: Get per-task pass rates for a lab
- get_timeline: Get submissions per day for a lab
- get_groups: Get per-group performance for a lab
- get_top_learners: Get top N students for a lab
- get_completion_rate: Get completion percentage for a lab
- trigger_sync: Refresh data from autochecker

For questions like "which lab has the lowest pass rate", you need to:
1. First call get_items to get all labs
2. Then call get_pass_rates for each lab
3. Compare the results
4. Report the lab with the lowest rate

Always provide specific numbers from the data, not vague answers.
"""


class LLMClient:
    """Client for Qwen Code LLM API with tool calling."""

    def __init__(self, api_key: str, base_url: str, model: str):
        """
        Initialize the LLM client.

        Args:
            api_key: API key for authentication
            base_url: Base URL of the LLM API (e.g., http://localhost:42005/v1)
            model: Model name to use (e.g., qwen3-coder-flash)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        max_iterations: int = 5,
    ) -> str:
        """
        Chat with the LLM using tool calling.

        Args:
            messages: List of conversation messages
            max_iterations: Maximum tool calling iterations

        Returns:
            Final response from the LLM
        """
        # Add system prompt
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
                    "tools": TOOLS,
                    "tool_choice": "auto",
                },
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]

            # Check if LLM wants to call tools
            if "tool_calls" in message and message["tool_calls"]:
                tool_calls = message["tool_calls"]
                conversation.append(message)

                # Execute each tool call
                for tool_call in tool_calls:
                    function = tool_call["function"]
                    tool_name = function["name"]
                    tool_args = json.loads(function["arguments"])

                    result = await self._execute_tool(tool_name, tool_args)

                    # Add tool result to conversation
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                # Continue the loop to get LLM's response with tool results
            else:
                # No tool calls, return the final response
                return message["content"]

        # Max iterations reached, return last response
        return "I need more information to answer this question."

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return the result."""
        from services.lms_client import LMSClient

        # Get LMS client from environment
        lms_url = os.getenv("LMS_API_URL", "http://localhost:42002")
        lms_key = os.getenv("LMS_API_KEY", "")
        lms = LMSClient(lms_url, lms_key)

        try:
            if name == "get_items":
                result = await lms.get_labs()
                return {"items": result.get("labs", [])}
            elif name == "get_learners":
                result = await lms._client.get("/learners/")
                result.raise_for_status()
                return {"learners": result.json()}
            elif name == "get_scores":
                lab = arguments.get("lab", "")
                result = await lms._client.get("/analytics/scores/", params={"lab": lab})
                result.raise_for_status()
                return {"scores": result.json(), "lab": lab}
            elif name == "get_pass_rates":
                lab = arguments.get("lab", "")
                result = await lms.get_pass_rates(lab)
                return result
            elif name == "get_timeline":
                lab = arguments.get("lab", "")
                result = await lms._client.get("/analytics/timeline/", params={"lab": lab})
                result.raise_for_status()
                return {"timeline": result.json(), "lab": lab}
            elif name == "get_groups":
                lab = arguments.get("lab", "")
                result = await lms._client.get("/analytics/groups/", params={"lab": lab})
                result.raise_for_status()
                return {"groups": result.json(), "lab": lab}
            elif name == "get_top_learners":
                lab = arguments.get("lab", "")
                limit = arguments.get("limit", 5)
                result = await lms._client.get(
                    "/analytics/top-learners/",
                    params={"lab": lab, "limit": limit},
                )
                result.raise_for_status()
                return {"top_learners": result.json(), "lab": lab}
            elif name == "get_completion_rate":
                lab = arguments.get("lab", "")
                result = await lms._client.get(
                    "/analytics/completion-rate/",
                    params={"lab": lab},
                )
                result.raise_for_status()
                return {"completion_rate": result.json(), "lab": lab}
            elif name == "trigger_sync":
                result = await lms._client.post("/pipeline/sync")
                result.raise_for_status()
                return {"sync_result": result.json()}
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            await lms.close()
