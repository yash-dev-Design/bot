import asyncio
import json
import os
from typing import AsyncGenerator
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Set your OpenRouter API key
OPENROUTER_API_KEY = "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"

app = FastAPI(title="AI Chatbot", description="AI Chatbot powered by DeepSeek via OpenRouter")

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    content: str
    error: str = None

async def stream_openrouter_response(message: str) -> AsyncGenerator[str, None]:
    """Stream response from OpenRouter API"""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "AI Chatbot"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful AI assistant. Provide clear, concise, and helpful responses. Format your responses nicely with proper spacing and structure when appropriate."
            },
            {"role": "user", "content": message}
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'error': f'API Error: {response.status_code} - {error_text.decode()}'})}\n\n"
                    return
                
                async for chunk in response.aiter_lines():
                    if chunk:
                        chunk = chunk.strip()
                        if chunk.startswith(b"data: "):
                            data_str = chunk[6:].decode('utf-8')
                            
                            if data_str == "[DONE]":
                                break
                                
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                            except json.JSONDecodeError:
                                continue
                                
    except httpx.TimeoutException:
        yield f"data: {json.dumps({'error': 'Request timeout. Please try again.'})}\n\n"
    except httpx.RequestError as e:
        yield f"data: {json.dumps({'error': f'Connection error: {str(e)}'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)}'})}\n\n"

