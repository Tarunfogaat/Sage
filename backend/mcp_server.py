from typing import Any

from mcp.server.mcpserver import MCPServer

from .google_client import GoogleWorkspaceClient
from .zoho_client import ZohoCRMClient


# =====================================
# MCP SERVER
# =====================================

mcp = MCPServer(
    "Sage Workspace MCP Server"
)


zoho = ZohoCRMClient()
google_workspace = GoogleWorkspaceClient()


@mcp.tool()
async def google_sheets_list(
    page_size: int = 20
) -> dict[str, Any]:
    """List Google Sheets spreadsheets available to the configured account."""
    return await google_workspace.list_spreadsheets(page_size)


@mcp.tool()
async def google_sheets_create(
    title: str
) -> dict[str, Any]:
    """Create a new Google Sheets spreadsheet."""
    return await google_workspace.create_spreadsheet(title)


@mcp.tool()
async def google_sheets_read(
    spreadsheet_id: str,
    range_name: str
) -> dict[str, Any]:
    """Read values from a Google Sheets range, such as Sheet1!A1:D20."""
    return await google_workspace.read_sheet(
        spreadsheet_id,
        range_name
    )


@mcp.tool()
async def google_sheets_update(
    spreadsheet_id: str,
    range_name: str,
    values: list[list[str]]
) -> dict[str, Any]:
    """Write values to a Google Sheets range."""
    return await google_workspace.update_sheet(
        spreadsheet_id,
        range_name,
        values
    )


@mcp.tool()
async def google_sheets_append(
    spreadsheet_id: str,
    range_name: str,
    values: list[list[str]]
) -> dict[str, Any]:
    """Append rows to a Google Sheets range."""
    return await google_workspace.append_sheet(
        spreadsheet_id,
        range_name,
        values
    )


@mcp.tool()
async def google_docs_get(
    document_id: str
) -> dict[str, Any]:
    """Read a Google Docs document."""
    return await google_workspace.get_document(document_id)


@mcp.tool()
async def google_docs_create(
    title: str
) -> dict[str, Any]:
    """Create a new Google Docs document."""
    return await google_workspace.create_document(title)


@mcp.tool()
async def google_docs_append_text(
    document_id: str,
    text: str
) -> dict[str, Any]:
    """Append text to the end of a Google Docs document."""
    return await google_workspace.append_document_text(
        document_id,
        text
    )


@mcp.tool()
async def google_slides_get(
    presentation_id: str
) -> dict[str, Any]:
    """Read a Google Slides presentation."""
    return await google_workspace.get_presentation(presentation_id)


@mcp.tool()
async def google_slides_create(
    title: str
) -> dict[str, Any]:
    """Create a new Google Slides presentation."""
    return await google_workspace.create_presentation(title)


@mcp.tool()
async def google_slides_add_slide(
    presentation_id: str,
    title: str,
    body: str = ""
) -> dict[str, Any]:
    """Add a title-and-body slide to a Google Slides presentation."""
    return await google_workspace.add_slide_with_text(
        presentation_id,
        title,
        body
    )


# =====================================
# TOOL 1
# GET LEADS
# =====================================

@mcp.tool()
async def get_leads(

    page: int = 1,

    per_page: int = 10

) -> dict[str, Any]:

    """
    Get leads from Zoho CRM.
    """

    print(
        f"[MCP] get_leads("
        f"page={page}, "
        f"per_page={per_page})"
    )


    return await zoho.get_leads(

        page=page,

        per_page=per_page
    )


# =====================================
# TOOL 2
# CREATE LEAD
# =====================================

@mcp.tool()
async def create_lead(

    last_name: str,

    company: str,

    email: str | None = None,

    first_name: str | None = None

) -> dict[str, Any]:

    """
    Create a new lead in Zoho CRM.
    """

    print(
        "[MCP] create_lead"
    )


    return await zoho.create_lead(

        last_name=last_name,

        company=company,

        email=email,

        first_name=first_name
    )


# =====================================
# TOOL 3
# UPDATE LEAD
# =====================================

@mcp.tool()
async def update_lead(

    lead_id: str,

    fields: dict[str, Any]

) -> dict[str, Any]:

    """
    Update a Zoho CRM lead.
    """

    print(
        f"[MCP] update_lead "
        f"{lead_id}"
    )


    return await zoho.update_lead(

        lead_id,

        fields
    )


# =====================================
# TOOL 4
# SEARCH LEAD
# =====================================

@mcp.tool()
async def search_leads(

    email: str

) -> dict[str, Any]:

    """
    Search Zoho CRM leads by email.
    """

    print(
        f"[MCP] search_leads "
        f"{email}"
    )


    return await zoho.search_leads(
        email
    )


# =====================================
# TOOL 5
# GET CONTACTS
# =====================================

@mcp.tool()
async def get_contacts(

    page: int = 1,

    per_page: int = 10

) -> dict[str, Any]:

    """
    Get contacts from Zoho CRM.
    """

    print(
        f"[MCP] get_contacts"
    )


    return await zoho.get_contacts(

        page=page,

        per_page=per_page
    )