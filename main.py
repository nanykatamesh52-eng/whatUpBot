from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from assistant import AI_Assistant  # ✅ import your assistant class

# Initialize once
assistant = AI_Assistant()

app = FastAPI()

@app.post("/webhook")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    """
    Called whenever Twilio sends a WhatsApp message.
    `From`: the sender's number
    `Body`: the text message
    """
    print(f"📩 WhatsApp from {From}: {Body}")

    # ✅ Call your assistant to generate a reply
    reply_text = assistant.generate_ai_response(Body, "English")

    # Send the reply back to WhatsApp
    return PlainTextResponse(f"""
<Response>
    <Message>{reply_text}</Message>
</Response>""", media_type="application/xml")
