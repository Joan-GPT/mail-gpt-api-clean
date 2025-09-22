from __future__ import print_function
import os.path
import base64
import re
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import openai

# -------------------------------------
# Configuración
# -------------------------------------
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------------
# Conectar con Gmail
# -------------------------------------
def get_gmail_service():
    creds = None
    if os.path.exists("/etc/secrets/token.json"):
        creds = Credentials.from_authorized_user_file("etc/secrets/token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("/etc/secrets/credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

# -------------------------------------
# Extraer cuerpo del email (texto o HTML)
# -------------------------------------
def extract_body(payload):
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")

            if not data:
                continue

            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

            if mime == "text/plain":
                return decoded
            elif mime == "text/html" and not body:  # si no hay texto plano, tomamos HTML
                # Eliminar etiquetas HTML
                soup = BeautifulSoup(decoded, "html.parser")
                body = soup.get_text(separator="\n")
    else:
        data = payload.get("body", {}).get("data")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Limpiar espacios excesivos
    body = re.sub(r"\n\s*\n", "\n\n", body).strip()
    return body

# -------------------------------------
# Leer correos no leídos
# -------------------------------------
def get_unread_emails(service, max_results=3):
    results = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=max_results).execute()
    messages = results.get("messages", [])
    emails = []

    for m in messages:
        msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = msg["payload"]["headers"]

        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(sin asunto)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(desconocido)")

        body = extract_body(msg["payload"])
        emails.append({"from": sender, "subject": subject, "body": body})
    return emails

# -------------------------------------
# Resumir con GPT
# -------------------------------------
def analyze_email(email):
    prompt = f"""
    Resume este correo en español:
    De: {email['from']}
    Asunto: {email['subject']}
    Contenido: {email['body'][:2000]}

    Haz:
    1. Un resumen breve en español.
    2. Una lista clara de acciones recomendadas.
    3. Un borrador de respuesta formal y educada.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# -------------------------------------
# Programa principal
# -------------------------------------
if __name__ == "__main__":
    service = get_gmail_service()
    emails = get_unread_emails(service)

    if not emails:
        print("✅ No tienes correos no leídos.")
    else:
        for email in emails:
            print("---------------------------------------------------")
            print(f"📩 De: {email['from']}")
            print(f"📌 Asunto: {email['subject']}\n")
            print("📜 Cuerpo original del email:\n")
            print(email["body"] if email["body"] else "(vacío)")
            print("\n🤖 Análisis de GPT:\n")
            print(analyze_email(email))
            print("---------------------------------------------------\n")
