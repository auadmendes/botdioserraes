import asyncio
import logging
import os
from datetime import datetime
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Importações do seu projeto
from src.database import (
    add_term, remove_term, get_all_subscriptions, 
    ja_foi_notificado, get_user_terms, get_admin_stats
)
from src.scraper import check_term_ioes, capturar_e_baixar_diario
from src.ia_analyst import gerar_resumo_diario

load_dotenv()

# CONFIGURAÇÕES
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- COMANDOS DO USUÁRIO ---

async def start(update, context):
    await update.message.reply_text("🤖 Bot Ativado!\nUse /monitorar [nome] para começar.")

async def resposta_padrao(update, context):
    nome_usuario = update.effective_user.first_name
    resposta = (
        f"Olá {nome_usuario}! 👋\n\n"
        "Toque nos comandos abaixo para copiar e depois complete com o nome:\n\n"
        "✨ **Comandos disponíveis:**\n"
        "🔹 `/monitorar ` - Cadastrar novo nome\n"
        "🔹 `/meustermos` - Ver o que estou vigiando\n"
        "🔹 `/remover ` - Parar de vigiar um nome\n"
        "🔹 `/som` - Testar som da notificação"
    )
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def meus_termos(update, context):
    chat_id = update.effective_chat.id
    termos = get_user_terms(chat_id) 
    if termos:
        termos_lista = "\n".join([f"• {t}" for t in termos])
        await update.message.reply_text(f"📝 **Seus nomes monitorados:**\n\n{termos_lista}", parse_mode='Markdown')
    else:
        await update.message.reply_text("Você não tem nomes cadastrados. Use /monitorar [nome]")

async def remover(update, context):
    chat_id = update.effective_chat.id
    termo = " ".join(context.args).strip()
    if not termo:
        await update.message.reply_text("⚠️ Exemplo: `/remover Maria Rangel`", parse_mode='Markdown')
        return
    if remove_term(chat_id, termo):
        await update.message.reply_text(f"✅ Removido com sucesso: **{termo}**")
    else:
        await update.message.reply_text(f"❓ Não encontrei '{termo}' na sua lista.")

async def monitorar(update, context):
    term = " ".join(context.args).strip()
    if term:
        add_term(update.effective_chat.id, update.effective_user.username, term)
        await update.message.reply_text(f"✅ Agora estou vigiando: **{term}**")
    else:
        await update.message.reply_text("❌ Exemplo: /monitorar MARIA RANGEL")

async def som(update, context):
    await update.message.reply_text("🔔 Testando som...", disable_notification=False)

async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado.")
        return
    total_users, total_alerts, top_terms = get_admin_stats()
    texto_top = "\n".join([f"🔥 {t['_id']}: {t['count']}" for t in top_terms])
    mensagem = (f"📊 **Estatísticas**\n\n👥 Usuários: `{total_users}`\n🔔 Alertas: `{total_alerts}`\n\n🔝 **Top Termos:**\n{texto_top}")
    await update.message.reply_text(mensagem, parse_mode='Markdown')

# --- TAREFAS AGENDADAS (JOBS) ---

async def tarefa_de_busca(app):
    """Busca os nomes específicos de cada usuário"""
    logging.info("🔎 Iniciando busca de termos...")
    subs = get_all_subscriptions()
    for sub in subs:
        chat_id = sub['chat_id']
        for term in sub['terms']:
            resultados = await check_term_ioes(term)
            if isinstance(resultados, list):
                for item in resultados:
                    if not ja_foi_notificado(chat_id, item['link']):
                        msg = (f"🔔 **Resultado Encontrado!**\n\n👤 Termo: {term}\n📄 Página: {item['pagina']}\n🔗 [Abrir Diário]({item['link']})")
                        await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
    logging.info("✅ Busca de termos finalizada.")

async def tarefa_resumo_diario(app):
    logging.info("📝 Iniciando resumo diário com Gemini...")
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    # Recebe os dois valores do scraper
    caminho_pdf, link_pdf = capturar_e_baixar_diario(hoje) 

    if caminho_pdf and link_pdf:
        # Envia os dois valores para a IA
        resumo = await gerar_resumo_diario(caminho_pdf, link_pdf)
        
        # Opcional: Salvar no banco se você quiser usar o comando /resumo depois
        from src.database import salvar_resumo_no_banco
        salvar_resumo_no_banco(hoje, resumo)

        subs = get_all_subscriptions()
        for sub in subs:
            try:
                await app.bot.send_message(
                    chat_id=sub['chat_id'],
                    text=f"☀️ BOM DIA! RESUMO DA SERRA ({hoje})\n\n{resumo}"
                    # Remova a linha do parse_mode aqui!
                )
            except Exception as e:
                logging.error(f"Erro ao enviar resumo para {sub['chat_id']}: {e}")
        
        if os.path.exists(caminho_pdf):
            os.remove(caminho_pdf)
    logging.info("✅ Resumo diário finalizado.")

# --- INICIALIZAÇÃO ---

async def post_init(application):
    # Configura o Menu de Comandos
    await application.bot.set_my_commands([
        BotCommand("monitorar", "Vigiar um nome"),
        BotCommand("meustermos", "Ver meus nomes"),
        BotCommand("remover", "Parar de vigiar"),
        BotCommand("som", "Testar som"),
        BotCommand("stats", "Admin Stats")
    ])

    scheduler = AsyncIOScheduler()
    # Busca termos a cada 1 hora
    #scheduler.add_job(tarefa_de_busca, 'interval', hours=0, minutes=1, args=[application])
    # Resumo diário às 09:00 da manhã
    scheduler.add_job(tarefa_resumo_diario, 'cron', hour=12, minute=9, args=[application])
    
    scheduler.start()
    logging.info("⏰ Scheduler iniciado.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitorar", monitorar))
    app.add_handler(CommandHandler("meustermos", meus_termos))
    app.add_handler(CommandHandler("remover", remover))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("som", som))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), resposta_padrao))

    logging.info("🚀 Bot iniciando...")
    app.run_polling()