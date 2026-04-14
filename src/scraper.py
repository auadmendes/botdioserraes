from flask import logging
import httpx
from datetime import datetime
import urllib.parse
import requests
from bs4 import BeautifulSoup
import os

BASE_SEARCH_URL = "https://ioes.dio.es.gov.br/busca/busca/buscar/query/0"

# --- FUNÇÃO 1: BUSCA NOMES ESPECÍFICOS (MONITORAMENTO) ---
async def check_term_ioes(term):
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    date_filter = f"/di:{today}/df:{today}"
    
    params = {
        "1": "1",
        "q": f'"{term}"',
        "subtheme": "diariodaserra"
    }
    
    url = f"{BASE_SEARCH_URL}{date_filter}/"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("hits") and data["hits"].get("total", 0) > 0:
                for hit in data["hits"]["hits"]:
                    source = hit["_source"]
                    edicao_id = source.get("edicao_id") or source.get("diario_id")
                    pagina = source.get("pagina")
                    termo_url = urllib.parse.quote(term)
                    
                    link_visualizacao = f"https://ioes.dio.es.gov.br/diariodaserra/ver/{edicao_id}/{pagina}/{termo_url}"
                    
                    resumo = ""
                    if "highlight" in hit and "texto" in hit["highlight"]:
                        resumo = hit["highlight"]["texto"][0].replace("<strong>", "*").replace("</strong>", "*")

                    results.append({
                        "data": f"{source['day']}/{source['month']}/{source['year']}",
                        "link": link_visualizacao,
                        "pagina": pagina,
                        "resumo": resumo
                    })
            
            return results

        except Exception as e:
            print(f"⚠️ Erro ao buscar termo {term}: {e}")
            return []

# --- FUNÇÃO 2: DOWNLOAD DO DIÁRIO COMPLETO (RESUMO IA) ---
import logging # Garante o import correto no topo do arquivo

def capturar_e_baixar_diario(data_alvo):
    try:
        # 1. Preparação de caminhos e nomes
        data_limpa = data_alvo.replace("/", "-")
        print(f"📅 Data Alvo: {data_alvo} | Data Limpa: {data_limpa}")
        
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        print(f"📂 Diretório Atual do Script: {diretorio_atual}")
        # Caminho para salvar o arquivo na raiz do projeto
        caminho_projeto = os.path.abspath(os.path.join(diretorio_atual, ".."))
        print(f"📁 Caminho do Projeto: {caminho_projeto}")
        caminho_arquivo = os.path.join(caminho_projeto, f"diario_{data_limpa}.pdf")
        print(f"📄 Caminho Completo para Salvar o PDF: {caminho_arquivo}")
        
        # 2. Requisição para a API do IOES
        url_api = "https://ioes.dio.es.gov.br/apifront/portal/edicoes/ultimas_edicoes/diariodaserra"
        print(f"🔗 URL da API: {url_api}")
        
        response = requests.get(url_api, timeout=15)
        print(f"📊 Status da Resposta: {response.status_code}")
        
        edicoes = response.json()
        print(f"📦 Tipo de Dados Recebidos: {type(edicoes)}")

        edicao_id = None

        # --- LÓGICA DE EXTRAÇÃO DO ID ---

        # CASO A: API retornou um Dicionário direto (Formato atual)
        if isinstance(edicoes, dict):
            print(f"📦 API retornou um dicionário. Chaves: {list(edicoes.keys())}")
            edicao_id = edicoes.get('id') or edicoes.get('ID') or edicoes.get('edicao_id')
            print(f"🔍 ID Encontrado no topo do dicionário: {edicao_id}")
            
            # Se o ID não estiver no topo, procura se existe uma lista dentro do dicionário
            if not edicao_id:
                print("🔍 ID não encontrado no topo do dicionário. Verificando listas internas...")
                for chave in edicoes.keys():
                    if isinstance(edicoes[chave], list) and len(edicoes[chave]) > 0:
                        item = edicoes[chave][0]
                        if isinstance(item, dict):
                            edicao_id = item.get('id')
                            break

        # CASO B: API retornou uma Lista (Formato antigo/alternativo)
        elif isinstance(edicoes, list) and len(edicoes) > 0:
            print(f"📄 API retornou uma lista com {len(edicoes)} itens.")
            item = edicoes[0]
            if isinstance(item, dict):
                edicao_id = item.get('id') or item.get('ID') or item.get('edicao_id')
            else:
                edicao_id = item

        print(f"🔍 ID Final Identificado: {edicao_id}")

        # 3. Download do PDF se o ID foi encontrado
        if edicao_id:
            download_url = f"https://ioes.dio.es.gov.br/portal/edicoes/download/{edicao_id}"
            print(f"🚀 Tentando baixar PDF do ID: {edicao_id}")
            
            pdf_res = requests.get(download_url, timeout=60)
            print(f"📊 Status do Download: {pdf_res.status_code} | Tamanho do Conteúdo: {len(pdf_res.content)} bytes")
            
            # Verifica se o download foi bem sucedido e se o conteúdo parece um PDF
            if pdf_res.status_code == 200 and len(pdf_res.content) > 1000:
                with open(caminho_arquivo, 'wb') as f:
                    f.write(pdf_res.content)
                print(f"✅ ARQUIVO SALVO COM SUCESSO: {len(pdf_res.content)} bytes")
                return caminho_arquivo, download_url
            else:
                print(f"❌ Resposta de download inválida. Status: {pdf_res.status_code}")
        else:
            print("⚠️ Não foi possível localizar o edicao_id nos dados recebidos.")
        
    except Exception as e:
        print(f"❌ Erro Crítico no Scraper: {e}")
    
    return None, None

##

async def check_term_vitoria(term):
    """Busca termos específicos no Diário de Vitória"""
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    date_filter = f"/di:{today}/df:{today}"
    
    params = {
        "1": "1",
        "q": f'"{term}"',
        "subtheme": "vitoria" # <--- MUDANÇA AQUI
    }
    
    url = f"{BASE_SEARCH_URL}{date_filter}/"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("hits") and data["hits"].get("total", 0) > 0:
                for hit in data["hits"]["hits"]:
                    source = hit["_source"]
                    edicao_id = source.get("edicao_id") or source.get("diario_id")
                    pagina = source.get("pagina")
                    termo_url = urllib.parse.quote(term)
                    
                    # Link de visualização específico para Vitória
                    link_visualizacao = f"https://ioes.dio.es.gov.br/vitoria/ver/{edicao_id}/{pagina}/{termo_url}"
                    
                    resumo = ""
                    if "highlight" in hit and "texto" in hit["highlight"]:
                        resumo = hit["highlight"]["texto"][0].replace("<strong>", "*").replace("</strong>", "*")

                    results.append({
                        "data": f"{source['day']}/{source['month']}/{source['year']}",
                        "link": link_visualizacao,
                        "pagina": pagina,
                        "resumo": resumo
                    })
            return results
        except Exception as e:
            print(f"⚠️ Erro ao buscar termo {term} em Vitória: {e}")
            return []

def capturar_diario_vitoria(data_alvo):
    """Captura o PDF do Diário de Vitória para resumo de IA"""
    url_vitoria = "https://ioes.dio.es.gov.br/vitoria" 
    # Repita a lógica de download que usamos no scraper da Serra, 
    # mas apontando para url_vitoria.
    # O ID da edição de Vitória será diferente do da Serra.