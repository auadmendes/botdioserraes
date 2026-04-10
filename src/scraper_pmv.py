import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import os
import logging

def buscar_vitoria_completo(data_alvo, termos):
    """
    Função oficial para o bot: baixa o PDF de Vitória e varre todos os termos.
    """
    url_portal = "https://diariooficial.vitoria.es.gov.br/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resultados_totais = []
    
    # 1. Troca / por - para o nome do arquivo
    data_limpa = data_alvo.replace('/', '-')
    caminho_pdf = f"vitoria_{data_limpa}.pdf"
    
    try:
        response = requests.get(url_portal, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontra o link da data
        link_tag = None
        for a in soup.find_all('a', href=True):
            if data_alvo in a.get_text():
                link_tag = a['href']
                break
        
        if link_tag:
            full_link = f"https://diariooficial.vitoria.es.gov.br/{link_tag}"
            pdf_res = requests.get(full_link, headers=headers)
            
            with open(caminho_pdf, 'wb') as f:
                f.write(pdf_res.content)
            
            # 2. Varre o PDF para cada termo do usuário
            with fitz.open(caminho_pdf) as doc:
                for page_num, page in enumerate(doc, start=1):
                    texto_pagina = page.get_text()
                    for termo in termos:
                        if termo.lower() in texto_pagina.lower():
                            resultados_totais.append({
                                "termo": termo,
                                "pagina": page_num,
                                "link": full_link,
                                "cidade": "VITÓRIA (PMV)"
                            })
            
            # 3. Limpeza: Deleta o PDF após a leitura
            if os.path.exists(caminho_pdf):
                os.remove(caminho_pdf)
                
            return resultados_totais
            
    except Exception as e:
        logging.error(f"Erro no scraper PMV: {e}")
        if os.path.exists(caminho_pdf): os.remove(caminho_pdf)
        
    return []