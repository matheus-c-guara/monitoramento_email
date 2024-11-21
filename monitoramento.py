# Bibliotecas para enviar email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
# Bibliotecas para enviar mensagem no slack
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
# Bibliotecas para fazer as contas e lidar com tabelas
import numpy as np
import pandas as pd
# Bibliotecas auxiliares para fazer requisição a internet, lidar com as senhas e com tempo, respectivamente
import requests
import os
import time

# Configurações de API
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("AD_ACCOUNT_ID")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
PIPEFY_TOKEN = os.getenv("PIPEFY_TOKEN")

# Configurações de email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = os.getenv("EMAIL")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Limiares de métricas
CPC_THRESHOLD = 100.00  # Limiar do CPC em reais

# ---------------------------------
# Consulta métricas do Meta Ads.
# ---------------------------------
def get_meta_ads_metrics():
    url = f"https://graph.facebook.com/v21.0/{AD_ACCOUNT_ID}/insights"
    params = {
        "level": "ad",
        "use_account_attribution_setting": "true",
        "access_token": META_ACCESS_TOKEN,
        "fields": "campaign_id,adset_id,ad_name,spend",
        "date_preset": "today"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("Erro ao consultar a API do Meta Ads:", response.text)
        return []

# ---------------------------------
# Consulta métricas do Google Ads
# ---------------------------------
def get_google_ads_metrics():
    return []

# ---------------------------------
# Consulta métricas do Pipefy
# ---------------------------------
def get_pipefy_metrics():
    # Function responsible to get cards from a pipe using Pipefy's GraphQL API
    def request_id(auth_token, pipe_id, report_id):
        url = "https://api.pipefy.com/graphql"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }

        payload = {
            "query": f"""
            mutation {{
                exportPipeReport(input: {{pipeId: {pipe_id}, pipeReportId: {report_id}}}) {{
                    pipeReportExport {{
                        id
                    }}
                }}
            }}
            """
        }

        response = requests.post(url, json=payload, headers=headers)
        
        return json.loads(response.text)['data']['exportPipeReport']['pipeReportExport']['id']

    def request_report(auth_token, download_id):    
        url = "https://api.pipefy.com/graphql"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' %auth_token
        }

        payload = {
        "query": f"""
        {{
            pipeReportExport(id: {download_id}) {{
                fileURL
                state
                startedAt
                requestedBy {{
                    id
                }}
            }}
        }}
        """
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        
        return response.text

    def get_metrics(max_attempts=30):
        qualificacao = int(request_id(PIPEFY_TOKEN, 303857036, 300613389))

        for attempt in range(max_attempts):
            try:
                response_qualificacao = request_report(PIPEFY_TOKEN, qualificacao)
                response_data = json.loads(response_qualificacao)['data']['pipeReportExport']
                
                if response_data['state'] != 'done':
                    print(f"Relatório ainda em estado {response_data['state']}. Tentativa {attempt + 1}")
                    time.sleep(10)
                    continue
                
                file_url = response_data['fileURL']
                df_qualificacao = pd.read_excel(file_url)
                print("Update executado com sucesso!")
                return df_qualificacao
            except Exception as e:
                print(f"Tentativa {attempt} falhou: {e}")
                time.sleep(10)
        else:
            print("Todas as tentativas falharam.")
            return None
    return get_metrics()

# ---------------------------------
# Envia um e-mail com o aviso.
# ---------------------------------
def send_email(subject, message):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"E-mail enviado com sucesso: {subject}")
    except Exception as e:
        print("Erro ao enviar e-mail:", e)

# ---------------------------------
# Envia uma mensagem no slack com o aviso.
# ---------------------------------
def send_slack_message(message):
    client = WebClient(token=SLACK_TOKEN)

    # Envia uma mensagem
    try:
        response = client.chat_postMessage(
            channel="#media-buying",
            text=message
        )
        print("Mensagem enviada com sucesso:", response["message"]["text"])
    except SlackApiError as e:
        print(f"Erro ao enviar mensagem: {e.response['error']}")

# ---------------------------------
# Filtra um dataframe para valores após a data relativa dada
# ---------------------------------
def filter_last_days(df, days):
    today = datetime.today()
    # Data de days dias atrás
    fourteen_days_ago = today - timedelta(days=days)
    
    # Garantir que a coluna de data esteja no formato correto
    df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
    
    # Filtrar registros
    df_filtered = df[df['Criado em'] >= fourteen_days_ago]
    return df_filtered

