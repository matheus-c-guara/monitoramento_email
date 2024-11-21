from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

slack_token = os.getenv("SLACK_TOKEN")
client = WebClient(token=slack_token)

# Envia uma mensagem
try:
    response = client.chat_postMessage(
        channel="#media-buying",
        text="Github também envia mensagens no Slack!"
    )
    print("Mensagem enviada com sucesso:", response["message"]["text"])
except SlackApiError as e:
    print(f"Erro ao enviar mensagem: {e.response['error']}")
