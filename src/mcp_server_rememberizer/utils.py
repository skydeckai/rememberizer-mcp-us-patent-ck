import logging
from enum import Enum

import httpx
from dotenv import load_dotenv
from httpx import HTTPError, HTTPStatusError, Timeout
from mcp import McpError, ErrorData
from pydantic import AnyUrl

logger = logging.getLogger(__name__)

load_dotenv()

APP_NAME = "mcp_server_rememberizer"
ACCOUNT_INFORMATION_PATH = "account/"
LIST_DOCUMENTS_PATH = "documents/"
RETRIEVE_DOCUMENT_PATH = "documents/{id}/contents/"
RETRIEVE_SLACK_PATH = "discussions/{id}/contents/?integration_type=slack"
SEARCH_PATH = "documents/search/"
AGENTIC_SEARCH_PATH = "documents/agentic_search/"
LIST_INTEGRATIONS_PATH = "integrations/"
MEMORIZE_PATH = "documents/memorize/"


class RememberizerTools(Enum):
    SEARCH = "retrieve_semantically_similar_internal_knowledge"
    AGENTIC_SEARCH = "smart_search_internal_knowledge"
    LIST_INTEGRATIONS = "list_internal_knowledge_systems"
    ACCOUNT_INFORMATION = "rememberizer_account_information"
    LIST_DOCUMENTS = "list_personal_team_knowledge_documents"
    MEMORIZE = "remember_this"


class APIClient:
    def __init__(self, base_url: str, ck_id: str):
        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=Timeout(connect=60.0, read=60.0, write=5.0, pool=5.0),
            headers={
                "Content-Type": "application/json",
                "public-ck-id": ck_id,
            },
        )

    async def get(self, path: str, params: dict = None):
        try:
            logger.debug(f"Fetching {path}")
            response = await self.http_client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise McpError(ErrorData(-32001, "Error: Unauthorized. Please check your REMEMBERIZER API token"))
            logger.error(
                f"HTTP {exc.response.status_code} error while fetching {path}: {str(exc)}",
                exc_info=True,
            )
            return exc.response.json()  # Return full error message to the client
        except HTTPError as exc:
            logger.error(
                f"Connection error while fetching {path}: {str(exc)}", exc_info=True
            )
            raise McpError(ErrorData(-32000, f"Failed to fetch {path}. Connection error."))

    async def post(self, path, data: dict, params: dict = None):
        try:
            logger.debug(f"Posting to {path}")
            response = await self.http_client.post(path, json=data, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise McpError(ErrorData(-32001, "Error: Unauthorized. Please check your REMEMBERIZER API token"))
            logger.error(
                f"HTTP {exc.response.status_code} error while posting to {path}: {str(exc)}",
                exc_info=True,
            )
            return exc.response.json()  # Return full error message to the client
        except HTTPError as exc:
            logger.error(
                f"Connection error while posting to {path}: {str(exc)}", exc_info=True
            )
            raise McpError(ErrorData(-32000, f"Failed to post to {path}. Connection error."))

def get_document_uri(document):
    host = "slack" if document["integration_type"] == "slack" else "document"
    return AnyUrl(f"rememberizer://{host}/{document['pk']}")


def add_empty_results_guidance(data: dict, tool_name: str, has_datetime_filter: bool = False) -> str:
    if "matched_chunks" not in data or len(data["matched_chunks"]) > 0:
        return data

    if "message" in data and "Unable to complete" in data["message"]:
        return data

    guidances = [
        "Check `data_sources` to verify that knowledge sources are connected and contain documents."
    ]

    # Tool-specific guidance
    if tool_name == RememberizerTools.SEARCH.value:
        guidances.append("Try broader or more general terms in your `match_this` parameter.")
    elif tool_name == RememberizerTools.AGENTIC_SEARCH.value:
        guidances.append("Follow `result` summary to understand the context of the results and refine your query.")
        guidances.append("Review the `metadata.iterations` to see how your query was transformed - use this to refine your approach.")

    if has_datetime_filter:
        guidances.append("Consider adjusting the datetime range.")

    data["guidance"] = " ".join(guidances)

    return data
