import contextlib
import os
import sys
import uuid
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if __package__ in (None, ""):
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent)
    )
    from backend.config import load_project_environment
    from backend.agent import SageAgent
    from backend.mcp_server import google_workspace, mcp, zoho
else:
    from .config import load_project_environment
    from .agent import SageAgent
    from .mcp_server import google_workspace, mcp, zoho


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_project_environment()


# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent


FRONTEND_DIR = (
    BASE_DIR / "frontend"
)

HOST = "127.0.0.1"
PORT = 8000
WEB_URL = "http://localhost:8000"


# ==========================================
# MCP URL
# ==========================================

MCP_URL = os.getenv(

    "MCP_URL",

    f"http://{HOST}:{PORT}/mcp/"
)


# ==========================================
# MCP HTTP APPLICATION
# ==========================================

mcp_http_app = (
    mcp.streamable_http_app(
        streamable_http_path="/"
    )
)


# ==========================================
# FASTAPI LIFESPAN
# ==========================================

@contextlib.asynccontextmanager
async def lifespan(
    app: FastAPI
) -> AsyncIterator[None]:

    print()
    print("=" * 70)
    print("        SAGE WORKSPACE MCP SERVER")
    print("=" * 70)

    print()
    print(
        "Web UI:"
    )

    print(
        WEB_URL
    )

    print()

    print(
        "MCP Server:"
    )

    print(
        f"http://{HOST}:{PORT}/mcp/"
    )

    print()

    print(
        "WebSocket:"
    )

    print(
        f"ws://{HOST}:{PORT}/ws"
    )

    print()

    print(
        "Available MCP tools:"
    )

    print("Zoho CRM:", "configured" if zoho.configured() else "credentials missing")
    print(
        "Google Sheets:",
        "configured"
        if google_workspace.configured("sheets")
        else "GOOGLE_SHEET_TOKEN missing"
    )
    print(
        "Google Docs:",
        "configured"
        if google_workspace.configured("docs")
        else "GOOGLE_DOCS_TOKEN missing"
    )
    print(
        "Google Slides:",
        "configured"
        if google_workspace.configured("slides")
        else "GOOGLE_SLIDES_TOKEN missing"
    )
    print(
        "Gemini:",
        "configured" if os.getenv("GEMINI_API_KEY") else "GEMINI_API_KEY missing"
    )
    print(
        "Gemini model:",
        os.getenv("GEMINI_MODEL") or "GEMINI_MODEL missing"
    )

    print()

    print("=" * 70)
    print()


    # --------------------------------------
    # START MCP SESSION MANAGER
    # --------------------------------------

    async with mcp.session_manager.run():

        yield


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(

    title="Sage AI Agent",

    description="Sage AI Agent for Zoho CRM and Google Workspace",

    lifespan=lifespan
)


# ==========================================
# MOUNT MCP SERVER
# ==========================================

app.mount(

    "/mcp",

    mcp_http_app
)


# ==========================================
# STATIC FRONTEND
# ==========================================

app.mount(

    "/static",

    StaticFiles(
        directory=FRONTEND_DIR
    ),

    name="static"
)


# ==========================================
# HOME PAGE
# ==========================================

@app.get("/")
async def home():

    return FileResponse(

        FRONTEND_DIR
        / "index.html"
    )


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
async def health():

    return {

        "status":
            "healthy",

        "service":
            "sage-workspace-mcp",

        "mcp_endpoint":
            "/mcp/",

        "websocket":
            "/ws"
    }


# ==========================================
# WEBSOCKET
# ==========================================

