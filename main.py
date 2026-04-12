import asyncio
import logging
import os
from datetime import datetime
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


from src.scraper_pmv import buscar_vitoria_completo
from src.scraper_vv import buscar_vila_velha_completo


from dotenv import load_dotenv

# Importações do seu projeto
from src.database import (
    add_term, remove_term, get_all_subscriptions, 
    ja_foi_notificado, get_user_terms, get_admin_stats, remove_user_term,
    salvar_resumo_no_banco, 
    buscar_resumo_por_data,    # <--- ADICIONE ESTA
    get_ultimas_datas_resumo   # <--- ADICIONE ESTA TAMBÉM
)
from src.scraper import check_term_ioes, capturar_e_baixar_diario, check_term_vitoria
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

    if not termos:
        await update.message.reply_text("Você não tem nomes monitorados.")
        return

    termos_lista = ""
    for t in termos:
        # Se for um dicionário (formato novo)
        if isinstance(t, dict):
            nome = t.get('nome', 'Sem nome').replace("*", "")
            # Substituímos o sublinhado por espaço para o Telegram não achar que é itálico
            cidade = t.get('cidade', 'SERRA').replace("_", " ")
        else:
            # Se ainda houver strings antigas no banco
            nome = str(t).replace("*", "")
            cidade = "SERRA"
            
        termos_lista += f"• **{nome}** ({cidade})\n"

    # Se a lista estiver vazia por algum erro de processamento
    if not termos_lista:
        termos_lista = "Nenhum termo processado."

    await update.message.reply_text(
        f"📝 **Seus nomes monitorados:**\n\n{termos_lista}", 
        parse_mode='Markdown'
    )

# Comando para remover um termo específico
# 1. O Comando principal /remover
async def remover(update, context):
    chat_id = update.effective_chat.id
    args = context.args

    # CASO 1: /remover NOME CIDADE (Ex: /remover ELENA SERRA)
    if len(args) >= 2:
        cidade = args[-1].upper()
        nome = " ".join(args[:-1]).upper()
        if remove_user_term(chat_id, nome, cidade):
            await update.message.reply_text(f"✅ Termo **{nome}** ({cidade}) removido!")
        else:
            await update.message.reply_text("❌ Não encontrei esse termo nessa cidade.")
        return

    # CASO 2: /remover NOME (Ex: /remover ELENA)
    if len(args) == 1:
        nome = args[0].upper()
        await mostrar_botoes_cidade_remocao(update, nome)
        return

    # CASO 3: /remover (Sem argumentos)
    await update.message.reply_text("🤔 Qual nome você deseja remover da sua lista?")
    context.user_data['esperando_nome_remocao'] = True

