// ============================================
// Shital Academy Chatbot
// script.js
// ============================================

// ---------- DOM ----------
const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

const typingIndicator = document.getElementById("typingIndicator");

const leadModal = document.getElementById("leadModal");
const leadForm = document.getElementById("leadForm");

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const mobileInput = document.getElementById("mobile");

// ---------- State ----------
let waitingForResponse = false;
let chatEnded = false;

let sessionId = null;

// Always start with the modal hidden
leadModal.classList.add("hidden");

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

// ============================================
// Message UI
// ============================================

function addMessage(text, sender) {

    const message = document.createElement("div");
    message.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = sender === "bot" ? "🤖" : "👤";

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

        const response = await fetch("/chat", {

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

        addMessage(data.reply, "bot");

        if (data.trigger_lead_form) {
            leadModal.classList.remove("hidden");
        }

        if (data.end_session) {

            chatEnded = true;

            messageInput.disabled = true;
            sendButton.disabled = true;

            return;
        }

        enableInput();

    }
    catch (err) {

        hideTyping();

        console.error(err);

        addMessage(
            "⚠️ Unable to connect to the server. Please try again.",
            "bot"
        );

        enableInput();

    }

}

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

    try {

        const response = await fetch("/lead", {

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

        alert("Unable to save your details.");

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