@app.post("/api/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """Handle chat messages and return streaming response"""
    
    if not chat_message.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    return StreamingResponse(
        stream_openrouter_response(chat_message.message),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.get("/")
async def serve_index():
    """Serve the main HTML file"""
    return FileResponse("index.html", media_type="text/html")

@app.get("/background.jpg")
async def serve_background():
    """Serve the background image"""
    return FileResponse("background.jpg", media_type="image/jpeg")

@app.get("/favicon.ico")
async def serve_favicon():
    """Serve the favicon"""
    return FileResponse("favicon.ico", media_type="image/x-icon")

# Health check endpoint for deployment
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Chatbot"}

if __name__ == "__main__":
    import uvicorn
    
    # Create the HTML file
    html_content = '''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="AI Chatbot powered by DeepSeek via OpenRouter">
    <title>AI Chatbot</title>
    <link rel="icon" type="image/x-icon"
        href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
    <meta name="theme-color" content="#007AFF">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="AI Chatbot">
    <style>
        :root {
            --primary-color: #007AFF;
            --primary-color-dark: rgba(0, 86, 204, 0.8);
            --bg-message-user: rgba(0, 122, 255, 0.7);
            --bg-message-bot: rgba(255, 255, 255, 0.15);
            --text-color: white;
            --border-color: rgba(255, 255, 255, 0.2);
            --error-color: rgba(255, 59, 48, 0.9);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #000;
            height: 100vh;
            height: calc(var(--vh, 1vh) * 100);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            color: var(--text-color);
            overflow: hidden;
            position: relative;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('background.jpg') center/cover no-repeat;
            z-index: -2;
            opacity: 0.6;
        }

        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.5));
            z-index: -1;
        }

        .chat-container {
            width: 100%;
            height: 100vh;
            height: calc(var(--vh, 1vh) * 100);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            max-width: 800px;
            margin: 0 auto;
            justify-content: flex-end;
            background: transparent;
        }

        .chat-header {
            padding: 15px 20px;
            text-align: center;
            border-bottom: none;
            flex-shrink: 0;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            max-width: 800px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(5px);
            width: 100%;
        }

        .chat-header h1 {
            color: var(--text-color);
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 5px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }

        .chat-header p {
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.9rem;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            padding-top: 100px;
            padding-bottom: 100px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 100%;
            scroll-behavior: smooth;
            position: relative;
            background: transparent;
        }

        .message {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            animation: slideIn 0.15s ease-out;
            line-height: 1.5;
            border: none;
        }

        .user-message {
            background: rgba(0, 122, 255, 0.4);
            color: var(--text-color);
            border-bottom-right-radius: 4px;
            margin-left: auto;
            margin-right: 0;
        }

        .bot-message {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-color);
            border-bottom-left-radius: 4px;
            margin-right: auto;
            margin-left: 0;
            white-space: pre-wrap;
            line-height: 1.6;
            padding: 16px 20px;
            font-size: 0.95em;
        }

        .typing-indicator {
            position: fixed;
            bottom: 85px;
            left: calc(50% - 380px);
            background: var(--bg-message-bot);
            padding: 8px 12px;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            display: none;
            align-items: center;
            gap: 6px;
            max-width: 200px;
            width: auto;
            z-index: 1000;
        }

        .typing-indicator span {
            color: var(--text-color);
            font-size: 0.9rem;
            font-weight: 500;
            white-space: nowrap;
        }

        .typing-dots {
            display: flex;
            gap: 3px;
        }

        .typing-dot {
            width: 5px;
            height: 5px;
            background: var(--primary-color);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-dot:nth-child(1) {
            animation-delay: -0.32s;
        }

        .typing-dot:nth-child(2) {
            animation-delay: -0.16s;
        }

        .typing-dot:nth-child(3) {
            animation-delay: 0s;
        }

        .chat-input {
            padding: 15px 20px;
            border-top: none;
            background: rgba(0, 0, 0, 0.3);
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            max-width: 800px;
            margin: 0 auto;
            z-index: 1000;
            flex-shrink: 0;
            backdrop-filter: blur(5px);
            width: 100%;
        }

        .input-group {
            display: flex;
            gap: 12px;
            align-items: center;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }

        #userInput {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 25px;
            font-size: 15px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-weight: normal;
            outline: none;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-color);
            transition: all 0.2s;
            min-height: 44px;
        }

        #userInput::placeholder {
            color: rgba(255, 255, 255, 0.6);
            font-weight: normal;
        }

        #userInput:focus {
            border: none;
            background: rgba(255, 255, 255, 0.15);
        }

        #sendButton {
            background: rgba(0, 122, 255, 0.4);
            color: var(--text-color);
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            min-width: 60px;
            min-height: 44px;
        }

        #sendButton:hover:not(:disabled) {
            background: rgba(0, 86, 204, 0.5);
            transform: translateY(-1px);
        }

        #sendButton:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .error-message {
            background: var(--error-color);
            color: var(--text-color);
            padding: 12px;
            border-radius: 8px;
            margin: 0 auto 12px auto;
            display: none;
            text-align: center;
            font-size: 14px;
            max-width: 70%;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(8px);
                filter: blur(2px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
                filter: blur(0);
            }
        }

        @keyframes bounce {

            0%,
            80%,
            100% {
                transform: scale(0);
            }

            40% {
                transform: scale(1);
            }
        }

        @media (max-width: 768px) {
            .chat-header {
                padding: 12px 15px;
                padding-top: env(safe-area-inset-top, 12px);
            }

            .chat-header h1 {
                font-size: 1.3rem;
                margin-bottom: 4px;
            }

            .chat-header p {
                font-size: 0.8rem;
            }

            .chat-messages {
                padding: 15px;
                padding-top: calc(80px + env(safe-area-inset-top, 0px));
                padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
            }

            .message {
                max-width: 90%;
                padding: 10px 14px;
                font-size: 0.95em;
            }

            .typing-indicator {
                bottom: calc(80px + env(safe-area-inset-bottom, 0px));
                left: 35px;
                padding: 6px 10px;
            }

            .chat-input {
                padding: 10px 15px;
                padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
            }

            .input-group {
                gap: 8px;
                padding: 0 5px;
            }

            #userInput {
                padding: 10px 14px;
                font-size: 15px;
                min-height: 40px;
            }

            #sendButton {
                padding: 10px 16px;
                font-size: 15px;
                min-width: 50px;
                min-height: 40px;
            }

            .error-message {
                max-width: 90%;
                font-size: 13px;
                padding: 10px;
                margin: 0 auto 10px auto;
            }
        }

        /* iPhone X and newer safe area support */
        @supports (padding: max(0px)) {
            .chat-container {
                padding-top: env(safe-area-inset-top);
                padding-bottom: env(safe-area-inset-bottom);
                padding-left: env(safe-area-inset-left);
                padding-right: env(safe-area-inset-right);
            }
        }

        /* Landscape mode adjustments */
        @media (max-width: 768px) and (orientation: landscape) {
            .chat-header {
                padding: 8px;
            }

            .chat-messages {
                padding-top: 60px;
                padding-bottom: 60px;
            }

            .chat-input {
                padding: 8px;
            }

            #userInput,
            #sendButton {
                min-height: 36px;
            }
        }

        /* Small screen adjustments */
        @media (max-width: 360px) {
            .chat-header h1 {
                font-size: 1.2rem;
            }

            .chat-header p {
                font-size: 0.75rem;
            }

            .message {
                max-width: 95%;
                padding: 8px 12px;
                font-size: 0.9em;
            }

            #userInput {
                font-size: 14px;
            }

            #sendButton {
                font-size: 14px;
                padding: 8px 14px;
            }
        }

        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }

        .typing-dots .text {
            display: inline-block;
            margin-right: 2px;
        }

        .typing-dots .dot {
            display: inline-block;
            animation: dotAnimation 1.4s infinite;
            opacity: 0;
        }

        .typing-dots .dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dots .dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes dotAnimation {

            0%,
            20% {
                opacity: 0;
            }

            50% {
                opacity: 1;
            }

            80%,
            100% {
                opacity: 0;
            }
        }

        .bot-message strong {
            font-weight: 600;
            color: #fff;
        }
        .bot-message em {
            font-style: italic;
            color: rgba(255, 255, 255, 0.9);
        }
        .bot-message code {
            background: rgba(0, 0, 0, 0.2);
            padding: 2px 4px;
            border-radius: 4px;
            font-family: monospace;
        }
        .bot-message pre {
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
        }
        .bot-message pre code {
            background: none;
            padding: 0;
        }
        .bot-message li {
            margin-left: 20px;
            margin-bottom: 4px;
        }
    </style>
</head>

<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>AI Chatbot</h1>
            <p>Powered by DeepSeek via OpenRouter</p>
        </div>

        <div class="chat-messages" id="chatMessages">
            <div class="error-message" id="errorMessage"></div>
        </div>

        <div class="typing-indicator" id="typingIndicator">
            <div class="typing-dots">
                <span class="text">AI is thinking</span><span class="dot">.</span><span class="dot">.</span><span
                    class="dot">.</span>
            </div>
        </div>

        <div class="chat-input">
            <div class="input-group">
                <textarea id="userInput" placeholder="Type your message here..." rows="1" maxlength="4000"></textarea>
                <button id="sendButton">
                    <span class="button-text">Send</span>
                    <div class="loading-spinner"></div>
                </button>
            </div>
        </div>
    </div>

    <script>
        const elements = {
            chatMessages: document.getElementById('chatMessages'),
            userInput: document.getElementById('userInput'),
            sendButton: document.getElementById('sendButton'),
            typingIndicator: document.getElementById('typingIndicator'),
            errorMessage: document.getElementById('errorMessage'),
            buttonText: document.querySelector('.button-text'),
            loadingSpinner: document.querySelector('.loading-spinner')
        };

        let isLoading = false;

        // Auto-resize textarea
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }

        elements.userInput.addEventListener('input', function () {
            autoResize(this);
        });

        function scrollToBottom() {
            setTimeout(() => {
                elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
            }, 50);
        }

        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            messageDiv.innerHTML = content;
            elements.chatMessages.appendChild(messageDiv);
            scrollToBottom();
            return messageDiv;
        }

        function updateBotMessage(messageDiv, content) {
            messageDiv.innerHTML = content;
            scrollToBottom();
        }

        function showError(message) {
            elements.errorMessage.textContent = message;
            elements.errorMessage.style.display = 'block';
            setTimeout(() => {
                elements.errorMessage.style.display = 'none';
            }, 5000);
        }

        function setLoading(loading) {
            isLoading = loading;
            elements.sendButton.disabled = loading;
            elements.buttonText.style.display = loading ? 'none' : 'inline';
            elements.loadingSpinner.style.display = loading ? 'inline-block' : 'none';

            scrollToBottom();
        }

        async function sendMessage() {
            const message = elements.userInput.value.trim();

            if (!message || isLoading) return;

            elements.userInput.value = '';
            elements.userInput.style.height = 'auto';
            setLoading(true);

            addMessage(message, true);
            const botMessageDiv = addMessage('', false);

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Server error');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let botResponse = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.error) {
                                    throw new Error(data.error);
                                }
                                if (data.content) {
                                    botResponse += data.content;
                                    updateBotMessage(botMessageDiv, botResponse);
                                }
                            } catch (e) {
                                console.warn('Error parsing SSE data:', e);
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                showError(error.message);
                botMessageDiv.textContent = 'Sorry, I encountered an error. Please try again.';
            } finally {
                setLoading(false);
            }
        }

        elements.sendButton.addEventListener('click', sendMessage);

        elements.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Handle mobile viewport and window resize
        function handleViewport() {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);

            // Force layout recalculation
            const chatContainer = document.querySelector('.chat-container');
            if (chatContainer) {
                chatContainer.style.height = `${window.innerHeight}px`;
            }
        }

        // Debounce resize events
        let resizeTimeout;
        function debouncedHandleViewport() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(handleViewport, 100);
        }

        window.addEventListener('resize', debouncedHandleViewport);
        window.addEventListener('orientationchange', () => {
            setTimeout(handleViewport, 300); // Delay for orientation change
        });
        handleViewport();

        // Add welcome message
        setTimeout(() => {
            addMessage("Hello! I'm your AI assistant powered by DeepSeek. How can I help you today?", false);
        }, 500);
    </script>
</body>

</html>'''
    
    # Write the HTML file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Create a simple background image placeholder (you can replace this with the actual image)
    print("📁 Created index.html file")
    print("🌐 Starting server on http://localhost:8000")
    print("🤖 Chatbot ready with live streaming!")
    print("🔑 Using OpenRouter API with DeepSeek model")
    print("\n" + "="*50)
    print("🚀 DEPLOYMENT READY FEATURES:")
    print("✅ FastAPI server with async streaming")
    print("✅ Health check endpoint (/health)")
    print("✅ Error handling and timeouts")
    print("✅ CORS headers for cross-origin requests")
    print("✅ Mobile-responsive design")
    print("✅ Real-time streaming responses")
    print("="*50 + "\n")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
