let socket = null;
let reconnectTimer = null;


/* =========================================
   DOM ELEMENTS
========================================= */

const landing =
    document.getElementById(
        "landing"
    );


const chatSection =
    document.getElementById(
        "chatSection"
    );


const startButton =
    document.getElementById(
        "startButton"
    );

const navChatButton =
    document.getElementById(
        "navChatButton"
    );


const demoButton =
    document.getElementById(
        "demoButton"
    );


const backButton =
    document.getElementById(
        "backButton"
    );


const newChatButton =
    document.getElementById(
        "newChatButton"
    );


const statusDot =
    document.getElementById(
        "statusDot"
    );


const statusText =
    document.getElementById(
        "statusText"
    );


const integrationList =
    document.getElementById(
        "integrationList"
    );


const toolList =
    document.getElementById(
        "toolList"
    );


const messages =
    document.getElementById(
        "messages"
    );


const messageInput =
    document.getElementById(
        "messageInput"
    );


const sendButton =
    document.getElementById(
        "sendButton"
    );


const activity =
    document.getElementById(
        "activity"
    );


const activityText =
    document.getElementById(
        "activityText"
    );


/* =========================================
   CONNECTION STATUS
========================================= */

function setConnectionStatus(
    connected,
    label = connected
        ? "Connected"
        : "Offline"
) {

    statusDot.classList.toggle(
        "connected",
        connected
    );


    statusText.textContent = label;

}


/* =========================================
   OPEN CHAT
========================================= */

function openChat() {

    landing.classList.add(
        "hidden"
    );


    chatSection.classList.remove(
        "hidden"
    );


    connectWebSocket();


    setTimeout(
        () => {

            messageInput.focus();

        },
        300
    );

}


/* =========================================
   CONNECT WEBSOCKET
========================================= */

function connectWebSocket() {

    if (
        socket &&
        (
            socket.readyState ===
            WebSocket.OPEN

            ||

            socket.readyState ===
            WebSocket.CONNECTING
        )
    ) {

        return;

    }

    if (reconnectTimer) {

        clearTimeout(reconnectTimer);
        reconnectTimer = null;

    }

    const protocol =
        window.location.protocol ===
        "https:"
            ? "wss:"
            : "ws:";


    const connection = new WebSocket(

        `${protocol}//${window.location.host}/ws`

    );

    socket = connection;

    connection.onopen = () => {

        if (socket !== connection) {
            return;
        }

        setConnectionStatus(
            true
        );

    };


    connection.onmessage = (
        event
    ) => {

        if (socket !== connection) {
            return;
        }

        const data =
            JSON.parse(
                event.data
            );


        handleServerEvent(
            data
        );

    };


    connection.onerror = () => {

        if (socket === connection) {
            setConnectionStatus(
                false,
                "Reconnecting..."
            );
        }

    };


    connection.onclose = () => {

        if (socket !== connection) {
            return;
        }

        setConnectionStatus(
            false,
            "Reconnecting..."
        );

        if (!chatSection.classList.contains("hidden")) {
            reconnectTimer = setTimeout(
                () => {
                    reconnectTimer = null;
                    connectWebSocket();
                },
                1500
            );
        }

    };

}


/* =========================================
   HANDLE BACKEND EVENTS
========================================= */