# ---------------------------------
# Função principal
# ---------------------------------
def check_metrics():
    # Coletando os dados
    meta_metrics = get_meta_ads_metrics()
    df_qualificacao = get_pipefy_metrics()

    # Tratando os dados da Meta
    df_gasto_meta = pd.DataFrame(meta_metrics)
    df_gasto_meta['utm_campaign'] = df_gasto_meta['campaign_id'].astype(str) + '-' + df_gasto_meta['adset_id'].astype(str) + '-' + df_gasto_meta['ad_name'].astype(str)
    df_gasto_meta = df_gasto_meta.drop(columns=['adset_id', 'ad_name', "date_stop"])
    df_gasto_meta = df_gasto_meta.rename(columns={'spend': 'gasto_meta', 'date_start': 'data'})
    df_gasto_meta['data'] = pd.to_datetime(df_gasto_meta['data']).dt.strftime('%Y-%m-%d')
    df_gasto_meta['gasto_meta'] = df_gasto_meta['gasto_meta'].astype(float)
    
    #Tratando os dados do pipefy
    df_qualificados = df_qualificacao[df_qualificacao['Fase atual'] == 'Lead qualificado'][["Fase atual", "Criado em", "utm_source", "utm_medium", "utm_campaign"]]
    df_qualificados = df_qualificados.dropna(subset=['utm_source', 'utm_medium', 'utm_campaign'])
    df_qualificados['Criado em'] = pd.to_datetime(df_qualificados['Criado em'])
    df_qualificados['Criado em'] = df_qualificados['Criado em'].dt.strftime('%Y-%m-%d')
    df_qualificados = df_qualificados.sort_values(by='Criado em', ascending=False)
    df_qualificados_facebook = df_qualificados[df_qualificados['utm_source'] == 'facebook']
    df_qualificados_facebook_14d = filter_last_days(df_qualificados_facebook, 1) #Filtrando apenas hoje
    df_qualificados_anuncio_meta = df_qualificados_facebook_14d.groupby(["Criado em", "utm_campaign"]).size().reset_index(name="Qualificados")
    df_qualificados_anuncio_meta = df_qualificados_anuncio_meta.rename(columns={'Criado em': 'data'})
    df_qualificados_anuncio_meta['data'] = pd.to_datetime(df_qualificados_anuncio_meta['data']).dt.strftime('%Y-%m-%d')
    df_qualificados_anuncio_meta = df_qualificados_anuncio_meta.sort_values(by='data', ascending=False)
    df_qualificados_anuncio_meta['campaign_id'] = df_qualificados_anuncio_meta['utm_campaign'].str.split('-').str[0]

    #Junção os dois dfs para cálculo do CPQ e separando a análise para campanha e para anúncio
    df_cpq_anuncio = df_gasto_meta.merge(df_qualificados_anuncio_meta, on=['utm_campaign','data','campaign_id'], how='left')
    df_cpq_anuncio['CPQ_anuncio'] = (df_cpq_anuncio['gasto_meta'] / df_cpq_anuncio['Qualificados']).round(2)

    df_cpq_campanha = df_cpq_anuncio.groupby('campaign_id').agg({'gasto_meta': 'sum', 'Qualificados': 'sum', 'data':'first'}).reset_index()
    df_cpq_campanha['Qualificados'] = df_cpq_campanha['Qualificados'].replace(0, np.nan)
    df_cpq_campanha['CPQ_campanha'] = (df_cpq_campanha['gasto_meta'] / df_cpq_campanha['Qualificados']).round(2)

    # Filtra as linhas onde o CPQ é maior que 100
    filtered_df_anuncio = df_cpq_anuncio[df_cpq_anuncio['CPQ_anuncio'] > 100]
    filtered_df_campanha = df_cpq_campanha[df_cpq_campanha['CPQ_campanha'] > 100]

    # Extrai os nomes das campanhas e anuncios
    ads_meta_anuncio = filtered_df_anuncio['utm_campaign'].unique()
    ads_meta_campanha = filtered_df_campanha['campaign_id'].unique()

    # Cria a lista de anúncios e campanhas para a mensagem
    ads_list_anuncio = "\n".join(ads_meta_anuncio)
    ads_list_campanha = "\n".join(ads_meta_campanha)

    # Assunto e mensagem do email
    subject = "Alerta: CPQ acima do limite no Meta Ads"
    message_ad = f"Os anúncios: \n{ads_list_anuncio}\n tiveram uma performance abaixo do esperado, mostrando um CPQ > R$100."
    message_campaign = f"As campanhas: \n{ads_list_campanha}\n tiveram uma performance abaixo do esperado, mostrando um CPQ > R$100."
    final_message = f"{message_ad}\n\n{message_campaign}"

    # Exemplo de envio do email (substitua com sua função de envio de email)
    send_email(subject, final_message)
    send_slack_message(final_message)

if __name__ == "__main__":
    check_metrics()
