import httpx
import asyncio
from datetime import datetime

# Configurações
BASE_SEARCH_URL = "https://ioes.dio.es.gov.br/busca/busca/buscar/query/0"
DATA_HOJE = "2026-04-10"

async def buscar_texto_estado(termo):
    print(f"🔎 Testando busca no ESTADO para: '{termo}'...")
    
    date_filter = f"/di:{DATA_HOJE}/df:{DATA_HOJE}"
    params = {
        "1": "1",
        "q": f'"{termo}"',
        "subtheme": "diario_oficial"  # <--- ESTE É O SEGREDO!
    }
    url = f"{BASE_SEARCH_URL}{date_filter}/"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()
            total = data.get("hits", {}).get("total", 0)

            if total > 0:
                print(f"✅ SUCESSO! Encontrados {total} resultados no Diário do Estado.")
                for hit in data["hits"]["hits"]:
                    source = hit["_source"]
                    # O ID do documento é o _id do hit
                    doc_id = hit["_id"]
                    pagina = source.get('pagina')
                    
                    print("-" * 30)
                    print(f"📄 Página: {pagina}")
                    # Link de visualização para o caderno Estadual
                    print(f"🔗 Link: https://ioes.dio.es.gov.br/portal/edicoes/ver/{doc_id}/{pagina}")
            else:
                print(f"❌ '{termo}' não encontrado no caderno do Estado hoje.")

        except Exception as e:
            print(f"⚠️ Erro: {e}")

if __name__ == "__main__":
    # Teste agora com o nome que vimos na imagem!
    asyncio.run(buscar_texto_estado("FABIANE ANDRADE DE ASSIS"))