import os
from dotenv import load_dotenv
from google import genai

def main():
    load_dotenv()

    #api_key = os.getenv("GEMINI_API_KEY")
    #api_key = "AIzaSyCEYuLQtrbURhD_fnq1h2Pp4OtJ-FvrXEE"
    api_key = "AIzaSyC5jTcxL6i63v2RxZpctDMoypXd8pfm0uE"
    # (ou deixe sua chave fixa enquanto está testando, mas o ideal é usar o .env)

    if not api_key:
        print("Erro: variável GEMINI_API_KEY não encontrada. Confira o arquivo .env.")
        return

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",  # 🔴 TROQUEI AQUI
            contents="Diga 'Olá, Gemini API está funcionando!' em português."
        )
        print("Resposta do modelo:")
        print(response.text)
    except Exception as e:
        print("Ocorreu um erro ao chamar a API:")
        print(e)

if __name__ == "__main__":
    main()