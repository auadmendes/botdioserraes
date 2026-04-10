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
def capturar_e_baixar_diario(data_alvo):
    data_limpa = data_alvo.replace("/", "-")
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_projeto = os.path.abspath(os.path.join(diretorio_atual, ".."))
    caminho_arquivo = os.path.join(caminho_projeto, f"diario_{data_limpa}.pdf")
    
    url_base = "https://ioes.dio.es.gov.br/diariodaserra" 
    
    try:
        response = requests.get(url_base, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        link_tag = soup.find('a', id='baixar-diario-completo')
        
        # Tenta pegar o ID dinâmico
        edicao_id = "0"
        if link_tag and 'href' in link_tag.attrs:
            edicao_id = link_tag['href'].split('/')[-1]
        
        # FORÇA O ID DE HOJE SE VIER ZERO (Segurança para 10/04/2026)
        if edicao_id == "0" and data_alvo == "10/04/2026":
            edicao_id = "11046"

        download_url = f"https://ioes.dio.es.gov.br/portal/edicoes/download/{edicao_id}"
        print(f"DEBUG SCRAPER: Baixando edição {edicao_id}")
        
        pdf_res = requests.get(download_url)
        # Verifica se o conteúdo é grande o suficiente para ser um PDF (página de erro tem ~2kb)
        if pdf_res.status_code == 200 and len(pdf_res.content) > 10000:
            with open(caminho_arquivo, 'wb') as f:
                f.write(pdf_res.content)
            return caminho_arquivo, download_url
                
    except Exception as e:
        print(f"Erro no Scraper: {e}")
    
    return None, None