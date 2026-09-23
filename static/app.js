const uploadView = document.getElementById("uploadView");
const chatView = document.getElementById("chatView");
const chatBox = document.getElementById("chat-box");
const historyBox = document.getElementById("history");
const input = document.getElementById("question");
const chatTitle = document.getElementById("chatTitle");
const newChatBtn = document.getElementById("newChatBtn");
const composerForm = document.getElementById("composerForm");
const fileInput = document.getElementById("file");
const fileLabel = document.getElementById("fileLabel");
const dropZone = document.getElementById("dropZone");
const toast = document.getElementById("toast");
const sidebar = document.getElementById("sidebar");
const menuButton = document.getElementById("menuButton");
const overlay = document.getElementById("overlay");
const searchTrigger = document.getElementById("searchTrigger");
const searchModal = document.getElementById("searchModal");
const globalSearch = document.getElementById("globalSearch");
const searchResults = document.getElementById("searchResults");
const themeToggle = document.getElementById("themeToggle");
const deleteChatBtn = document.getElementById("deleteChatBtn");
const deleteChatDialog = document.getElementById("deleteChatDialog");
const pinChatBtn = document.getElementById("pinChatBtn");
const archiveChatBtn = document.getElementById("archiveChatBtn");
const shareChatBtn = document.getElementById("shareChatBtn");
const attachFileBtn = document.getElementById("attachFileBtn");
const voiceInputBtn = document.getElementById("voiceInputBtn");
const pinnedChatsBtn = document.getElementById("pinnedChatsBtn");
const archivedChatsBtn = document.getElementById("archivedChatsBtn");
const recentChatsBtn = document.getElementById("recentChatsBtn");
const historyLabel = document.getElementById("historyLabel");
const settingsBtn = document.getElementById("settingsBtn");
const settingsPanel = document.getElementById("settingsPanel");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");
const themeSetting = document.getElementById("themeSetting");
const compactMessagesSetting = document.getElementById("compactMessagesSetting");
const openSharedChatsSetting = document.getElementById("openSharedChatsSetting");
const resetSettingsBtn = document.getElementById("resetSettingsBtn");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");

let currentChatId = null;
let chatsCache = [];
let toastTimer = null;
let activeHistoryView = "recent";
let currentChatState = { is_pinned: false, is_archived: false };
const defaultSettings = {
    theme: "light",
    compactMessages: false,
    openSharedChats: true
};
let appSettings = { ...defaultSettings };

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function setView(view) {
    if (view === "chat") {
        uploadView.style.display = "none";
        chatView.style.display = "block";
        return;
    }

    uploadView.style.display = "flex";
    chatView.style.display = "none";
}

function closeOverlaySurfaces() {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
    searchModal.classList.remove("show");
    settingsPanel.classList.remove("show");
    document.getElementById("profileMenu")?.classList.remove("show");
}

function readSettings() {
    try {
        return { ...defaultSettings, ...JSON.parse(localStorage.getItem("docmind-settings") || "{}") };
    } catch (error) {
        return { ...defaultSettings };
    }
}

function persistSettings() {
    localStorage.setItem("docmind-settings", JSON.stringify(appSettings));
}

function syncSettingsControls() {
    themeSetting.value = appSettings.theme;
    compactMessagesSetting.checked = appSettings.compactMessages;
    openSharedChatsSetting.checked = appSettings.openSharedChats;
}

function applySettings() {
    document.body.classList.toggle("dark", appSettings.theme === "dark");
    document.body.classList.toggle("compact-messages", appSettings.compactMessages);
}

function updateSetting(key, value) {
    appSettings = { ...appSettings, [key]: value };
    persistSettings();
    applySettings();
}

function openSettings() {
    syncSettingsControls();
    overlay.classList.add("show");
    settingsPanel.classList.add("show");
    settingsPanel.querySelector("select, input, button")?.focus();
}

function updateChatControls() {
    const hasActiveChat = Boolean(currentChatId);
    deleteChatBtn.disabled = !hasActiveChat;
    shareChatBtn.disabled = !hasActiveChat;
    pinChatBtn.disabled = !hasActiveChat || currentChatState.is_archived;
    archiveChatBtn.disabled = !hasActiveChat;
    pinChatBtn.title = currentChatState.is_pinned ? "Unpin chat" : "Pin chat";
    pinChatBtn.setAttribute("aria-label", pinChatBtn.title);
    archiveChatBtn.title = currentChatState.is_archived ? "Restore chat" : "Archive chat";
    archiveChatBtn.setAttribute("aria-label", archiveChatBtn.title);
}