function handleServerEvent(
    data
) {

    switch (
        data.type
    ) {


        /* =============================
           CONNECTION
        ============================= */

        case "connection":

            setConnectionStatus(
                data.status ===
                "connected"
            );

            break;



        /* =============================
           SESSION
        ============================= */

        case "session_started":

            addEvent(
                "info",
                `Session started: ${data.session_id}`
            );

            break;



        /* =============================
           STATUS
        ============================= */

        case "status":

            addEvent(
                "info",
                data.message
            );

            break;



        /* =============================
           MCP TOOLS
        ============================= */

        case "tools_loaded":

            renderTools(
                data.tools
            );

            break;

        case "integrations":

            renderIntegrations(
                data.integrations
            );

            break;



        /* =============================
           SAGE MESSAGE
        ============================= */

        case "assistant_message":

            addMessage(
                "assistant",
                data.message
            );

            break;



        /* =============================
           USER MESSAGE
        ============================= */

        case "user_echo":

            addMessage(
                "user",
                data.message
            );

            break;



        /* =============================
           THINKING
        ============================= */

        case "thinking":

            showActivity(
                data.message
            );

            break;



        /* =============================
           INTENT
        ============================= */

        case "intent":

            hideActivity();


            addEvent(
                "info",
                `Intent detected → ${data.tool}`
            );

            highlightTool(
                data.tool
            );

            break;



        /* =============================
           TOOL CALL
        ============================= */

        case "tool_call":

            addEvent(
                "tool",
                `Tool selected → ${data.tool}`
            );

            break;



        /* =============================
           TOOL EXECUTION
        ============================= */

        case "tool_executing":

            showActivity(
                `Working with ${serviceForTool(data.tool)}...`
            );


            addEvent(
                "tool",
                `Calling MCP tool → ${data.tool}`
            );

            break;



        /* =============================
           TOOL RESULT
        ============================= */

        case "tool_result":

            hideActivity();


            addEvent(
                "result",
                `✓ ${friendlyToolName(data.tool)} completed`
            );

            break;



        /* =============================
           TOOL ERROR
        ============================= */

        case "tool_error":

            hideActivity();


            addEvent(
                "error",
                `✕ ${friendlyToolName(data.tool)}: ${data.error}`
            );

            break;



        /* =============================
           FINAL ANSWER
        ============================= */

        case "final_response":

            hideActivity();


            addMessage(
                "assistant",
                data.message
            );

            break;



        /* =============================
           ERROR
        ============================= */

        case "error":

            hideActivity();


            addEvent(
                "error",
                data.message
            );

            addMessage(
                "assistant",
                `I couldn't complete that request. ${data.message}`
            );

            break;

    }

}

function renderIntegrations(integrations) {
    const names = [
        "Google Sheets",
        "Google Docs",
        "Google Slides",
        "Zoho CRM"
    ];

    const configuredServices = integrations || {};
    integrationList.innerHTML = "";

    names.forEach(name => {
        const configured = Boolean(configuredServices[name]);
        const card = document.createElement("div");
        card.className = "server-card";

        const icon = document.createElement("div");
        icon.className = "server-icon";
        icon.textContent = name.startsWith("Google") ? "G" : "Z";

        const details = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = name;
        const status = document.createElement("small");
        status.textContent = configured
            ? "Ready"
            : "Add credentials in .env";
        details.append(title, status);

        const dot = document.createElement("span");
        dot.className = configured
            ? "server-dot connected"
            : "server-dot";

        card.append(icon, details, dot);
        integrationList.appendChild(card);
    });
}

function serviceForTool(toolName) {
    if (toolName.startsWith("google_sheets_")) {
        return "Google Sheets";
    }
    if (toolName.startsWith("google_docs_")) {
        return "Google Docs";
    }
    if (toolName.startsWith("google_slides_")) {
        return "Google Slides";
    }
    if (
        ["get_leads", "create_lead", "update_lead", "search_leads", "get_contacts"]
            .includes(toolName)
    ) {
        return "Zoho CRM";
    }
    return "your connected tools";
}

function friendlyToolName(toolName) {
    return toolName
        .replace(/^google_sheets_/, "Sheets: ")
        .replace(/^google_docs_/, "Docs: ")
        .replace(/^google_slides_/, "Slides: ")
        .replaceAll("_", " ");
}


/* =========================================
   RENDER MCP TOOLS
========================================= */

function renderTools(
    tools
) {

    toolList.innerHTML = "";


    tools.forEach(
        tool => {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "tool-item";


            item.dataset.tool =
                tool.name;


            item.innerHTML = `

                <span class="tool-check">

                    ✓

                </span>

                <span>

                    ${escapeHtml(
                        tool.name
                    )}

                </span>

            `;


            item.title =
                tool.description ||
                "";


            toolList.appendChild(
                item
            );

        }
    );

}


