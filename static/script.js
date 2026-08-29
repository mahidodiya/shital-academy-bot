// ============================================
// Shital Academy Chatbot
// script.js
// ============================================

// ---------- DOM ----------
const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const newChatButton = document.getElementById("newChatButton");

const typingIndicator = document.getElementById("typingIndicator");

const leadModal = document.getElementById("leadModal");
const leadForm = document.getElementById("leadForm");
const leadSubmitButton = document.getElementById("leadSubmitButton");

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const mobileInput = document.getElementById("mobile");

// ---------- Config ----------
const API_BASE_URL = "https://shital-academy-assistant.onrender.com";
const REQUEST_TIMEOUT_MS = 20000;

// ---------- State ----------
let waitingForResponse = false;
let chatEnded = false;

let sessionId = null;

// Always start with the modal hidden and the "new chat" control hidden
leadModal.classList.add("hidden");
newChatButton.classList.add("hidden");

// ============================================
// Helpers
// ============================================

function currentTime() {
    return new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });
}

function scrollBottom() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
    typingIndicator.classList.remove("hidden");
    scrollBottom();
}

function hideTyping() {
    typingIndicator.classList.add("hidden");
}

function escapeHTML(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    waitingForResponse = false;
    messageInput.focus();
}

function disableInput() {
    messageInput.disabled = true;
    sendButton.disabled = true;
    waitingForResponse = true;
}

// A fetch with a hard timeout, so a stalled connection doesn't leave
// the typing indicator (or the lead form) hanging forever.
async function fetchWithTimeout(url, options = {}) {

    const controller = new AbortController();

    const timeoutId = setTimeout(
        () => controller.abort(),
        REQUEST_TIMEOUT_MS
    );

    try {

        return await fetch(url, {
            ...options,
            signal: controller.signal
        });

    } finally {

        clearTimeout(timeoutId);

    }

}

// ============================================
// Message UI
// ============================================

function addMessage(text, sender) {

    const message = document.createElement("div");
    message.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";

    if (sender === "bot") {
        avatar.innerHTML = '<img src="templates/bot.jpg" alt="Bot">';
    } else {
        avatar.innerHTML = "👤";
    }

    const content = document.createElement("div");
    content.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = escapeHTML(text).replace(/\n/g, "<br>");

    const time = document.createElement("span");
    time.className = "time";
    time.innerText = currentTime();

    content.appendChild(bubble);
    content.appendChild(time);

    message.appendChild(avatar);
    message.appendChild(content);

    chatBox.appendChild(message);

    scrollBottom();
}

// ============================================
// Send Message
// ============================================

async function sendMessage() {

    if (chatEnded) return;

    const message = messageInput.value.trim();

    if (!message) return;

    if (waitingForResponse) return;

    addMessage(message, "user");

    messageInput.value = "";
    messageInput.style.height = "52px";

    disableInput();

    showTyping();

    try {

        const response = await fetchWithTimeout(
            `${API_BASE_URL}/chat`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })

            });

        hideTyping();

        if (!response.ok) {
            throw new Error("Server Error");
        }

        const data = await response.json();
        sessionId = data.session_id;

        // NOTE: the backend returns the bot's reply under the
        // "response" key (see chatbot.py / main.py), not "reply".
        addMessage(data.response, "bot");

        if (data.trigger_lead_form) {
            leadModal.classList.remove("hidden");
            nameInput.focus();
        }

        if (data.end_session) {

            chatEnded = true;

            messageInput.disabled = true;
            sendButton.disabled = true;

            newChatButton.classList.remove("hidden");
            newChatButton.focus();

            return;
        }

        enableInput();

    }
    catch (err) {

        hideTyping();

        console.error(err);

        const timedOut = err.name === "AbortError";

        addMessage(
            timedOut
                ? "⚠️ The server took too long to respond. Please try again."
                : "⚠️ Unable to connect to the server. Please try again.",
            "bot"
        );

        enableInput();

    }

}

// ============================================
// New Chat
// ============================================

function startNewChat() {

    sessionId = null;
    chatEnded = false;

    // Remove every message except the original welcome message
    // (it's always the first child of the chat box).
    while (chatBox.children.length > 1) {
        chatBox.removeChild(chatBox.lastChild);
    }

    leadModal.classList.add("hidden");
    leadForm.reset();

    newChatButton.classList.add("hidden");

    enableInput();

    scrollBottom();

}

newChatButton.addEventListener("click", startNewChat);

// ============================================
// Lead Form
// ============================================

leadForm.addEventListener("submit", async function (e) {

    e.preventDefault();

    const payload = {

        session_id: sessionId,

        name: nameInput.value.trim(),

        email: emailInput.value.trim(),

        mobile: mobileInput.value.trim()

    };

    leadSubmitButton.disabled = true;
    leadSubmitButton.innerText = "Saving...";

    try {

        const response = await fetchWithTimeout(
            `${API_BASE_URL}/lead`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(payload)

            });

        const result = await response.json();

        if (!response.ok) {

            alert(result.detail || "Invalid details.");

            return;

        }

        leadModal.classList.add("hidden");

        leadForm.reset();

        addMessage(
            "✅ Thank you! Your details have been saved successfully.",
            "bot"
        );

        messageInput.focus();

    }

    catch (err) {

        console.error(err);

        const timedOut = err.name === "AbortError";

        alert(
            timedOut
                ? "The server took too long to respond. Please try again."
                : "Unable to save your details."
        );

    }

    finally {

        leadSubmitButton.disabled = false;
        leadSubmitButton.innerText = "Continue Chat";

    }

});

// ============================================
// Auto Resize Textarea
// ============================================

messageInput.addEventListener("input", function () {

    this.style.height = "auto";

    this.style.height = this.scrollHeight + "px";

});

// ============================================
// Send Button
// ============================================

sendButton.addEventListener("click", sendMessage);

// ============================================
// Enter Key
// ============================================

messageInput.addEventListener("keydown", function (e) {

    if (
        e.key === "Enter" &&
        !e.shiftKey
    ) {

        e.preventDefault();

        sendMessage();

    }

});

// ============================================
// Focus
// ============================================

messageInput.focus();