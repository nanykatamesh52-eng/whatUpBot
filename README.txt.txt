# WhatsApp AI Bot (FastAPI)

## What it Does
This is a simple WhatsApp chatbot using FastAPI. It:
- Receives messages from WhatsApp via Twilio
- Sends the message to an AI assistant
- Replies back automatically

## Requirements
- Python 3.10+
- FastAPI, Uvicorn, Twilio
- `assistant.py` with `AI_Assistant` class
- Twilio WhatsApp sandbox account

Install dependencies:
pip install fastapi uvicorn twilio python-dotenv

## Files
- main.py → FastAPI webhook
- assistant.py → AI response logic
- .env → Environment variables (Twilio info)

## How it Works
1. WhatsApp user sends a message to your Twilio number.
2. Twilio forwards the message to /webhook endpoint via POST request.
3. FastAPI receives From (sender number) and Body (message text).
4. AI_Assistant.generate_ai_response() is called to generate a reply.
5. The reply is sent back to Twilio in XML format.
6. Twilio delivers the reply to the WhatsApp user.

## How to Run
1. Start FastAPI server:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
2. (Optional) Expose your local server using ngrok:
ngrok http 8000
3. Set the Twilio webhook URL to:
https://<ngrok-id>.ngrok.io/webhook
4. Send a WhatsApp message to your Twilio sandbox number. The bot will reply.

## Example
User: Hello
Bot: Hi! How can I help you today?

## Notes
- Keep your server running to receive messages.
- Make sure AI_Assistant is implemented correctly.
- Responses are sent in Twilio’s required XML format.