function openSearch() {
    renderSearchResults("");
    overlay.classList.add("show");
    searchModal.classList.add("show");
    globalSearch.value = "";
    globalSearch.focus();
}

function autoGrowComposer() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
}

function createIcon(name) {
    const icon = document.createElement("i");
    icon.setAttribute("data-lucide", name);
    return icon;
}

function createActionButton(label, iconName, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.appendChild(createIcon(iconName));
    if (onClick) {
        button.addEventListener("click", onClick);
    }
    return button;
}

function appendInlineMarkdown(parent, text) {
    const source = String(text || "");
    const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*\s][^*]*\*|_[^_\s][^_]*_|\[[^\]]+\]\((https?:\/\/[^)\s]+)\))/g;
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(source)) !== null) {
        if (match.index > lastIndex) {
            parent.appendChild(document.createTextNode(source.slice(lastIndex, match.index)));
        }

        const token = match[0];
        if (token.startsWith("`")) {
            const code = document.createElement("code");
            code.textContent = token.slice(1, -1);
            parent.appendChild(code);
        } else if (token.startsWith("**") || token.startsWith("__")) {
            const strong = document.createElement("strong");
            appendInlineMarkdown(strong, token.slice(2, -2));
            parent.appendChild(strong);
        } else if (token.startsWith("*") || token.startsWith("_")) {
            const emphasis = document.createElement("em");
            appendInlineMarkdown(emphasis, token.slice(1, -1));
            parent.appendChild(emphasis);
        } else {
            const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
            if (linkMatch) {
                const link = document.createElement("a");
                link.href = linkMatch[2];
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                appendInlineMarkdown(link, linkMatch[1]);
                parent.appendChild(link);
            }
        }

        lastIndex = pattern.lastIndex;
    }

    if (lastIndex < source.length) {
        parent.appendChild(document.createTextNode(source.slice(lastIndex)));
    }
}

function splitTableRow(line) {
    return line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim());
}

function isTableDivider(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || "");
}

function isListLine(line) {
    return /^\s*([-*+]\s+|\d+\.\s+)/.test(line || "");
}

function flushParagraph(container, paragraphLines) {
    if (!paragraphLines.length) {
        return;
    }

    const p = document.createElement("p");
    appendInlineMarkdown(p, paragraphLines.join(" ").trim());
    container.appendChild(p);
    paragraphLines.length = 0;
}

