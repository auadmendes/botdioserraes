import asyncio
import httpx
import json
from datetime import datetime
import urllib.parse

async def testar_busca(termo):
    # Usando a data de hoje para o teste
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # URL que identificamos no seu arquivo HAR
    url = f"https://ioes.dio.es.gov.br/busca/busca/buscar/query/0/di:{hoje}/df:{hoje}/"
    
    params = {
        "1": "1",
        "q": f'"{termo}"',
        "subtheme": "diariodaserra"
    }

    print(f"🔎 Buscando por: {termo} na data {hoje}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            
            print(f"📡 Status Code: {response.status_code}")
            
            # Print do JSON bruto para ver a estrutura completa que o site retorna
            dados = response.json()
            print("📦 Resposta bruta do site:")
            print(json.dumps(dados, indent=2)) # Isso organiza o JSON na tela

            if "hits" in dados and dados["hits"]["total"] > 0:
                print(f"\n✅ SUCESSO: Encontrei {dados['hits']['total']} resultados!")
                for hit in dados["hits"]["hits"]:
                    source = hit["_source"]
                    print(f"---")
                    print(f"Pagina: {source.get('pagina')}")
                    print(f"Resumo: {hit.get('highlight', {}).get('texto', ['Sem resumo'])[0]}")
            else:
                print("\n❌ Nenhum resultado encontrado para hoje.")

        except Exception as e:
            print(f"⚠️ Erro no teste: {e}")

# Roda o teste
if __name__ == "__main__":
    termo_teste = "MARIA RANGEL DA SILVA" # Termo que você usou no print anterior
    asyncio.run(testar_busca(termo_teste))