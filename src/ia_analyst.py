from google import genai
import fitz 
import os
from dotenv import load_dotenv

load_dotenv()
# Sua chave que funciona no curl
client = genai.Client(
    #api_key="AIzaSyC5jTcxL6i63v2RxZpctDMoypXd8pfm0uE"
    api_key= os.getenv("GEMINI_API_KEY")
)

def extrair_texto_pdf(pdf_path):
    texto = ""
    try:
        with fitz.open(pdf_path) as doc:
            # Lemos as 10 primeiras páginas (o diário de hoje tem 14) [cite: 171, 207]
            for i in range(min(10, len(doc))):
                texto += doc[i].get_text()
        return texto
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return ""

async def gerar_resumo_diario(pdf_path, link_pdf): # Adicionamos link_pdf aqui
    try:
        texto = extrair_texto_pdf(pdf_path)
        if not texto: return "Erro ao extrair texto do PDF."

        # Prompt focado nas notícias (mantenha a lógica do conteúdo)
        prompt = (
            "Resuma o Diário Oficial da Serra (ES) em tópicos com emojis. "
            #"Destaque: 1. Promoção Bike Serra (50% desconto), 2. Curso Seringueira (15 vagas), "
            #"3. Concurso SEDU e 4. Decretos do Prefeito Weverson Meireles."
            f"\n\nCONTEÚDO:\n{texto[:15000]}"
        )

        # 📊 MONITOR DE TOKENS (Entrada)
        try:
            contagem = client.models.count_tokens(
        model='gemini-3-flash-preview', 
        contents=prompt
    )
            print(f"📊 MONITOR DE TOKENS: Enviando {contagem.total_tokens} tokens para o Gemini.")
        except Exception as e_token:
            print(f"⚠️ Não foi possível contar tokens: {e_token}")

        # Chamada da IA
        response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt
        )
        
        # 📈 MONITOR DE TOKENS (Saída/Uso)
        print(f"📉 TOKENS DE RESPOSTA: {response.usage_metadata.candidates_token_count}")
        print(f"📈 TOTAL DA OPERAÇÃO: {response.usage_metadata.total_token_count}")

        texto_limpo = response.text
        
        # 1. Remove a nota de rodapé chata do Google
        # Usei split para garantir que remova qualquer variação da nota final
        if "---" in texto_limpo:
            texto_limpo = texto_limpo.split("---")[0].strip()
        
        # 2. Remove os asteriscos duplos
        texto_limpo = texto_limpo.replace("**", "")
        
        # 3. Monta o texto final com o link online
        resumo_final = (
            f"{texto_limpo}\n\n"
            f"📄 Diário Completo: {link_pdf}"
        )
        
        return resumo_final

    except Exception as e:
        print(f"DEBUG IA: {e}")
        return f"Erro na IA: {e}. Verifique se o modelo está habilitado no AI Studio."