function renderHeading(container, line) {
    const match = line.match(/^(#{1,4})\s+(.+)$/);
    if (!match) {
        return false;
    }

    const heading = document.createElement(`h${match[1].length + 2}`);
    appendInlineMarkdown(heading, match[2].replace(/\s+#+$/, ""));
    container.appendChild(heading);
    return true;
}

function renderBlockquote(container, lines) {
    const quote = document.createElement("blockquote");
    const cleaned = lines.map((line) => line.replace(/^\s*>\s?/, ""));
    renderMarkdown(quote, cleaned.join("\n"));
    container.appendChild(quote);
}

function renderList(container, lines) {
    const firstMatch = lines[0].match(/^\s*(\d+\.|[-*+])\s+/);
    const ordered = Boolean(firstMatch && /\d+\./.test(firstMatch[1]));
    const list = document.createElement(ordered ? "ol" : "ul");
    const stack = [{ indent: -1, list }];

    lines.forEach((line) => {
        const match = line.match(/^(\s*)(\d+\.|[-*+])\s+(.+)$/);
        if (!match) {
            return;
        }

        const indent = Math.floor(match[1].replace(/\t/g, "    ").length / 2);
        const marker = match[2];
        const orderedItem = /\d+\./.test(marker);

        while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
            stack.pop();
        }

        let current = stack[stack.length - 1].list;
        if (indent > stack[stack.length - 1].indent + 1) {
            const lastItem = current.lastElementChild;
            if (lastItem) {
                const nested = document.createElement(orderedItem ? "ol" : "ul");
                lastItem.appendChild(nested);
                stack.push({ indent, list: nested });
                current = nested;
            }
        }

        const item = document.createElement("li");
        appendInlineMarkdown(item, match[3]);
        current.appendChild(item);
    });

    container.appendChild(list);
}

function renderTable(container, lines) {
    const table = document.createElement("table");
    const [headerLine, , ...bodyLines] = lines;
    const headers = splitTableRow(headerLine);

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((header) => {
        const th = document.createElement("th");
        appendInlineMarkdown(th, header);
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    bodyLines.forEach((line) => {
        const row = document.createElement("tr");
        splitTableRow(line).forEach((cell) => {
            const td = document.createElement("td");
            appendInlineMarkdown(td, cell);
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    wrap.appendChild(table);
    container.appendChild(wrap);
}

function renderCodeBlock(container, code, language) {
    const block = document.createElement("div");
    block.className = "code-block";

    const header = document.createElement("div");
    header.className = "code-header";

    const label = document.createElement("span");
    label.textContent = language || "text";
    header.appendChild(label);

    header.appendChild(createActionButton("Copy code", "copy", () => {
        navigator.clipboard?.writeText(code);
        showToast("Code copied");
    }));

    const pre = document.createElement("pre");
    const codeNode = document.createElement("code");
    codeNode.textContent = code;
    pre.appendChild(codeNode);

    block.appendChild(header);
    block.appendChild(pre);
    container.appendChild(block);
}

function renderMarkdown(container, text) {
    const lines = String(text || "").split("\n");
    const paragraphLines = [];
    let index = 0;

    while (index < lines.length) {
        const line = lines[index];
        const trimmed = line.trim();

        if (!trimmed) {
            flushParagraph(container, paragraphLines);
            index += 1;
            continue;
        }

        if (/^---+$|^\*\*\*+$|^___+$/.test(trimmed)) {
            flushParagraph(container, paragraphLines);
            container.appendChild(document.createElement("hr"));
            index += 1;
            continue;
        }

        if (trimmed.startsWith("```")) {
            flushParagraph(container, paragraphLines);
            const language = trimmed.slice(3).trim();
            const codeLines = [];
            index += 1;

            while (index < lines.length && !lines[index].trim().startsWith("```")) {
                codeLines.push(lines[index]);
                index += 1;
            }

            renderCodeBlock(container, codeLines.join("\n"), language);
            index += 1;
            continue;
        }

        if (trimmed.includes("|") && isTableDivider(lines[index + 1])) {
            flushParagraph(container, paragraphLines);
            const tableLines = [trimmed, lines[index + 1].trim()];
            index += 2;

            while (index < lines.length && lines[index].trim().includes("|")) {
                tableLines.push(lines[index].trim());
                index += 1;
            }

            renderTable(container, tableLines);
            continue;
        }

        if (/^\s*>\s?/.test(line)) {
            flushParagraph(container, paragraphLines);
            const quoteLines = [];

            while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
                quoteLines.push(lines[index]);
                index += 1;
            }

            renderBlockquote(container, quoteLines);
            continue;
        }

        if (isListLine(line)) {
            flushParagraph(container, paragraphLines);
            const listLines = [];

            while (index < lines.length && isListLine(lines[index])) {
                listLines.push(lines[index]);
                index += 1;
            }

            renderList(container, listLines);
            continue;
        }

        if (/^#{1,4}\s+/.test(trimmed)) {
            flushParagraph(container, paragraphLines);
            renderHeading(container, trimmed);
            index += 1;
            continue;
        }

        paragraphLines.push(trimmed);
        index += 1;
    }

    flushParagraph(container, paragraphLines);
}

function addUserMessage(text) {
    const message = document.createElement("article");
    message.className = "message user-message";

    const bubble = document.createElement("div");
    bubble.className = "user-bubble";
    bubble.textContent = text;

    message.appendChild(bubble);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addAIMessage(answer, sources = [], question = null) {
    const message = document.createElement("article");
    message.className = "message assistant-message";

    const avatar = document.createElement("div");
    avatar.className = "assistant-avatar";
    avatar.appendChild(createIcon("sparkles"));

    const content = document.createElement("div");
    content.className = "message-content";
    renderMarkdown(content, answer);

    if (sources.length > 0) {
        const sourceWrap = document.createElement("div");
        sourceWrap.className = "sources";

        sources.forEach((source) => {
            const badge = document.createElement("span");
            badge.className = "citation-badge";
            badge.appendChild(createIcon("file-text"));
            badge.appendChild(document.createTextNode(source));
            sourceWrap.appendChild(badge);
        });

        content.appendChild(sourceWrap);
    }

    const actions = document.createElement("div");
    actions.className = "message-actions";
    actions.appendChild(createActionButton("Copy answer", "copy", () => {
        navigator.clipboard?.writeText(String(answer || ""));
        showToast("Answer copied");
    }));
    actions.appendChild(createActionButton("Retry", "refresh-cw", () => {
        if (question) {
            sendQuestion(question, false);
        }
    }));
    actions.appendChild(createActionButton("Helpful", "thumbs-up", () => saveFeedback(answer, "up", actions)));
    actions.appendChild(createActionButton("Not helpful", "thumbs-down", () => saveFeedback(answer, "down", actions)));
    content.appendChild(actions);

    message.appendChild(avatar);
    message.appendChild(content);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
    refreshIcons();
}

async function saveFeedback(answer, rating, actions) {
    if (!currentChatId) {
        showToast("Open a chat before sending feedback.");
        return;
    }

    try {
        const response = await fetch("/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: currentChatId, answer, rating })
        });

        if (!response.ok) {
            throw new Error("Feedback was not saved.");
        }

        actions.querySelectorAll("button").forEach((button) => {
            button.classList.toggle("selected", button.title === (rating === "up" ? "Helpful" : "Not helpful"));
        });
        showToast("Feedback saved");
    } catch (error) {
        showToast("Could not save feedback.");
    }
}

function addTypingIndicator() {
    const message = document.createElement("article");
    message.className = "message assistant-message";
    message.id = "loading";

    const avatar = document.createElement("div");
    avatar.className = "assistant-avatar";
    avatar.appendChild(createIcon("sparkles"));

    const content = document.createElement("div");
    content.className = "message-content";

    const typing = document.createElement("div");
    typing.className = "typing";
    typing.appendChild(document.createTextNode("Thinking"));
    typing.appendChild(document.createElement("span"));
    typing.appendChild(document.createElement("span"));
    typing.appendChild(document.createElement("span"));

    content.appendChild(typing);
    message.appendChild(avatar);
    message.appendChild(content);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
    refreshIcons();
    return message;
}

function highlightChat(chatId) {
    document.querySelectorAll(".chat-item").forEach((item) => {
        item.classList.toggle("active", item.dataset.id === chatId);
    });
}

function createChatItem(chat) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "chat-item";
    item.dataset.id = chat.chat_id;
    item.appendChild(createIcon("file-text"));

    const title = document.createElement("span");
    title.textContent = chat.title || chat.filename || "Untitled chat";
    item.appendChild(title);

    if (chat.is_pinned) {
        const pinned = createIcon("pin");
        pinned.classList.add("chat-status-icon");
        item.appendChild(pinned);
    }

    item.addEventListener("click", () => openChat(chat.chat_id));
    return item;
}

function setHistoryView(view) {
    activeHistoryView = view;
    const labels = { recent: "Recent Chats", pinned: "Pinned", archived: "Archived" };
    historyLabel.textContent = labels[view];
    recentChatsBtn.classList.toggle("active", view === "recent");
    pinnedChatsBtn.classList.toggle("active", view === "pinned");
    archivedChatsBtn.classList.toggle("active", view === "archived");
    loadHistory();
}

async function loadHistory() {
    try {
        const response = await fetch(`/history?view=${activeHistoryView}`);
        chatsCache = await response.json();
        historyBox.textContent = "";

        if (!chatsCache.length) {
            const empty = document.createElement("div");
            empty.className = "empty-state";
            empty.textContent = "No recent chats yet.";
            historyBox.appendChild(empty);
            return;
        }

        chatsCache.forEach((chat) => historyBox.appendChild(createChatItem(chat)));
        highlightChat(currentChatId);
        refreshIcons();
    } catch (error) {
        showToast("Could not load recent chats.");
    }
}

function renderSearchResults(query) {
    const normalized = query.trim().toLowerCase();
    const matches = chatsCache.filter((chat) => {
        const title = `${chat.title || ""} ${chat.filename || ""}`.toLowerCase();
        return title.includes(normalized);
    });

    searchResults.textContent = "";

    if (!matches.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No conversations found.";
        searchResults.appendChild(empty);
        return;
    }

    matches.forEach((chat) => {
        const item = createChatItem(chat);
        item.addEventListener("click", closeOverlaySurfaces);
        searchResults.appendChild(item);
    });

    refreshIcons();
}

async function openChat(chatId) {
    try {
        const response = await fetch(`/chat/${chatId}`);
        const data = await response.json();

        if (!response.ok || data.status === "error") {
            showToast(data.message || "Chat not found.");
            return;
        }

        currentChatId = chatId;
        currentChatState = { is_pinned: data.is_pinned, is_archived: data.is_archived };
        updateChatControls();
        highlightChat(chatId);
        setView("chat");
        closeOverlaySurfaces();
        chatTitle.textContent = data.title || "Document chat";
        chatBox.textContent = "";

        const msgRes = await fetch(`/messages/${chatId}`);
        const messages = await msgRes.json();

        messages.forEach((msg) => {
            if (msg.role === "user") {
                addUserMessage(msg.content);
            } else {
                addAIMessage(msg.content, []);
            }
        });
    } catch (error) {
        showToast("Could not open this chat.");
    }
}

async function uploadFile() {
    const file = fileInput.files[0];

    if (!file) {
        showToast("Select a TXT or PDF file first.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    showToast("Indexing document...");

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (data.status === "success") {
            currentChatId = data.chat_id || null;
            currentChatState = { is_pinned: false, is_archived: false };
            updateChatControls();
            setView("chat");
            chatTitle.textContent = file.name;
            chatBox.textContent = "";
            addAIMessage(`I indexed ${file.name}. Ask me anything from the document.`, []);
            await loadHistory();
            highlightChat(currentChatId);
            showToast("Document ready");
            return;
        }

        showToast(data.message || "Upload failed.");
    } catch (error) {
        showToast("Upload failed. Please try again.");
    }
}

async function sendQuestion(question = input.value.trim(), showUserMessage = true) {

    if (!question) {
        return;
    }

    setView("chat");
    if (showUserMessage) {
        addUserMessage(question);
        input.value = "";
        autoGrowComposer();
    }

    const loading = addTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });
        const data = await response.json();

        loading.remove();

        if (!response.ok || data.status === "error") {
            addAIMessage(data.message || "I could not answer that yet. Upload a document first.", []);
            return;
        }

        addAIMessage(data.answer || data.message, data.sources || [], question);
    } catch (error) {
        loading.remove();
        addAIMessage("Something went wrong while generating the answer.", []);
    }
}

newChatBtn.addEventListener("click", async () => {
    try {
        await fetch("/new_chat", { method: "POST" });
    } catch (error) {
        showToast("Starting a local draft chat.");
    }

    currentChatId = null;
    currentChatState = { is_pinned: false, is_archived: false };
    updateChatControls();
    chatTitle.textContent = "Start with a document";
    chatBox.textContent = "";
    fileInput.value = "";
    fileLabel.textContent = "Drop a TXT or PDF file or browse";
    setView("upload");
    highlightChat(null);
    closeOverlaySurfaces();
});

async function deleteCurrentChat() {
    if (!currentChatId) {
        return;
    }

    const chatId = currentChatId;
    try {
        const response = await fetch("/delete_chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId })
        });
        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            throw new Error(data.message || "Delete failed.");
        }

        currentChatId = null;
        currentChatState = { is_pinned: false, is_archived: false };
        chatTitle.textContent = "Start with a document";
        chatBox.textContent = "";
        fileInput.value = "";
        fileLabel.textContent = "Drop a TXT or PDF file or browse";
        setView("upload");
        updateChatControls();
        await loadHistory();
        showToast("Chat deleted");
    } catch (error) {
        showToast(error.message || "Could not delete this chat.");
    }
}

async function shareCurrentChat() {
    if (!currentChatId) {
        return;
    }

    const url = new URL(window.location.href);
    url.searchParams.set("chat", currentChatId);
    const shareData = { title: chatTitle.textContent, text: `DocMind chat: ${chatTitle.textContent}`, url: url.toString() };

    try {
        if (navigator.share) {
            await navigator.share(shareData);
        } else {
            await navigator.clipboard.writeText(shareData.url);
            showToast("Chat link copied");
        }
    } catch (error) {
        if (error.name !== "AbortError") {
            showToast("Could not share this chat.");
        }
    }
}

async function updateCurrentChatStatus(action) {
    if (!currentChatId) {
        return;
    }

    try {
        const response = await fetch("/chat_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: currentChatId, action })
        });
        const data = await response.json();
        if (!response.ok || data.status !== "success") {
            throw new Error(data.message || "Could not update chat status.");
        }

        if (action === "archive") {
            currentChatId = null;
            currentChatState = { is_pinned: false, is_archived: false };
            chatTitle.textContent = "Start with a document";
            chatBox.textContent = "";
            setView("upload");
            updateChatControls();
            setHistoryView("recent");
            showToast("Chat archived");
            return;
        }

        if (action === "unarchive") {
            currentChatState.is_archived = false;
            setHistoryView("recent");
            showToast("Chat restored");
        } else {
            currentChatState.is_pinned = action === "pin";
            await loadHistory();
            showToast(action === "pin" ? "Chat pinned" : "Chat unpinned");
        }
        updateChatControls();
    } catch (error) {
        showToast(error.message || "Could not update chat status.");
    }
}

composerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendQuestion();
});