/* =========================================
   HIGHLIGHT TOOL
========================================= */

function highlightTool(
    toolName
) {

    document
        .querySelectorAll(
            ".tool-item"
        )
        .forEach(
            item => {

                item.classList.toggle(

                    "active",

                    item.dataset.tool ===
                    toolName

                );

            }
        );

}


/* =========================================
   ADD CHAT MESSAGE
========================================= */

function addMessage(
    role,
    text
) {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        `message ${role}`;


    const label =
        role === "user"
            ? "YOU"
            : "SAGE";


    wrapper.innerHTML = `

        <div class="message-label">

            ${label}

        </div>


        <div class="message-bubble">

            ${escapeHtml(text)}

        </div>

    `;


    messages.appendChild(
        wrapper
    );


    scrollMessages();

}


/* =========================================
   ADD LIVE EVENT
========================================= */

function addEvent(
    type,
    text
) {

    const event =
        document.createElement(
            "div"
        );


    event.className =
        `tool-event ${
            type === "error"
                ? "error"
                : ""
        } ${
            type === "result"
                ? "result"
                : ""
        }`;


    event.innerHTML = `

        <strong>

            ${escapeHtml(text)}

        </strong>

    `;


    messages.appendChild(
        event
    );


    scrollMessages();

}


/* =========================================
   ACTIVITY
========================================= */

function showActivity(
    text
) {

    activity.classList.remove(
        "hidden"
    );


    activityText.textContent =
        text;


    scrollMessages();

}


function hideActivity() {

    activity.classList.add(
        "hidden"
    );

}


/* =========================================
   SEND MESSAGE
========================================= */

function sendMessage() {

    const text =
        messageInput.value.trim();


    if (!text) {

        return;

    }


    if (
        !socket ||
        socket.readyState !==
        WebSocket.OPEN
    ) {

        addEvent(
            "error",
            "Sage is reconnecting. Your message is still in the box; send it when Sage is connected."
        );

        return;

    }


    socket.send(

        JSON.stringify({

            type:
                "user_message",

            message:
                text

        })

    );


    messageInput.value = "";

    messageInput.style.height =
        "auto";

}


/* =========================================
   NEW CHAT
========================================= */

function newChat() {

    messages.innerHTML = "";


    addMessage(

        "assistant",

        "New conversation started. " +
        "What would you like me to help with?"

    );

}


/* =========================================
   BACK
========================================= */

function goBack() {

    if (reconnectTimer) {

        clearTimeout(reconnectTimer);
        reconnectTimer = null;

    }

    if (socket) {

        socket.close();

        socket = null;

    }


    chatSection.classList.add(
        "hidden"
    );


    landing.classList.remove(
        "hidden"
    );


    setConnectionStatus(
        false
    );

}


/* =========================================
   SCROLL
========================================= */

function scrollMessages() {

    messages.scrollTop =
        messages.scrollHeight;

}


/* =========================================
   HTML ESCAPE
========================================= */

function escapeHtml(
    value
) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}


/* =========================================
   EVENT LISTENERS
========================================= */

startButton.addEventListener(
    "click",
    openChat
);

navChatButton.addEventListener(
    "click",
    openChat
);


demoButton.addEventListener(
    "click",
    openChat
);


backButton.addEventListener(
    "click",
    goBack
);


newChatButton.addEventListener(
    "click",
    newChat
);


sendButton.addEventListener(
    "click",
    sendMessage
);


/* =========================================
   ENTER TO SEND
========================================= */

messageInput.addEventListener(

    "keydown",

    event => {

        if (
            event.key ===
            "Enter"

            &&

            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();

        }

    }

);


/* =========================================
   AUTO RESIZE TEXTAREA
========================================= */

messageInput.addEventListener(

    "input",

    () => {

        messageInput.style.height =
            "auto";


        messageInput.style.height =
            Math.min(
                messageInput.scrollHeight,
                120
            ) + "px";

    }

);