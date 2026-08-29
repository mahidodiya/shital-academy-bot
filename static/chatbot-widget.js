(function () {
    "use strict";

    // ============================================
    // Shital Academy Chatbot Widget
    // ============================================

    const CHATBOT_URL =
        "https://shital-academy-assistant.onrender.com/";

    // Prevent duplicate initialization
    if (document.getElementById("shital-academy-chatbot-widget")) {
        return;
    }

    // ============================================
    // CSS
    // ============================================

    const style = document.createElement("style");

    style.textContent = `
        #shital-academy-chatbot-widget {
            position: fixed;
            right: 24px;
            bottom: 24px;
            z-index: 2147483647;
            font-family: Arial, sans-serif;
        }

        #shital-chatbot-button {
            width: 64px;
            height: 64px;
            border: none;
            border-radius: 50%;
            background: #2563eb;
            color: white;
            font-size: 28px;
            cursor: pointer;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s ease,
                        box-shadow 0.2s ease;
        }

        #shital-chatbot-button img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 50%;
}
        #shital-chatbot-button:hover {
            transform: scale(1.06);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        #shital-chatbot-window {
    position: fixed;
    right: 24px;
    bottom: 90px;

    width: 360px;
    height: 550px;

    border: none;
    border-radius: 18px;

    background: white;

    box-shadow:
        0 15px 50px rgba(0, 0, 0, 0.25);

    display: none;

    overflow: hidden;
}

        #shital-chatbot-window.shital-chatbot-open {
            display: block;
        }

        @media (max-width: 768px) {

            #shital-academy-chatbot-widget {
                right: 16px;
                bottom: 16px;
            }

            #shital-chatbot-button {
                width: 58px;
                height: 58px;
                font-size: 25px;
            }

            #shital-chatbot-window {
                top: 10px;
                left: 10px;
                right: 10px;
                bottom: 10px;

                width: auto;
                height: auto;

                border-radius: 14px;
            }
        }
    `;

    document.head.appendChild(style);

    // ============================================
    // Widget Container
    // ============================================

    const widget = document.createElement("div");

    widget.id = "shital-academy-chatbot-widget";

    // ============================================
    // Chat Button
    // ============================================

    const button = document.createElement("button");

    button.id = "shital-chatbot-button";
    button.type = "button";
    button.innerHTML = '<img src="templates/bot.jpg" alt="Bot">';
    button.setAttribute(
        "aria-label",
        "Open Shital Academy AI Assistant"
    );

    button.setAttribute(
        "title",
        "Chat with Shital Academy AI Assistant"
    );

    // ============================================
    // Chat Window
    // ============================================

    const iframe = document.createElement("iframe");

    iframe.id = "shital-chatbot-window";

    iframe.src = CHATBOT_URL;

    iframe.title = "Shital Academy AI Assistant";

    iframe.setAttribute(
        "allow",
        "clipboard-write"
    );

    iframe.setAttribute(
        "loading",
        "lazy"
    );

    // ============================================
    // Open / Close
    // ============================================

    let isOpen = false;

    function openChatbot() {

        isOpen = true;

        iframe.classList.add("shital-chatbot-open");

        button.innerHTML = "✕";

        button.setAttribute(
            "aria-label",
            "Close Shital Academy AI Assistant"
        );
    }

    function closeChatbot() {

        isOpen = false;

        iframe.classList.remove("shital-chatbot-open");

        button.innerHTML = '<img src="templates/bot.jpg" alt="Bot">';

        button.setAttribute(
            "aria-label",
            "Open Shital Academy AI Assistant"
        );
    }

    button.addEventListener("click", function () {

        if (isOpen) {
            closeChatbot();
        } else {
            openChatbot();
        }

    });

    // ============================================
    // Assemble Widget
    // ============================================

    widget.appendChild(iframe);
    widget.appendChild(button);

    document.body.appendChild(widget);

})();