async def mostrar_botoes_cidade_remocao(update, nome_digitado):
    chat_id = update.effective_chat.id
    termos_do_banco = get_user_terms(chat_id)
    # O que o usuário digitou limpo para comparação
    nome_search = nome_digitado.upper().strip().replace("*", "")

    # Lista para armazenar dicionários com {cidade, nome_original_no_banco}
    opcoes_encontradas = []
    
    for t in termos_do_banco:
        nome_original = ""
        cidade_original = ""
        
        if isinstance(t, dict):
            nome_original = t.get('nome', '')
            cidade_original = t.get('cidade', 'SERRA')
        else:
            nome_original = str(t)
            cidade_original = "SERRA"

        # Comparamos o nome do banco (sem asteriscos) com a busca
        if nome_original.upper().replace("*", "").strip() == nome_search:
            opcoes_encontradas.append({
                "cidade": cidade_original,
                "nome_real": nome_original # Mantemos os asteriscos aqui para o delete
            })

    if not opcoes_encontradas:
        await update.message.reply_text(f"❌ O nome **{nome_digitado}** não foi encontrado na sua lista.")
        return

    # Criamos os botões
    keyboard = []
    for opcao in opcoes_encontradas:
        nome_real = opcao['nome_real']
        cid = opcao['cidade']
        # O callback_data envia o nome real (com asterisco se tiver) para a remoção no banco funcionar
        keyboard.append([
            InlineKeyboardButton(
                f"Remover de {cid}", 
                callback_data=f"DEL:{nome_real}:{cid}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🗑 Encontrei **{nome_search}** em {len(opcoes_encontradas)} cidade(s).\nQual deseja remover?",
        reply_markup=reply_markup
    )

async def callback_remover(update, context):
    query = update.callback_query
    await query.answer()
    
    # O dado vem do botão: "DEL:NOME:CIDADE"
    data = query.data.split(":")
    if len(data) < 3:
        await query.edit_message_text("❌ Erro ao processar remoção.")
        return
        
    nome = data[1]
    cidade = data[2]
    chat_id = update.effective_chat.id

    # Chama o banco (que usa collection.update_one)
    if remove_user_term(chat_id, nome, cidade):
        await query.edit_message_text(f"✅ Sucesso! **{nome}** ({cidade}) foi removido.")
    else:
        await query.edit_message_text(f"❌ Termo não encontrado ou já removido.")

# 2. Handler para quando o usuário clicar no botão de confirmação da remoção
async def callback_remover(update, context):
    query = update.callback_query
    await query.answer()
    
    # Formato do data: "DEL:NOME:CIDADE"
    _, nome, cidade = query.data.split(":")
    chat_id = update.effective_chat.id

    if remove_user_term(chat_id, nome, cidade):
        await query.edit_message_text(f"✅ Sucesso! **{nome}** ({cidade}) foi removido.")
    else:
        await query.edit_message_text(f"❌ Erro: O termo **{nome}** não estava cadastrado em {cidade}.")

# 3. Ajuste no MessageHandler para capturar o nome se ele digitar sozinho
async def resposta_padrao(update, context):
    chat_id = update.effective_chat.id
    texto = update.message.text.upper().strip()

    # Se o bot estiver esperando um nome para remover
    if context.user_data.get('esperando_nome_remocao'):
        context.user_data['esperando_nome_remocao'] = False
        # Redireciona para a lógica de escolher a cidade
        context.args = [texto]
        await remover(update, context)
        return

    # ... seu código atual de resposta_padrao continua aqui embaixo ...


async def monitorar(update, context):
    termo = " ".join(context.args).strip()
    if not termo:
        await update.message.reply_text("❌ Exemplo: `/monitorar MARIA RANGEL`", parse_mode='Markdown')
        return

    # Guarda o termo temporariamente no contexto do usuário
    context.user_data['termo_pendente'] = termo

    # Cria os botões
    keyboard = [
        [
            InlineKeyboardButton("Serra", callback_data='SERRA'),
            InlineKeyboardButton("Vitória", callback_data='VITORIA')
        ],
        [
            InlineKeyboardButton("Vila Velha", callback_data='VILA_VELHA'),
            InlineKeyboardButton("Cariacica", callback_data='CARIACICA')
        ],
        [InlineKeyboardButton("🌍 Todos os Diários", callback_data='TODOS')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🔍 Onde você deseja monitorar o termo **{termo}**?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Função que captura o clique no botão
async def callback_monitorar(update, context):
    query = update.callback_query
    await query.answer()
    
    cidade = query.data
    termo = context.user_data.get('termo_pendente')
    chat_id = update.effective_chat.id
    username = update.effective_user.username

    if termo:
        add_term(chat_id, username, termo, cidade)
        await query.edit_message_text(
            text=f"✅ Sucesso! Agora vigiando **{termo}** em **{cidade}**."
        )
    else:
        await query.edit_message_text(text="❌ Erro na sessão. Tente /monitorar novamente.")

async def som(update, context):
    await update.message.reply_text("🔔 Testando som...", disable_notification=False)

async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        total_users, total_alerts, top_terms = get_admin_stats()
        
        linhas_top = []
        for t in top_terms:
            raw_id = t['_id']
            
            # Se o ID for um dicionário (formato novo), pegamos apenas o campo 'nome'
            if isinstance(raw_id, dict):
                nome_base = raw_id.get('nome', 'Sem Nome')
            else:
                # Se for string (formato antigo)
                nome_base = str(raw_id)
            
            # Limpa caracteres que quebram o Markdown do Telegram
            nome_limpo = nome_base.replace("*", "").replace("_", " ")
            linhas_top.append(f"🔥 {nome_limpo}: `{t['count']}`")
        
        texto_top = "\n".join(linhas_top) if linhas_top else "Nenhum termo relevante."

        mensagem = (
            "📊 **Estatísticas Reais**\n\n"
            f"👥 Usuários: `{total_users}`\n"
            f"🔔 Alertas Enviados: `{total_alerts}`\n\n"
            "🔝 **Top Termos:**\n"
            f"{texto_top}"
        )
        await update.message.reply_text(mensagem, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Erro ao exibir stats: {e}")
        await update.message.reply_text("❌ Erro técnico ao processar estatísticas.")

# --- TAREFA ESPECÍFICA: SERRA ---
async def tarefa_busca_serra(app):
    logging.info("🔎 [SERRA] Iniciando busca de termos...")
    subs = get_all_subscriptions()
    
    for sub in subs:
        chat_id = sub['chat_id']
        for t in sub['terms']:
            # Lógica para separar o texto do dicionário
            if isinstance(t, dict):
                termo_para_busca = t['nome']
                cidade_do_termo = t.get('cidade', 'SERRA')
            else:
                termo_para_busca = t
                cidade_do_termo = 'SERRA'

            # Só busca se for Serra ou Todos
            if cidade_do_termo in ['SERRA', 'TODOS']:
                # MUITO IMPORTANTE: Passar apenas termo_para_busca
                resultados = await check_term_ioes(termo_para_busca) 
                await processar_resultados(app, chat_id, termo_para_busca, resultados, "SERRA")

# --- TAREFA ESPECÍFICA: VITÓRIA ---
async def tarefa_busca_vitoria_pmv(app):
    logging.info("🔎 [PMV-VITÓRIA] Iniciando busca otimizada...")
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    # 1. Pegamos todos os usuários
    subs = get_all_subscriptions()
    if not subs:
        return

    # 2. Criamos uma lista ÚNICA de todos os nomes que precisam ser buscados em Vitória
    # Isso evita baixar o PDF várias vezes.
    todos_termos_vitoria = set()
    for sub in subs:
        for t in sub['terms']:
            # Verifica se o termo é para Vitoria ou para Todos
            if t['cidade'] in ['VITORIA', 'TODOS']:
                todos_termos_vitoria.add(t['nome'])

    if not todos_termos_vitoria:
        logging.info("ℹ️ Nenhum termo cadastrado para Vitória hoje.")
        return

    # 3. Baixamos o PDF UMA ÚNICA VEZ e buscamos todos os termos de uma vez
    # Convertemos o set em lista para o scraper
    resultados_globais = buscar_vitoria_completo(hoje, list(todos_termos_vitoria))

    if not resultados_globais:
        logging.info("✅ [PMV-VITÓRIA] Busca finalizada: Nenhum termo encontrado no PDF.")
        return

    # 4. Agora distribuímos os resultados para os usuários certos
    for sub in subs:
        chat_id = sub['chat_id']
        termos_deste_usuario = [t['nome'] for t in sub['terms'] if t['cidade'] in ['VITORIA', 'TODOS']]
        
        for res in resultados_globais:
            # Se o resultado encontrado pertence a este usuário
            if res['termo'] in termos_deste_usuario:
                identificador_unico = f"{res['link']}_{res['pagina']}_{res['termo']}"
                
                if not ja_foi_notificado(chat_id, identificador_unico):
                    msg = (
                        f"🔔 **Resultado Encontrado em VITÓRIA!**\n\n"
                        f"👤 Termo: {res['termo']}\n"
                        f"📄 Página: {res['pagina']}\n"
                        f"🔗 [Abrir Diário Oficial](https://diariooficial.vitoria.es.gov.br/)"
                    )
                    try:
                        await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logging.error(f"Erro ao enviar para {chat_id}: {e}")

    logging.info("✅ [PMV-VITÓRIA] Busca e notificações finalizadas.")

# --- TAREFA ESPECÍFICA: VILA VELHA ---
async def tarefa_busca_vila_velha(app):
    logging.info("🔎 [VILA VELHA] Iniciando busca na última edição...")
    subs = get_all_subscriptions()
    if not subs: return

    todos_termos_vv = set()
    for sub in subs:
        for t in sub['terms']:
            if isinstance(t, dict):
                if t.get('cidade') in ['VILA_VELHA', 'TODOS']:
                    todos_termos_vv.add(t['nome'])
            elif isinstance(t, str):
                # Para termos antigos, buscamos em todos por segurança
                todos_termos_vv.add(t.upper())

    if not todos_termos_vv:
        return

    # Chama o scraper
    resultados_globais = buscar_vila_velha_completo(list(todos_termos_vv))

    for sub in subs:
        chat_id = sub['chat_id']
        
        # Filtra os termos deste usuário específico de forma segura
        termos_usuario = []
        for t in sub['terms']:
            if isinstance(t, dict):
                if t.get('cidade') in ['VILA_VELHA', 'TODOS']:
                    termos_usuario.append(t['nome'])
            elif isinstance(t, str):
                termos_usuario.append(t.upper())

        for res in resultados_globais:
            if res['termo'] in termos_usuario:
                # Criamos um identificador único com a data para não repetir o alerta hoje
                data_hoje = datetime.now().strftime('%Y-%m-%d')
                identificador = f"VV_{res['termo']}_{res['pagina']}_{data_hoje}"
                
                if not ja_foi_notificado(chat_id, identificador):
                    msg = (
                        f"🔔 **Resultado Encontrado em VILA VELHA!**\n\n"
                        f"👤 Termo: {res['termo']}\n"
                        f"📄 Página: {res['pagina']}\n"
                        f"🔗 [Abrir Portal Vila Velha]({res['link']})"
                    )
                    try:
                        await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logging.error(f"Erro ao notificar chat {chat_id}: {e}")

    logging.info("✅ [VILA VELHA] Busca finalizada.")

# Mantenha a função auxiliar processar_resultados como está
async def processar_resultados(app, chat_id, term, resultados, cidade):
    if isinstance(resultados, list) and resultados:
        for item in resultados:
            if not ja_foi_notificado(chat_id, item['link']):
                msg = (
                    f"🔔 **Resultado Encontrado em {cidade}!**\n\n"
                    f"👤 Termo: {term}\n"
                    f"📄 Página: {item['pagina']}\n"
                    f"🔗 [Abrir Diário]({item['link']})"
                )
                try:
                    await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                except Exception as e:
                    logging.error(f"Erro ao notificar {chat_id} ({cidade}): {e}")

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

# --- FUNÇÕES AUXILIARES ---
async def consultar_resumo(update, context):
    """
    Comando /resumo [data]
    Exemplo: /resumo 09/04/2026
    """
    # Pega o argumento enviado após o comando
    args = context.args
    
    if not args:
        # Se o usuário não digitar a data, podemos mostrar as últimas datas disponíveis
        ultimas = get_ultimas_datas_resumo(5)
        datas_str = "\n".join([f"• `/resumo {d}`" for d in ultimas])
        
        msg = (
            "⚠️ **Por favor, informe uma data.**\n\n"
            "Exemplo: `/resumo 10/04/2026`\n\n"
            f"📅 **Últimos resumos disponíveis:**\n{datas_str}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    data_pedida = args[0].strip()
    
    # Busca no banco de dados usando sua função existente
    resumo = buscar_resumo_por_data(data_pedida)
    
    if resumo:
        # Envia o resumo encontrado (removendo parse_mode para evitar erros de caracteres)
        await update.message.reply_text(
            f"📅 **RESUMO DE {data_pedida}:**\n\n{resumo}"
        )
    else:
        await update.message.reply_text(
            f"❌ Não encontrei nenhum resumo para a data **{data_pedida}**.\n"
            "Verifique se o formato é DD/MM/AAAA.",
            parse_mode='Markdown'
        )
# --- INICIALIZAÇÃO ---

async def post_init(application):
    # ... (seu código de set_my_commands continua igual)

    scheduler = AsyncIOScheduler()

    # TAREFAS AGENDADAS COM CRON
    
# Se agora são 17:52, teste com 17:55 para dar tempo de iniciar
    scheduler.add_job(tarefa_busca_serra, 'cron', hour=10, minute=48, args=[application])
    scheduler.add_job(tarefa_busca_vitoria_pmv, 'cron', hour=10, minute=55, args=[application])
    scheduler.add_job(tarefa_busca_vila_velha, 'cron', hour=11, minute=1, args=[application])
    
    scheduler.start()
    logging.info("⏰ Scheduler iniciado no modo CRON (Horários fixos).")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # --- 1. COMANDOS ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitorar", monitorar))
    app.add_handler(CommandHandler("meustermos", meus_termos))
    app.add_handler(CommandHandler("remover", remover))
    app.add_handler(CommandHandler("resumo", consultar_resumo))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("som", som))

    # --- 2. CALLBACKS DE BOTÕES (ORDEM É CRÍTICA) ---
    
    # Primeiro: Trata botões de REMOVER (que começam com DEL:)
    app.add_handler(CallbackQueryHandler(callback_remover, pattern="^DEL:"))

    # Segundo: Trata botões de MONITORAR (Cidades puras)
    app.add_handler(CallbackQueryHandler(callback_monitorar, pattern="^(SERRA|VITORIA|VILA_VELHA|CARIACICA|TODOS)$"))

    # --- 3. MENSAGENS DE TEXTO (SEMPRE POR ÚLTIMO) ---
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), resposta_padrao))

    logging.info("🚀 Bot iniciando...")
    app.run_polling()