@app.websocket("/ws")
async def websocket_endpoint(

    websocket: WebSocket

):

    # --------------------------------------
    # ACCEPT CONNECTION
    # --------------------------------------

    await websocket.accept()


    # --------------------------------------
    # CREATE SESSION ID
    # --------------------------------------

    session_id = str(
        uuid.uuid4()
    )[:8]


    # --------------------------------------
    # CREATE AGENT
    # --------------------------------------

    agent = SageAgent(
        MCP_URL
    )


    # --------------------------------------
    # HELPER TO SEND EVENTS
    # --------------------------------------

    async def emit(
        event: dict
    ):

        await websocket.send_json(
            event
        )


    try:

        # ==================================
        # CONNECTION EVENT
        # ==================================

        await emit({

            "type":
                "connection",

            "status":
                "connected"
        })


        # ==================================
        # SESSION STARTED
        # ==================================

        await emit({

            "type":
                "session_started",

            "session_id":
                session_id
        })


        # ==================================
        # CONNECT AGENT TO MCP
        # ==================================

        await emit({

            "type":
                "status",

            "message":
                "Connecting to workspace tools..."
        })


        print(
            f"[SESSION {session_id}] "
            "Connecting to MCP..."
        )


        await agent.connect()


        print(
            f"[SESSION {session_id}] "
            "MCP connected"
        )


        # ==================================
        # GET MCP TOOLS
        # ==================================

        tools = [

            {

                "name":
                    tool.name,

                "description":
                    tool.description or ""
            }

            for tool
            in agent.tools
        ]

        await emit({
            "type": "integrations",
            "integrations": {
                "Zoho CRM": zoho.configured(),
                "Google Sheets": google_workspace.configured("sheets"),
                "Google Docs": google_workspace.configured("docs"),
                "Google Slides": google_workspace.configured("slides")
            }
        })


        # ==================================
        # SEND TOOLS TO FRONTEND
        # ==================================

        await emit({

            "type":
                "tools_loaded",

            "tools":
                tools
        })


        print(
            f"[SESSION {session_id}] "
            f"Tools loaded: "
            f"{[tool['name'] for tool in tools]}"
        )


        # ==================================
        # SAGE GREETING
        # ==================================

        await emit({

            "type":
                "assistant_message",

            "message": (
                "Hi! I'm Sage, your AI assistant. I can help with "
                "Google Sheets, Docs, Slides, Zoho CRM, and general "
                "questions. What would you like to do?"
            )
        })


        # ==================================
        # CHAT LOOP
        # ==================================

        while True:

            # --------------------------------
            # WAIT FOR FRONTEND MESSAGE
            # --------------------------------

            payload = (
                await websocket
                .receive_json()
            )


            # --------------------------------
            # ONLY HANDLE USER MESSAGE
            # --------------------------------

            if payload.get(
                "type"
            ) != "user_message":

                continue


            # --------------------------------
            # GET USER QUERY
            # --------------------------------

            query = str(

                payload.get(
                    "message",
                    ""
                )

            ).strip()


            # --------------------------------
            # IGNORE EMPTY MESSAGE
            # --------------------------------

            if not query:

                continue


            print()
            print(
                f"[USER {session_id}] "
                f"{query}"
            )


            # =================================
            # SHOW USER MESSAGE
            # =================================

            await emit({

                "type":
                    "user_echo",

                "message":
                    query
            })


            # =================================
            # THINKING EVENT
            # =================================

            await emit({

                "type":
                    "thinking",

                "message":
                    "Analyzing your request..."
            })


            # =================================
            # RUN AGENT
            # =================================

            try:

                answer = await agent.run(

                    query,

                    emit
                )


                # =================================
                # FINAL RESPONSE
                # =================================

                await emit({

                    "type":
                        "final_response",

                    "message":
                        answer
                })


                print(
                    f"[SAGE {session_id}] "
                    f"{answer}"
                )


            except Exception as exc:

                print()

                print(
                    f"[AGENT ERROR] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )


                await emit({

                    "type":
                        "error",

                    "message":
                        str(exc)
                })


    # ======================================
    # CLIENT DISCONNECTED
    # ======================================

    except WebSocketDisconnect:

        print()

        print(
            f"[SESSION {session_id}] "
            "Client disconnected"
        )


    # ======================================
    # OTHER WEBSOCKET ERROR
    # ======================================

    except Exception as exc:

        print()

        print(
            f"[WS ERROR] "
            f"{type(exc).__name__}: "
            f"{exc}"
        )


        try:

            await emit({

                "type":
                    "error",

                "message":
                    str(exc)
            })

        except Exception:

            pass


    # ======================================
    # CLEANUP
    # ======================================

    finally:

        await agent.close()


        print()

        print(
            f"[SESSION {session_id}] "
            "Closed"
        )


if __name__ == "__main__":
    import threading
    import webbrowser

    import uvicorn

    threading.Timer(
        1.5,
        webbrowser.open,
        args=(WEB_URL,),
        kwargs={"new": 2}
    ).start()

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True
    )