input.addEventListener("input", autoGrowComposer);

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
});

fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    fileLabel.textContent = file ? file.name : "Drop a TXT or PDF file or browse";
});

["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
    });
});

dropZone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer.files;

    if (!file) {
        return;
    }

    if (!/\.(txt|pdf)$/i.test(file.name)) {
        showToast("Only TXT and PDF files are supported.");
        return;
    }

    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    fileLabel.textContent = file.name;
});

document.querySelectorAll(".prompt-card").forEach((card) => {
    card.addEventListener("click", () => {
        input.value = card.dataset.prompt || "";
        autoGrowComposer();
        input.focus();
    });
});

menuButton.addEventListener("click", () => {
    sidebar.classList.add("open");
    overlay.classList.add("show");
});

overlay.addEventListener("click", closeOverlaySurfaces);
searchTrigger.addEventListener("click", openSearch);
globalSearch.addEventListener("input", () => renderSearchResults(globalSearch.value));

document.addEventListener("keydown", (event) => {
    const isSearchShortcut = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";

    if (isSearchShortcut) {
        event.preventDefault();
        openSearch();
    }

    if (event.key === "Escape") {
        closeOverlaySurfaces();
    }
});

themeToggle.addEventListener("click", () => {
    updateSetting("theme", document.body.classList.contains("dark") ? "light" : "dark");
    syncSettingsControls();
});

