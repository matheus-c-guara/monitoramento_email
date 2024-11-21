#Acessar Pipefy
import requests
from datetime import datetime
import json
import pandas as pd
import time
import os

#Pegar o token de acesso
token = os.getenv("PIPEFY_TOKEN")

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
    print(f"ID de download gerado: {qualificacao}")
    
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


qualificacao = int(request_id(token, 303857036, 300613389))
response_qualificacao = request_report(token, qualificacao)

max_attempts = 30  # número máximo de tentativas
attempt = 0

while attempt < max_attempts:
    try:
        response_qualificacao = request_report(token, qualificacao)
        response_data = json.loads(response_qualificacao)['data']['pipeReportExport']
        
        if response_data['state'] != 'done':
            print(f"Relatório ainda em estado {response_data['state']}. Tentativa {attempt + 1}")
            time.sleep(10)
            attempt += 1
            continue
        
        file_url = response_data['fileURL']
        df_qualificacao = pd.read_excel(file_url)
        print("Update executado com sucesso!")
        break
    except Exception as e:
        attempt += 1
        print(f"Tentativa {attempt} falhou: {e}")
        time.sleep(10)
else:
    print("Todas as tentativas falharam.")

print(df_qualificacao)
