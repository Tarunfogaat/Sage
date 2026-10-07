import os
from typing import Any, Literal
from urllib.parse import quote

import httpx
from .config import load_project_environment

load_project_environment()

GoogleService = Literal["sheets", "docs", "slides"]
TOKEN_ENV_VARS = {
    "sheets": "GOOGLE_SHEET_TOKEN",
    "docs": "GOOGLE_DOCS_TOKEN",
    "slides": "GOOGLE_SLIDES_TOKEN",
}
SERVICE_NAMES = {
    "sheets": "Google Sheets",
    "docs": "Google Docs",
    "slides": "Google Slides",
}


class GoogleWorkspaceClient:
    def __init__(self) -> None:
        self.access_tokens = {
            service: os.getenv(env_var, "").strip()
            for service, env_var in TOKEN_ENV_VARS.items()
        }

    def configured(self, service: GoogleService) -> bool:
        return bool(self.access_tokens[service])

    async def request(
        self,
        method: str,
        url: str,
        *,
        service: GoogleService,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        access_token = self.access_tokens[service]
        if not access_token:
            env_var = TOKEN_ENV_VARS[service]
            raise RuntimeError(
                f"{SERVICE_NAMES[service]} is not configured. "
                f"Set {env_var} in the project .env file "
                "and restart Sage."
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params=params,
                json=json
            )

        if response.is_error:
            try:
                detail = response.json().get(
                    "error",
                    response.text
                )
            except ValueError:
                detail = response.text

            raise RuntimeError(
                f"Google API failed ({response.status_code}): {detail}"
            )

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def list_spreadsheets(
        self,
        page_size: int = 20
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            service="sheets",
            params={
                "q": (
                    "mimeType = 'application/"
                    "vnd.google-apps.spreadsheet' "
                    "and trashed = false"
                ),
                "pageSize": min(max(page_size, 1), 100),
                "orderBy": "modifiedTime desc",
                "fields": (
                    "nextPageToken,"
                    "files(id,name,mimeType,webViewLink,modifiedTime)"
                )
            }
        )

    async def create_spreadsheet(
        self,
        title: str
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://sheets.googleapis.com/v4/spreadsheets",
            service="sheets",
            json={
                "properties": {
                    "title": title
                }
            }
        )

    async def read_sheet(
        self,
        spreadsheet_id: str,
        range_name: str
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{quote(spreadsheet_id, safe='')}/values/"
            f"{quote(range_name, safe='!:$')}",
            service="sheets",
        )

    async def update_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]]
    ) -> dict[str, Any]:
        return await self.request(
            "PUT",
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{quote(spreadsheet_id, safe='')}/values/"
            f"{quote(range_name, safe='!:$')}",
            service="sheets",
            params={"valueInputOption": "USER_ENTERED"},
            json={
                "majorDimension": "ROWS",
                "values": values
            }
        )

    async def append_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]]
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{quote(spreadsheet_id, safe='')}/values/"
            f"{quote(range_name, safe='!:$')}:append",
            service="sheets",
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS"
            },
            json={
                "majorDimension": "ROWS",
                "values": values
            }
        )

    async def get_document(
        self,
        document_id: str
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://docs.googleapis.com/v1/documents/"
            f"{quote(document_id, safe='')}",
            service="docs",
        )

    async def create_document(
        self,
        title: str
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://docs.googleapis.com/v1/documents",
            service="docs",
            json={"title": title}
        )

    async def append_document_text(
        self,
        document_id: str,
        text: str
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://docs.googleapis.com/v1/documents/"
            f"{quote(document_id, safe='')}:batchUpdate",
            service="docs",
            json={
                "requests": [{
                    "insertText": {
                        "endOfSegmentLocation": {},
                        "text": text
                    }
                }]
            }
        )

    async def get_presentation(
        self,
        presentation_id: str
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://slides.googleapis.com/v1/presentations/"
            f"{quote(presentation_id, safe='')}",
            service="slides",
        )

    async def create_presentation(
        self,
        title: str
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://slides.googleapis.com/v1/presentations",
            service="slides",
            json={"title": title}
        )

    async def add_slide_with_text(
        self,
        presentation_id: str,
        title: str,
        body: str
    ) -> dict[str, Any]:
        import uuid

        slide_id = f"slide{uuid.uuid4().hex}"
        title_id = f"title{uuid.uuid4().hex}"
        body_id = f"body{uuid.uuid4().hex}"

        return await self.request(
            "POST",
            "https://slides.googleapis.com/v1/presentations/"
            f"{quote(presentation_id, safe='')}:batchUpdate",
            service="slides",
            json={
                "requests": [
                    {
                        "createSlide": {
                            "objectId": slide_id,
                            "slideLayoutReference": {
                                "predefinedLayout": "BLANK"
                            }
                        }
                    },
                    {
                        "createShape": {
                            "objectId": title_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "width": {
                                        "magnitude": 600,
                                        "unit": "PT"
                                    },
                                    "height": {
                                        "magnitude": 60,
                                        "unit": "PT"
                                    }
                                },
                                "transform": {
                                    "scaleX": 1,
                                    "scaleY": 1,
                                    "translateX": 60,
                                    "translateY": 35,
                                    "unit": "PT"
                                }
                            }
                        }
                    },
                    {
                        "insertText": {
                            "objectId": title_id,
                            "text": title
                        }
                    },
                    {
                        "createShape": {
                            "objectId": body_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide_id,
                                "size": {
                                    "width": {
                                        "magnitude": 600,
                                        "unit": "PT"
                                    },
                                    "height": {
                                        "magnitude": 300,
                                        "unit": "PT"
                                    }
                                },
                                "transform": {
                                    "scaleX": 1,
                                    "scaleY": 1,
                                    "translateX": 60,
                                    "translateY": 120,
                                    "unit": "PT"
                                }
                            }
                        }
                    },
                    {
                        "insertText": {
                            "objectId": body_id,
                            "text": body
                        }
                    }
                ]
            }
        )
