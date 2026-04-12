from flask import logging
from pymongo import MongoClient
from datetime import datetime

# Substitua pela sua URL real do Atlas
MONGO_URI = "mongodb+srv://lucianohorta:Horta8808@cluster0.w48jn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['dioes_database']
collection = db['subscriptions']

# def add_term(chat_id, username, term):
#     collection.update_one(
#         {"chat_id": chat_id},
#         {
#             "$set": {"username": username, "last_update": datetime.now()},
#             "$addToSet": {"terms": term}
#         },
#         upsert=True
#     )


def add_term(chat_id, username, term, cidade="TODOS"):
    # Salva o termo com a cidade escolhida
    novo_termo = {"nome": term.upper(), "cidade": cidade.upper()}
    
    collection.update_one(
        {"chat_id": chat_id},
        {
            "$set": {"username": username, "last_update": datetime.now()},
            "$addToSet": {"terms": novo_termo}
        },
        upsert=True
    )

def remove_term(chat_id, term):
    collection.update_one(
        {"chat_id": chat_id},
        {"$pull": {"terms": term}}
    )

def remove_user_term(chat_id, nome_termo, cidade_termo):
    """
    Remove um termo específico de uma cidade específica para o usuário.
    """
    termo_obj = {"nome": nome_termo.upper(), "cidade": cidade_termo.upper()}
    
    # Aqui estava o erro: mudado de users_collection para collection
    result = collection.update_one(
        {"chat_id": chat_id},
        {"$pull": {"terms": termo_obj}}
    )
    return result.modified_count > 0

def get_admin_stats():
    """Retorna estatísticas consolidadas e limpas"""
    total_usuarios = collection.count_documents({})
    total_alertas = db['alerts_history'].count_documents({})
    
    pipeline = [
        {"$unwind": "$terms"},
        {
            "$project": {
                "termo_limpo": {
                    "$cond": {
                        # Se for um dicionário, pega o campo 'nome', senão usa a própria string
                        "if": {"$eq": [{"$type": "$terms"}, "object"]},
                        "then": "$terms.nome",
                        "else": "$terms"
                    }
                }
            }
        },
        {"$group": {"_id": "$termo_limpo", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    
    try:
        top_termos = list(collection.aggregate(pipeline))
    except Exception as e:
        logging.error(f"Erro no aggregate: {e}")
        top_termos = []
        
    return total_usuarios, total_alertas, top_termos

# ESTA É A FUNÇÃO QUE ESTAVA FALTANDO OU COM NOME ERRADO:
def get_user_terms(chat_id):
    user = collection.find_one({"chat_id": chat_id})
    if user and "terms" in user:
        return user["terms"]
    return []

def get_all_subscriptions():
    return list(collection.find({}))

def get_subscription(chat_id):
    """Busca os dados do usuário no banco"""
    return collection.find_one({"chat_id": chat_id})

def get_subscription(chat_id):
    """Busca os dados do usuário no banco"""
    return collection.find_one({"chat_id": chat_id})

def remove_term(chat_id, term):
    """Remove um termo específico da lista do usuário"""
    result = collection.update_one(
        {"chat_id": chat_id},
        {"$pull": {"terms": term}}
    )
    # Retorna True se algo foi removido, False se não
    return result.modified_count > 0

def get_admin_stats():
    """Retorna números totais para o administrador"""
    total_usuarios = collection.count_documents({})
    # Conta quantos alertas já foram disparados na história
    total_alertas = db['alerts_history'].count_documents({})
    
    # Busca os 5 termos mais monitorados (opcional, mas legal!)
    pipeline = [
        {"$unwind": "$terms"},
        {"$group": {"_id": "$terms", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_termos = list(collection.aggregate(pipeline))
    
    return total_usuarios, total_alertas, top_termos

# Função extra para evitar duplicados (o "Pulo do Gato")
def ja_foi_notificado(chat_id, link):
    alerta = db['alerts_history'].find_one({"chat_id": chat_id, "link": link})
    if alerta:
        return True
    db['alerts_history'].insert_one({
        "chat_id": chat_id, 
        "link": link, 
        "date": datetime.now()
    })
    return False


# Funções para salvar e buscar resumos diários no banco
def salvar_resumo_no_banco(data_str, texto_resumo):
    """Guarda o resumo do dia no MongoDB"""
    # 'data_str' deve vir no formato '09/04/2026'
    db.resumos.update_one(
        {"data": data_str},
        {"$set": {"texto": texto_resumo}},
        upsert=True
    )

def buscar_resumo_por_data(data_str):
    """Busca o resumo de uma data específica"""
    resultado = db.resumos.find_one({"data": data_str})
    return resultado['texto'] if resultado else None

# Função para pegar as últimas datas que possuem resumos (para evitar erros de data)
def get_ultimas_datas_resumo(limite=5):
    """Retorna as últimas datas que possuem resumo salvo, em ordem decrescente"""
    # Buscamos todos os resumos, ordenamos pelo ID (que no Mongo reflete a ordem de criação)
    # ou podemos ordenar por data se elas estiverem em formato comparável.
    # Como as datas são strings 'DD/MM/AAAA', vamos pegar as mais recentes inseridas:
    cursor = db.resumos.find({}, {"data": 1}).sort("_id", -1).limit(limite)
    return [doc['data'] for doc in cursor]

#line

#line