deleteChatBtn.addEventListener("click", () => deleteChatDialog.showModal());
deleteChatDialog.addEventListener("close", () => {
    if (deleteChatDialog.returnValue === "confirm") {
        deleteCurrentChat();
    }
});
shareChatBtn.addEventListener("click", shareCurrentChat);
pinChatBtn.addEventListener("click", () => updateCurrentChatStatus(currentChatState.is_pinned ? "unpin" : "pin"));
archiveChatBtn.addEventListener("click", () => updateCurrentChatStatus(currentChatState.is_archived ? "unarchive" : "archive"));
attachFileBtn.addEventListener("click", () => fileInput.click());

voiceInputBtn.addEventListener("click", () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("Voice input is not supported in this browser.");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language || "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
        input.value = `${input.value}${input.value ? " " : ""}${event.results[0][0].transcript}`;
        autoGrowComposer();
        input.focus();
    };
    recognition.onerror = () => showToast("Voice input could not start.");
    recognition.start();
});

pinnedChatsBtn.addEventListener("click", () => setHistoryView("pinned"));
archivedChatsBtn.addEventListener("click", () => setHistoryView("archived"));
recentChatsBtn.addEventListener("click", () => setHistoryView("recent"));
settingsBtn.addEventListener("click", openSettings);
closeSettingsBtn.addEventListener("click", closeOverlaySurfaces);
saveSettingsBtn.addEventListener("click", closeOverlaySurfaces);
themeSetting.addEventListener("change", () => updateSetting("theme", themeSetting.value));
compactMessagesSetting.addEventListener("change", () => updateSetting("compactMessages", compactMessagesSetting.checked));
openSharedChatsSetting.addEventListener("change", () => updateSetting("openSharedChats", openSharedChatsSetting.checked));
resetSettingsBtn.addEventListener("click", () => {
    appSettings = { ...defaultSettings };
    persistSettings();
    applySettings();
    syncSettingsControls();
    showToast("Settings reset");
});

