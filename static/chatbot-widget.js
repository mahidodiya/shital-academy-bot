(function () {

    "use strict";


    // ============================================
    // CONFIG
    // ============================================

    const CHATBOT_URL =
        "https://shital-academy-assistant.onrender.com";

    const BOT_IMAGE_URL =
        `${CHATBOT_URL}/static/bot.jpg`;


    // ============================================
    // PREVENT DUPLICATE WIDGET
    // ============================================

    if (
        document.getElementById(
            "shital-academy-chatbot-widget"
        )
    ) {

        return;

    }


    // ============================================
    // CSS
    // ============================================

    const style =
        document.createElement("style");


    style.textContent = `

        /* =========================
           WIDGET
        ========================= */

        #shital-academy-chatbot-widget {

            position: fixed;

            right: 20px;
            bottom: 20px;

            z-index: 2147483647;

            font-family: Arial, sans-serif;

        }


        /* =========================
           CHAT BUTTON
        ========================= */

        #shital-chatbot-button {

            width: 58px;
            height: 58px;

            padding: 0;

            border: none;

            border-radius: 50%;

            background: #e51c23;

            color: white;

            cursor: pointer;

            display: flex;

            align-items: center;
            justify-content: center;

            overflow: hidden;

            box-shadow:
                0 7px 22px
                rgba(0, 0, 0, 0.25);

            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease;

        }


        #shital-chatbot-button:hover {

            transform: scale(1.05);

            box-shadow:
                0 9px 26px
                rgba(0, 0, 0, 0.30);

        }


        /* =========================
           BOT IMAGE
        ========================= */

        #shital-chatbot-button img {

            width: 100%;
            height: 100%;

            display: block;

            object-fit: cover;

            border-radius: 50%;

        }


        /* =========================
           CLOSE BUTTON
        ========================= */

        #shital-chatbot-button.shital-close {

            font-size: 30px;

            background: #e51c23;

        }


        /* =========================
           CHAT WINDOW
        ========================= */

        #shital-chatbot-window {

            position: fixed;

            right: 20px;

            bottom: 88px;

            width: 360px;

            height: 550px;

            border: none;

            border-radius: 16px;

            background: white;

            box-shadow:
                0 15px 45px
                rgba(0, 0, 0, 0.24);

            display: none;

            overflow: hidden;

            background-color: white;

        }


        #shital-chatbot-window.shital-chatbot-open {

            display: block;

        }


        /* =========================
           TABLET / MOBILE
        ========================= */

        @media (max-width: 768px) {

            #shital-academy-chatbot-widget {

                right: 12px;

                bottom: 12px;

            }


            #shital-chatbot-button {

                width: 54px;

                height: 54px;

            }


            #shital-chatbot-window {

                right: 12px;

                bottom: 78px;

                width:
                    calc(100vw - 24px);

                max-width: 350px;

                height:
                    calc(100dvh - 120px);

                max-height: 540px;

                min-height: 400px;

                border-radius: 14px;

            }

        }


        /* =========================
           SMALL MOBILE
        ========================= */

        @media (max-width: 480px) {

            #shital-academy-chatbot-widget {

                right: 10px;

                bottom: 10px;

            }


            #shital-chatbot-button {

                width: 52px;

                height: 52px;

            }


            #shital-chatbot-window {

                left: 10px;

                right: 10px;

                bottom: 70px;

                width:
                    calc(100vw - 20px);

                max-width: none;

                height:
                    calc(100dvh - 90px);

                max-height: 510px;

                min-height: 380px;

                border-radius: 13px;

            }

        }


        /* =========================
           VERY SMALL PHONES
        ========================= */

        @media (max-width: 360px) {

            #shital-chatbot-window {

                left: 8px;

                right: 8px;

                bottom: 66px;

                width:
                    calc(100vw - 16px);

                height:
                    calc(100dvh - 82px);

                max-height: 480px;

            }

        }

    `;


    document.head.appendChild(style);


    // ============================================
    // WIDGET CONTAINER
    // ============================================

    const widget =
        document.createElement("div");

    widget.id =
        "shital-academy-chatbot-widget";


    // ============================================
    // CHAT BUTTON
    // ============================================

    const button =
        document.createElement("button");

    button.id =
        "shital-chatbot-button";

    button.type = "button";


    button.innerHTML =
        `<img
            src="${BOT_IMAGE_URL}"
            alt="Chat with Shital Academy AI Assistant"
        >`;


    button.setAttribute(
        "aria-label",
        "Open Shital Academy AI Assistant"
    );


    button.setAttribute(
        "title",
        "Chat with Shital Academy AI Assistant"
    );


    // ============================================
    // IFRAME
    // ============================================

    const iframe =
        document.createElement("iframe");


    iframe.id =
        "shital-chatbot-window";


    iframe.src =
        CHATBOT_URL;


    iframe.title =
        "Shital Academy AI Assistant";


    iframe.setAttribute(
        "allow",
        "clipboard-write"
    );


    iframe.setAttribute(
        "loading",
        "lazy"
    );


    // ============================================
    // STATE
    // ============================================

    let isOpen = false;


    // ============================================
    // OPEN CHAT
    // ============================================

    function openChatbot() {

        isOpen = true;


        iframe.classList.add(
            "shital-chatbot-open"
        );


        button.classList.add(
            "shital-close"
        );


        button.innerHTML = "✕";


        button.setAttribute(
            "aria-label",
            "Close Shital Academy AI Assistant"
        );

    }


    // ============================================
    // CLOSE CHAT
    // ============================================

    function closeChatbot() {

        isOpen = false;


        iframe.classList.remove(
            "shital-chatbot-open"
        );


        button.classList.remove(
            "shital-close"
        );


        button.innerHTML =
            `<img
                src="${BOT_IMAGE_URL}"
                alt="Chat with Shital Academy AI Assistant"
            >`;


        button.setAttribute(
            "aria-label",
            "Open Shital Academy AI Assistant"
        );

    }


    // ============================================
    // BUTTON CLICK
    // ============================================

    button.addEventListener(
        "click",
        function () {

            if (isOpen) {

                closeChatbot();

            }

            else {

                openChatbot();

            }

        }
    );


    // ============================================
    // ASSEMBLE
    // ============================================

    widget.appendChild(iframe);

    widget.appendChild(button);

    document.body.appendChild(widget);


})();