# 🤖 Serra Notifica Bot (DioesAPI)

O **Serra Notifica** é um bot de automação para o Telegram que monitora e resume diariamente o **Diário Oficial do Município da Serra (ES)**. Utilizando a IA **Gemini 1.5 Flash**, o sistema extrai informações críticas como alertas de Defesa Civil, investimentos em obras, editais e eventos culturais, entregando-os de forma mastigada para o cidadão.

## ✨ Funcionalidades

* 🔍 **Monitoramento de Termos**: Cadastre nomes ou palavras-chave (ex: seu nome ou nome da sua rua) e receba um alerta assim que forem publicados.
* 📝 **Resumo Diário com IA**: Todos os dias, o bot lê o PDF do Diário Oficial e gera um resumo inteligente em tópicos com emojis.
* 💾 **Histórico de Resumos**: Consulte resumos de datas passadas diretamente pelo chat.
* 🔔 **Alertas em Tempo Real**: Notificações instantâneas sobre resultados de buscas específicas.
* 📊 **Painel Administrativo**: Estatísticas de uso, termos mais buscados e controle de usuários.

## 🚀 Tecnologias Utilizadas

* **Linguagem:** Python 3.10+
* **IA:** [Google Gemini API](https://ai.google.dev/) (Modelo: Gemini 1.5 Flash)
* **Bot Framework:** [python-telegram-bot](https://python-telegram-bot.org/)
* **Banco de Dados:** MongoDB (Atlas)
* **Scraping:** BeautifulSoup4 & Requests
* **Agendamento:** APScheduler
* **Processamento de PDF:** PyMuPDF (fitz)

## 🛠️ Instalação e Configuração

### 1. Clonar o Repositório
```bash
git clone [https://github.com/seu-usuario/dioesapi.git](https://github.com/seu-usuario/dioesapi.git)
cd dioesapi
