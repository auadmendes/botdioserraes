import requests
from bs4 import BeautifulSoup
import fitz
import os
import logging
from datetime import datetime

def buscar_vila_velha_completo(termos):
    url_portal = "https://diariooficial.vilavelha.es.gov.br/Default.aspx"
    hoje = datetime.now().strftime("%d/%m/%Y")
    # A URL de consulta que você descobriu
    url_consulta = f"{url_portal}?texto=&dataInicial={hoje}&dataFinal={hoje}#consulta"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': url_consulta
    }
    caminho_pdf = "vv_temp.pdf"
    resultados_totais = []

    try:
        session = requests.Session()
        # 1. Carrega a página de consulta para pegar os campos ocultos do ASP.NET
        res_page = session.get(url_consulta, headers=headers, timeout=20)
        soup = BeautifulSoup(res_page.text, 'html.parser')

        # Pegamos os campos obrigatórios do formulário ASP
        def get_val(id):
            tag = soup.find('input', id=id)
            return tag['value'] if tag else ""

        # Este é o "payload" que simula o clique no link que você encontrou
        data = {
            '__EVENTTARGET': 'ctl00$cpConteudo$gvDocumentos$ctl02$lbDownloadPDF',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': get_val('__VIEWSTATE'),
            '__VIEWSTATEGENERATOR': get_val('__VIEWSTATEGENERATOR'),
            '__EVENTVALIDATION': get_val('__EVENTVALIDATION'),
        }

        # 2. Faz o POST para "clicar" no botão de PDF
        logging.info("📡 Solicitando PDF para Vila Velha via PostBack...")
        pdf_res = session.post(url_portal, headers=headers, data=data, timeout=40)

        if pdf_res.status_code == 200 and b'%PDF' in pdf_res.content[:100]:
            with open(caminho_pdf, 'wb') as f:
                f.write(pdf_res.content)
            
            logging.info(f"✅ PDF de Vila Velha baixado ({len(pdf_res.content)} bytes)")
            
            with fitz.open(caminho_pdf) as doc:
                for page_num, page in enumerate(doc, start=1):
                    texto = page.get_text()
                    for termo in termos:
                        if termo.lower() in texto.lower():
                            resultados_totais.append({
                                "termo": termo,
                                "pagina": page_num,
                                "link": url_consulta,
                                "cidade": "VILA VELHA"
                            })
            
            if os.path.exists(caminho_pdf): os.remove(caminho_pdf)
            return resultados_totais
        else:
            logging.error(f"❌ Não conseguimos o PDF. Status: {pdf_res.status_code}")
            
    except Exception as e:
        logging.error(f"❌ Erro no Scraper de VV: {e}")
        if os.path.exists(caminho_pdf): os.remove(caminho_pdf)
        
    return []