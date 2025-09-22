from fastapi import FastAPI
from mail_gpt import get_gmail_service, get_unread_emails

app = FastAPI()

@app.get("/gmail/unread")
def unread_emails():
    service = get_gmail_service()
    emails = get_unread_emails(service, max_results=5)
    return {"emails": emails}