appSettings = readSettings();
if (localStorage.getItem("docmind-theme") === "dark") {
    appSettings.theme = "dark";
    localStorage.removeItem("docmind-theme");
    persistSettings();
}
applySettings();
syncSettingsControls();

window.uploadFile = uploadFile;
window.sendQuestion = sendQuestion;

setView("upload");
updateChatControls();
loadHistory().then(async () => {
    const chatId = new URLSearchParams(window.location.search).get("chat");
    if (chatId && appSettings.openSharedChats) {
        await openChat(chatId);
    }
    refreshIcons();
});
refreshIcons();

// ─── Authentication ───

const authOverlay = document.getElementById("authOverlay");
const authModal = document.getElementById("authModal");
const authCloseBtn = document.getElementById("authCloseBtn");
const authTitle = document.getElementById("authTitle");
const authSubtitle = document.getElementById("authSubtitle");
const loginTab = document.getElementById("loginTab");
const signupTab = document.getElementById("signupTab");
const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");
const authError = document.getElementById("authError");
const authSuccess = document.getElementById("authSuccess");
const accountBtn = document.getElementById("accountBtn");
const profileBtn = document.getElementById("profileBtn");
const profileMenu = document.getElementById("profileMenu");
const profileLogoutBtn = document.getElementById("profileLogoutBtn");
const menuAvatar = document.getElementById("menuAvatar");
const menuUserName = document.getElementById("menuUserName");
const menuUserEmail = document.getElementById("menuUserEmail");
const userAvatar = document.getElementById("userAvatar");
const userName = document.getElementById("userName");
const userEmail = document.getElementById("userEmail");

