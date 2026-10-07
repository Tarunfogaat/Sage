import json
import os
import re
from typing import Any, Awaitable, Callable

import httpx
from mcp import Client
from openai import AsyncOpenAI

from .config import load_project_environment

load_project_environment()


EventSender = Callable[
    [dict[str, Any]],
    Awaitable[None]
]

AGENT_INSTRUCTIONS = """
You are Sage.

You are a general-purpose AI assistant with tools for Zoho CRM,
Google Sheets, Google Docs, and Google Slides.

Respond naturally and helpfully to greetings and general questions.

Use the relevant MCP tool when the user asks to read or change connected
Zoho CRM or Google Workspace data. Never invent data or claim a change
succeeded unless the corresponding tool succeeds.

Ask a concise follow-up question when a requested action is missing
required details or could change data ambiguously.

After a tool returns, summarize the result in plain language.
"""


class SageAgent:

    def __init__(
        self,
        mcp_url: str
    ):

        self.mcp_url = mcp_url

        self.mcp_client = None

        self.tools = []

        self.tool_map = {}


        api_key = os.getenv(
            "OPENAI_API_KEY",
            ""
        )


        self.openai = (

            AsyncOpenAI(
                api_key=api_key
            )

            if api_key

            else None
        )

        self.gemini_api_key = os.getenv(
            "GEMINI_API_KEY",
            ""
        )

        self.gemini_model = os.getenv(
            "GEMINI_MODEL",
            ""
        ).strip()

        self.model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.5"
        )


    # =================================
    # CONNECT MCP
    # =================================

    async def connect(self):

        print(
            "[AGENT] Connecting to MCP..."
        )


        self.mcp_client = Client(
            self.mcp_url
        )


        await self.mcp_client.__aenter__()


        result = await (
            self.mcp_client
            .list_tools()
        )


        self.tools = result.tools


        self.tool_map = {

            tool.name:
                tool

            for tool in self.tools
        }


        print(
            "[AGENT] Tools loaded:",
            [
                tool.name
                for tool in self.tools
            ]
        )


    # =================================
    # CLOSE
    # =================================

    async def close(self):

        if self.mcp_client:

            await self.mcp_client.__aexit__(
                None,
                None,
                None
            )

            self.mcp_client = None


    # =================================
    # MAIN RUN
    # =================================

    async def run(

        self,

        query: str,

        emit: EventSender

    ):

        if not self.mcp_client:

            raise RuntimeError(
                "MCP client not connected"
            )


        if self.gemini_api_key:
            if not self.gemini_model:
                raise RuntimeError(
                    "Gemini is configured without a model. "
                    "Set GEMINI_MODEL in the project .env file and restart Sage."
                )

            await emit({
                "type": "status",
                "message": "Sage is ready with Gemini."
            })

            return await (
                self.run_with_gemini(
                    query,
                    emit
                )
            )

        if self.openai:
            return await self.run_with_llm(
                query,
                emit
            )

        await emit({
            "type": "status",
            "message": (
                "Gemini is not configured. Add GEMINI_API_KEY to "
                "the project .env file and restart Sage for normal AI replies."
            )
        })
        return await self.local_router(query, emit)


    # =================================
    # LLM TOOL ROUTING
    # =================================

    async def run_with_llm(

        self,

        query: str,

        emit: EventSender

    ):

        tools = []


        for tool in self.tools:

            schema = getattr(
                tool,
                "input_schema",
                None
            ) or getattr(
                tool,
                "inputSchema",
                None
            )


            if schema is None:

                schema = {
                    "type": "object",
                    "properties": {}
                }


            tools.append({

                "type":
                    "function",

                "name":
                    tool.name,

                "description":
                    tool.description or "",

                "parameters":
                    schema,

                "strict":
                    False
            })


        response = await (
            self.openai.responses.create(

                model=self.model,

                instructions=AGENT_INSTRUCTIONS,

                input=query,

                tools=tools,

                parallel_tool_calls=False
            )
        )


        # ---------------------------------
        # Tool execution loop
        # ---------------------------------

        while True:

            calls = [

                item

                for item
                in response.output

                if item.type ==
                "function_call"
            ]


            # No tool call
            if not calls:

                return (
                    response.output_text
                    or
                    "No response generated."
                )


            input_items = list(
                response.output
            )


            for call in calls:

                tool_name = call.name


                arguments = json.loads(
                    call.arguments
                )


                # Tell frontend:
                # Intent detected

                await emit({

                    "type":
                        "intent",

                    "tool":
                        tool_name,

                    "arguments":
                        arguments
                })


                # Tool selected

                await emit({

                    "type":
                        "tool_call",

                    "tool":
                        tool_name,

                    "arguments":
                        arguments
                })


                # Execute

                await emit({

                    "type":
                        "tool_executing",

                    "tool":
                        tool_name
                })


                try:

                    result = await (
                        self.mcp_client
                        .call_tool(
                            tool_name,
                            arguments
                        )
                    )


                    output = (
                        self.convert_result(
                            result
                        )
                    )


                    await emit({

                        "type":
                            "tool_result",

                        "tool":
                            tool_name,

                        "result":
                            output
                    })


                except Exception as exc:

                    output = {

                        "error":
                            str(exc)
                    }


                    await emit({

                        "type":
                            "tool_error",

                        "tool":
                            tool_name,

                        "error":
                            str(exc)
                    })


                input_items.append({

                    "type":
                        "function_call_output",

                    "call_id":
                        call.call_id,

                    "output":
                        json.dumps(
                            output,
                            ensure_ascii=False
                        )
                })


            # Ask LLM to produce
            # final response

            response = await (
                self.openai.responses.create(

                    model=self.model,

                    instructions=AGENT_INSTRUCTIONS,

                    input=input_items,

                    tools=tools,

                    parallel_tool_calls=False
                )
            )


    # =================================
    # GEMINI TOOL ROUTING
    # =================================

    async def run_with_gemini(
        self,
        query: str,
        emit: EventSender
    ) -> str:

        declarations = []

        for tool in self.tools:

            schema = getattr(
                tool,
                "input_schema",
                None
            ) or getattr(
                tool,
                "inputSchema",
                None
            ) or {
                "type": "object",
                "properties": {}
            }

            schema = self.clean_gemini_schema(schema)

            declarations.append({
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema
            })

        contents = [{
            "role": "user",
            "parts": [{
                "text": query
            }]
        }]

        endpoint = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.gemini_model}:generateContent"
        )

        payload: dict[str, Any] = {
            "systemInstruction": {
                "parts": [{
                    "text": AGENT_INSTRUCTIONS
                }]
            },
            "contents": contents,
            "tools": [{
                "functionDeclarations": declarations
            }],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "AUTO"
                }
            }
        }

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            for _ in range(10):

                response = await client.post(
                    endpoint,
                    headers={
                        "x-goog-api-key":
                            self.gemini_api_key
                    },
                    json=payload
                )

                if response.is_error:

                    raise RuntimeError(
                        "Gemini API failed "
                        f"({response.status_code}): "
                        f"{response.text}"
                    )

                data = response.json()
                candidates = data.get(
                    "candidates",
                    []
                )

                if not candidates:

                    raise RuntimeError(
                        "Gemini returned no response candidates: "
                        f"{data}"
                    )

                candidate_content = candidates[0].get(
                    "content",
                    {}
                )

                parts = candidate_content.get(
                    "parts",
                    []
                )

                function_calls = [
                    part["functionCall"]
                    for part in parts
                    if "functionCall" in part
                ]

                if not function_calls:

                    answer = "".join(
                        part.get("text", "")
                        for part in parts
                    )

                    return answer or "No response generated."

                contents.append(candidate_content)

                function_responses = []

                for call in function_calls:

                    tool_name = call.get("name", "")

                    if tool_name not in self.tool_map:

                        raise RuntimeError(
                            "Gemini requested an unknown MCP tool: "
                            f"{tool_name}"
                        )

                    arguments = call.get("args", {})

                    if not isinstance(arguments, dict):

                        raise RuntimeError(
                            f"Gemini returned invalid arguments "
                            f"for {tool_name}"
                        )

                    await emit({
                        "type": "intent",
                        "tool": tool_name,
                        "arguments": arguments
                    })

                    await emit({
                        "type": "tool_call",
                        "tool": tool_name,
                        "arguments": arguments
                    })

                    await emit({
                        "type": "tool_executing",
                        "tool": tool_name
                    })

                    try:

                        result = await (
                            self.mcp_client
                            .call_tool(
                                tool_name,
                                arguments
                            )
                        )

                        output = self.convert_result(
                            result
                        )

                        await emit({
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": output
                        })

                    except Exception as exc:

                        output = {
                            "error": str(exc)
                        }

                        await emit({
                            "type": "tool_error",
                            "tool": tool_name,
                            "error": str(exc)
                        })

                    function_responses.append({
                        "functionResponse": {
                            "name": tool_name,
                            "response": (
                                output
                                if isinstance(output, dict)
                                else {"result": output}
                            )
                        }
                    })

                contents.append({
                    "role": "user",
                    "parts": function_responses
                })

        raise RuntimeError(
            "Gemini exceeded the maximum number of tool-calling turns."
        )

    @staticmethod
    def clean_gemini_schema(
        schema: Any
    ) -> Any:
        supported_keys = {
            "type",
            "properties",
            "required",
            "items",
            "description",
            "enum",
            "format",
            "nullable",
            "minimum",
            "maximum",
            "minItems",
            "maxItems",
            "minLength",
            "maxLength",
            "pattern"
        }

        if isinstance(schema, dict):
            cleaned = {}

            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    cleaned[key] = {
                        property_name:
                            SageAgent.clean_gemini_schema(property_schema)
                        for property_name, property_schema in value.items()
                    }
                elif key in supported_keys:
                    cleaned[key] = SageAgent.clean_gemini_schema(value)

            return cleaned

        if isinstance(schema, list):
            return [
                SageAgent.clean_gemini_schema(value)
                for value in schema
            ]

        return schema


    # =================================
    # MCP RESULT
    # =================================

    @staticmethod
    def convert_result(result):

        structured = getattr(
            result,
            "structured_content",
            None
        )


        if structured is not None:

            return structured


        content = getattr(
            result,
            "content",
            []
        )


        output = []


        for item in content:

            text = getattr(
                item,
                "text",
                None
            )


            if text:

                try:

                    output.append(
                        json.loads(text)
                    )

                except Exception:

                    output.append(text)


        return output


    # =================================
    # LOCAL FALLBACK
    # =================================

    async def local_router(

        self,

        query,

        emit

    ):

        q = query.lower()

        if any(
            greeting in q.split()
            for greeting in ("hi", "hello", "hey")
        ):
            return (
                "Hello! I'm Sage, your AI assistant. I can help with "
                "Google Sheets, Docs, Slides, Zoho CRM, or general "
                "questions. What would you like to do?"
            )


        if (
            "lead" in q
            and
            any(
                x in q
                for x in [
                    "show",
                    "get",
                    "list",
                    "latest"
                ]
            )
        ):

            tool = "get_leads"

            arguments = {

                "page": 1,

                "per_page": 10
            }


        elif "contact" in q:

            tool = "get_contacts"

            arguments = {

                "page": 1,

                "per_page": 10
            }


        elif (
            "search" in q
            and
            "lead" in q
        ):

            match = re.search(

                r"[\w.+-]+@[\w-]+\.[\w.-]+",

                query
            )


            if not match:

                return (
                    "Please provide "
                    "the lead email."
                )


            tool = "search_leads"

            arguments = {

                "email":
                    match.group(0)
            }


        else:

            return (
                "I can help with your work tools. For a normal AI "
                "conversation, set GEMINI_API_KEY in the project .env "
                "file and restart Sage. Without it, try a simple greeting "
                "or ask for leads or contacts."
            )


        await emit({

            "type":
                "intent",

            "tool":
                tool,

            "arguments":
                arguments
        })


        await emit({

            "type":
                "tool_call",

            "tool":
                tool,

            "arguments":
                arguments
        })


        await emit({

            "type":
                "tool_executing",

            "tool":
                tool
        })


        result = await (
            self.mcp_client
            .call_tool(
                tool,
                arguments
            )
        )


        output = self.convert_result(
            result
        )


        await emit({

            "type":
                "tool_result",

            "tool":
                tool,

            "result":
                output
        })


        return json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        )