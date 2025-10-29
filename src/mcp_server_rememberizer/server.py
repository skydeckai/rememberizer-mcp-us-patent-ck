import json
import logging

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from pydantic import AnyUrl

from mcp_server_rememberizer.utils import (
    ACCOUNT_INFORMATION_PATH,
    AGENTIC_SEARCH_PATH,
    APP_NAME,
    LIST_DOCUMENTS_PATH,
    LIST_INTEGRATIONS_PATH,
    MEMORIZE_PATH,
    RETRIEVE_DOCUMENT_PATH,
    RETRIEVE_SLACK_PATH,
    SEARCH_PATH,
    APIClient,
    add_empty_results_guidance,
    RememberizerTools,
    get_document_uri,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REMEMBERIZER_BASE_URL = "https://api.rememberizer.ai/api/v1/"
REMEMBERIZER_CK_ID = "{{CK_ID}}"

TOOL_CONTEXT_SUFFIX = "\n**Data context**: {{CK_DESCRIPTION}}"

client = APIClient(base_url=REMEMBERIZER_BASE_URL, ck_id=REMEMBERIZER_CK_ID)


async def serve() -> Server:
    server = Server(APP_NAME)

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        data = await client.get(LIST_DOCUMENTS_PATH)
        return [
            types.Resource(
                uri=get_document_uri(document),
                name=document["name"],
                mimeType="text/json",
            )
            for document in data["results"]
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        path = None
        if uri.host == "document":
            path = RETRIEVE_DOCUMENT_PATH
        elif uri.host == "slack":
            path = RETRIEVE_SLACK_PATH
        if not path:
            raise ValueError(f"Unknown resource: {uri}")

        document_id = uri.path.lstrip("/")
        data = await client.get(path.format(id=document_id))

        return json.dumps(data, indent=2)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=RememberizerTools.ACCOUNT_INFORMATION.value,
                description=f"Get information about your Rememberizer.ai personal/team knowledge repository account. This includes account holder name and email address.\n\n{TOOL_CONTEXT_SUFFIX}",
                inputSchema={
                    "type": "object",
                },
            ),
            types.Tool(
                name=RememberizerTools.SEARCH.value,
                description=(
                    f"Send a block of text and retrieve cosine similar matches from your connected Rememberizer personal/team internal knowledge and memory repository.\n\n{TOOL_CONTEXT_SUFFIX}"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "match_this": {
                            "type": "string",
                            "description": "Up to a 400-word sentence for which you wish to find "
                            "semantically similar chunks of knowledge.",
                        },
                        "n_results": {
                            "type": "integer",
                            "description": (
                                "Number of semantically similar chunks of text to return. "
                                "Use 'n_results=3' for up to 5, and 'n_results=10' for more information. "
                                "If you do not receive enough information, consider trying again with a larger "
                                "'n_results' value."
                            ),
                        },
                        "from_datetime_ISO8601": {
                            "type": "string",
                            "description": (
                                "Start date in ISO 8601 format with timezone (e.g., 2023-01-01T00:00:00Z). "
                                "Use this to filter results from a specific date."
                            ),
                        },
                        "to_datetime_ISO8601": {
                            "type": "string",
                            "description": (
                                "End date in ISO 8601 format with timezone (e.g., 2024-01-01T00:00:00Z). "
                                "Use this to filter results until a specific date."
                            ),
                        },
                    },
                    "required": ["match_this"],
                },
            ),
            types.Tool(
                name=RememberizerTools.AGENTIC_SEARCH.value,
                description="Search for documents in Rememberizer in its personal/team internal knowledge and memory repository using a simple query that returns the results of an agentic search. The search may include sources such as Slack discussions, Gmail, Dropbox documents, Google Drive documents, and uploaded files. Consider using the tool list_internal_knowledge_systems to find out which are available. Use the tool list_internal_knowledge_systems to find out which sources are available. \n\nYou can specify a from_datetime_ISO8601 and a to_datetime_ISO8601, and you should look at the context of your request to make sure you put reasonable parameters around this by, for example, converting a reference to recently to a start date two weeks before today, or converting yesterday to a timeframe during the last day. But do be aware of the effect of time zone differences in the source data and for the requestor.\n\n{TOOL_CONTEXT_SUFFIX}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Up to a 400-word sentence for which you wish to find "
                            "semantically similar chunks of knowledge.",
                        },
                        "user_context": {
                            "type": "string",
                            "description": (
                                "The additional context for the query. "
                                "You might need to summarize the conversation up to this point for better "
                                "context-awared results."
                            ),
                        },
                        "n_results": {
                            "type": "integer",
                            "description": (
                                "Number of semantically similar chunks of text to return. "
                                "Use 'n_results=3' for up to 5, and 'n_results=10' for more information. "
                                "If you do not receive enough information, consider trying again with a "
                                "larger 'n_results' value."
                            ),
                        },
                        "from_datetime_ISO8601": {
                            "type": "string",
                            "description": (
                                "Start date in ISO 8601 format with timezone (e.g., 2023-01-01T00:00:00Z). "
                                "Use this to filter results from a specific date."
                            ),
                        },
                        "to_datetime_ISO8601": {
                            "type": "string",
                            "description": (
                                "End date in ISO 8601 format with timezone (e.g., 2024-01-01T00:00:00Z). "
                                "Use this to filter results until a specific date."
                            ),
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name=RememberizerTools.LIST_INTEGRATIONS.value,
                description=f"List the sources of personal/team internal knowledge. These may include Slack discussions, Gmail, Dropbox documents, Google Drive documents, and uploaded files.\n\n{TOOL_CONTEXT_SUFFIX}",
                inputSchema={
                    "type": "object",
                },
            ),
            types.Tool(
                name=RememberizerTools.LIST_DOCUMENTS.value,
                description=f"""Retrieves a paginated list of all documents in your personal/team knowledge system. Sources could include Slack discussions, Gmail, Dropbox documents, Google Drive documents, and uploaded files. Consider using the tool list_internal_knowledge_systems to find out which are available.

{TOOL_CONTEXT_SUFFIX}

Use this tool to browse through available documents and their metadata.

Examples:
- List first 100 documents {{"page": 1, "page_size": 100}}
- Get next page: {{"page": 2, "page_size": 100}}
- Get maximum allowed documents: {{"page": 1, "page_size": 1000}}
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "description": "Page number for pagination (starts at 1)",
                            "minimum": 1,
                            "default": 1,
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of documents per page (1-1000)",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 100,
                        },
                    },
                },
            ),
            types.Tool(
                name=RememberizerTools.MEMORIZE.value,
                description=(
                    f"Save a piece of text information in your Rememberizer.ai knowledge system so that it "
                    f"may be recalled in future through tools retrieve_semantically_similar_internal_knowledge or "
                    f"smart_search_internal_knowledge.\n\n{TOOL_CONTEXT_SUFFIX}"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "Name of the information. "
                                "This is used to identify the information in the future."
                            ),
                        },
                        "content": {
                            "type": "string",
                            "description": "The information you wish to memorize.",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        match name:
            case RememberizerTools.SEARCH.value:
                match_this = arguments["match_this"]
                n_results = arguments.get("n_results", 5)
                from_datetime = arguments.get("from_datetime_ISO8601", None)
                to_datetime = arguments.get("to_datetime_ISO8601", None)
                params = {"q": match_this, "n": n_results, "from": from_datetime, "to": to_datetime}
                data = await client.get(SEARCH_PATH, params=params)
                data = add_empty_results_guidance(data, name, bool(from_datetime or to_datetime))
                return [types.TextContent(type="text", text=str(data))]
            case RememberizerTools.AGENTIC_SEARCH.value:
                query = arguments["query"]
                n_results = arguments.get("n_results", 5)
                user_context = arguments.get("user_context", None)
                from_datetime = arguments.get("from_datetime_ISO8601", None)
                to_datetime = arguments.get("to_datetime_ISO8601", None)
                params = {
                    "query": query,
                    "n_chunks": n_results,
                    "user_context": user_context,
                    "from": from_datetime,
                    "to": to_datetime,
                }
                data = await client.post(AGENTIC_SEARCH_PATH, data=params)
                data = add_empty_results_guidance(data, name, bool(from_datetime or to_datetime))
                return [types.TextContent(type="text", text=str(data))]
            case RememberizerTools.LIST_INTEGRATIONS.value:
                data = await client.get(LIST_INTEGRATIONS_PATH)
                return [types.TextContent(type="text", text=str(data.get("data", [])))]
            case RememberizerTools.ACCOUNT_INFORMATION.value:
                data = await client.get(ACCOUNT_INFORMATION_PATH)
                return [types.TextContent(type="text", text=str(data))]
            case RememberizerTools.LIST_DOCUMENTS.value:
                page = arguments.get("page", 1)
                page_size = arguments.get("page_size", 100)
                params = {"page": page, "page_size": page_size}
                data = await client.get(LIST_DOCUMENTS_PATH, params=params)
                return [types.TextContent(type="text", text=str(data))]
            case RememberizerTools.MEMORIZE.value:
                params = {
                    "name": arguments["name"],
                    "content": arguments["content"],
                }
                data = await client.post(MEMORIZE_PATH, data=params)
                return [types.TextContent(type="text", text=str(data))]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    return server


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        server = await serve()
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