let isLoggedIn = false;

function openAuthModal(tab = "login") {
    clearAuthMessages();
    switchAuthTab(tab);
    authOverlay.classList.add("show");
    authModal.classList.add("show");
    const firstInput = (tab === "login" ? loginForm : signupForm).querySelector("input");
    setTimeout(() => firstInput?.focus(), 300);
}

function closeAuthModal() {
    authOverlay.classList.remove("show");
    authModal.classList.remove("show");
    clearAuthMessages();
}

function switchAuthTab(tab) {
    loginTab.classList.toggle("active", tab === "login");
    signupTab.classList.toggle("active", tab === "signup");
    loginForm.style.display = tab === "login" ? "grid" : "none";
    signupForm.style.display = tab === "signup" ? "grid" : "none";
    authTitle.textContent = tab === "login" ? "Welcome back" : "Create an account";
    authSubtitle.textContent = tab === "login"
        ? "Sign in to continue to your workspace"
        : "Get started with DocMind AI";
    clearAuthMessages();
}

function showAuthError(message) {
    authError.textContent = message;
    authError.classList.add("show");
    authSuccess.classList.remove("show");
}

function showAuthSuccess(message) {
    authSuccess.textContent = message;
    authSuccess.classList.add("show");
    authError.classList.remove("show");
}

function clearAuthMessages() {
    authError.textContent = "";
    authError.classList.remove("show");
    authSuccess.textContent = "";
    authSuccess.classList.remove("show");
}

function updateAuthUI(user) {
    if (user) {
        isLoggedIn = true;
        const initial = (user.username || "U")[0].toUpperCase();
        userAvatar.textContent = initial;
        profileBtn.textContent = initial;
        menuAvatar.textContent = initial;
        userName.textContent = user.username;
        userEmail.textContent = user.email;
        menuUserName.textContent = user.username;
        menuUserEmail.textContent = user.email;
    } else {
        isLoggedIn = false;
        userAvatar.textContent = "?";
        profileBtn.textContent = "?";
        menuAvatar.textContent = "?";
        userName.textContent = "Guest";
        userEmail.textContent = "Not signed in";
        menuUserName.textContent = "Guest";
        menuUserEmail.textContent = "Not signed in";
        profileMenu.classList.remove("show");
    }
}

function toggleProfileMenu(anchor) {
    if (!isLoggedIn) {
        openAuthModal("login");
        return;
    }

    const wasOpen = profileMenu.classList.contains("show");
    closeOverlaySurfaces();

    if (wasOpen) {
        return;
    }

    const rect = anchor.getBoundingClientRect();
    const menuWidth = 260;
    const menuHeight = 140;
    profileMenu.style.left = `${Math.max(16, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - 16))}px`;
    profileMenu.style.top = `${Math.max(16, Math.min(rect.bottom + 10, window.innerHeight - menuHeight - 16))}px`;
    profileMenu.classList.add("show");
    refreshIcons();
}

async function checkAuth() {
    try {
        const response = await fetch("/me");
        const data = await response.json();
        if (data.logged_in) {
            updateAuthUI(data.user);
        } else {
            updateAuthUI(null);
            openAuthModal("login");
        }
    } catch {
        updateAuthUI(null);
    }
}

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthMessages();
    const identifier = document.getElementById("loginIdentifier").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!identifier || !password) {
        showAuthError("Please fill in all fields.");
        return;
    }

    const submitBtn = loginForm.querySelector(".auth-submit");
    submitBtn.disabled = true;

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier, password })
        });
        const data = await response.json();

        if (response.ok && data.status === "success") {
            updateAuthUI(data.user);
            closeAuthModal();
            loginForm.reset();
            showToast(`Welcome back, ${data.user.username}!`);
            await loadHistory();
        } else {
            showAuthError(data.message || "Login failed.");
        }
    } catch {
        showAuthError("Could not connect. Please try again.");
    } finally {
        submitBtn.disabled = false;
    }
});

signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthMessages();
    const username = document.getElementById("signupUsername").value.trim();
    const email = document.getElementById("signupEmail").value.trim();
    const password = document.getElementById("signupPassword").value;
    const confirm = document.getElementById("signupConfirm").value;

    if (!username || !email || !password || !confirm) {
        showAuthError("Please fill in all fields.");
        return;
    }

    if (password !== confirm) {
        showAuthError("Passwords do not match.");
        return;
    }

    if (password.length < 6) {
        showAuthError("Password must be at least 6 characters.");
        return;
    }

    const submitBtn = signupForm.querySelector(".auth-submit");
    submitBtn.disabled = true;

    try {
        const response = await fetch("/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password })
        });
        const data = await response.json();

        if (response.ok && data.status === "success") {
            updateAuthUI(data.user);
            closeAuthModal();
            signupForm.reset();
            showToast(`Welcome, ${data.user.username}!`);
            await loadHistory();
        } else {
            showAuthError(data.message || "Signup failed.");
        }
    } catch {
        showAuthError("Could not connect. Please try again.");
    } finally {
        submitBtn.disabled = false;
    }
});

async function logout() {
    try {
        await fetch("/logout", { method: "POST" });
    } catch {}
    updateAuthUI(null);
    currentChatId = null;
    currentChatState = { is_pinned: false, is_archived: false };
    updateChatControls();
    chatTitle.textContent = "Start with a document";
    chatBox.textContent = "";
    historyBox.textContent = "";
    setView("upload");
    showToast("Signed out");
    openAuthModal("login");
}

loginTab.addEventListener("click", () => switchAuthTab("login"));
signupTab.addEventListener("click", () => switchAuthTab("signup"));
authCloseBtn.addEventListener("click", closeAuthModal);
authOverlay.addEventListener("click", closeAuthModal);

accountBtn.addEventListener("click", () => {
    toggleProfileMenu(accountBtn);
});

profileBtn.addEventListener("click", () => {
    toggleProfileMenu(profileBtn);
});

profileLogoutBtn.addEventListener("click", logout);

document.addEventListener("click", (event) => {
    if (
        profileMenu.classList.contains("show") &&
        !profileMenu.contains(event.target) &&
        !accountBtn.contains(event.target) &&
        !profileBtn.contains(event.target)
    ) {
        profileMenu.classList.remove("show");
    }
});

// Intercept fetch to catch 401s globally
const originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    if (response.status === 401) {
        const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
        if (!['/login', '/signup', '/me'].some(p => url.includes(p))) {
            updateAuthUI(null);
            openAuthModal("login");
            showToast("Please sign in to continue.");
        }
    }
    return response;
};

// Check auth on page load
checkAuth();
