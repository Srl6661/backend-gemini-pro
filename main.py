from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import uuid
import hmac
import hashlib
import asyncio
import re
import requests
import threading
import json
from telethon import TelegramClient

app = Bottle()

# --- CONFIGURAÇÕES MERCADO PAGO ---
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise RuntimeError(
        "Variável de ambiente ACCESS_TOKEN não definida. "
        "Configure-a no Render com o token de produção do Mercado Pago."
    )
sdk = mercadopago.SDK(ACCESS_TOKEN)
SECRET_KEY = os.environ.get('SECRET_KEY', 'troque-essa-chave-em-producao')

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'


def gerar_codigo_pedido(payment_id):
    assinatura = hmac.new(SECRET_KEY.encode(), str(payment_id).encode(), hashlib.sha256).hexdigest()[:8].upper()
    return f"GP-{assinatura}"


def validar_codigo_pedido(payment_id, codigo):
    return hmac.compare_digest(gerar_codigo_pedido(payment_id), codigo or "")

# --- ROTAS DO MERCADO PAGO ---
@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))


@app.route('/gerar-pix', method=['POST', 'OPTIONS'])
def gerar_pix():
    if request.method == 'OPTIONS':
        return {}

    dados = request.json or {}
    client_id = dados.get("client_id", "")
    if not client_id:
        return {"error": "client_id obrigatório"}

    produto = dados.get("produto", "Serviço de Tecnologia")
    quantidade = dados.get("quantidade", 1)
    
    try:
        valor_total = float(dados.get("valor_total", 0))
    except (ValueError, TypeError):
        return {"error": "Valor inválido enviado pelo site."}

    if valor_total <= 0:
        return {"error": "O valor da transação deve ser maior que zero."}

    descricao_dinamica = f"{quantidade}x {produto}"
    email_fantasma = f"comprador_{client_id[:8]}@tecnologia.com"

    payment_data = {
        "transaction_amount": valor_total,
        "description": descricao_dinamica,
        "payment_method_id": "pix",
        "external_reference": client_id,
        "payer": {
            "email": email_fantasma
        }
    }

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        'x-idempotency-key': str(uuid.uuid4())
    }

    result = sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})

    if "id" not in payment:
        return {"error": "Erro ao gerar PIX com o Banco.", "detalhes": payment}

    transaction_data = payment.get("point_of_interaction", {}).get("transaction_data", {})

    return {
        "id_pagamento_mp": str(payment["id"]),
        "copia_e_cola": transaction_data.get("qr_code", ""),
        "qr_code_base64": transaction_data.get("qr_code_base64", "")
    }


@app.route('/status/<id>', method=['GET', 'OPTIONS'])
def status_pagamento(id):
    if request.method == 'OPTIONS':
        return {}
    result = sdk.payment().get(id)
    payment = result.get("response", {})
    status = payment.get("status", "nao_encontrado")

    resposta = {"status": status}
    if status == "approved":
        resposta["codigo_pedido"] = gerar_codigo_pedido(id)
    return resposta


# --- INÍCIO DA AUTOMAÇÃO DO TELEGRAM ---
CATALOGO_ATUALIZADO = []
API_ID = 33561861
API_HASH = '457908461a1dca18edc5ae51418b2dd7'

def calcular_preco(nome, preco_usd, dolar_hoje):
    if "Gemini" in nome:
        return 60.00
    
    custo_reais = float(preco_usd) * dolar_hoje
    if float(preco_usd) <= 5.00:
        return custo_reais * 10.00
    else:
        return custo_reais * 7.00

async def varredura_telegram():
    client = TelegramClient('sessao_secundaria', API_ID, API_HASH)
    await client.connect()

    while True:
        try:
            req = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            dolar_hoje = float(req.json()['USDBRL']['bid'])

            await client.send_message('@GGSoma_bot', '/products')
            await asyncio.sleep(5) 
            
            mensagens = await client.get_messages('@GGSoma_bot', limit=1)
            texto = mensagens[0].text
            
            padrao = r"(?:🤖|✨|🎓)\s*(.*?)(?:\((\d+)\))?\n\s*💰\s*\$([\d\.]+)"
            itens = re.findall(padrao, texto)
            
            nova_lista = []
            for nome, estoque, preco_usd in itens:
                tem_estoque = False if estoque == "0" else True
                preco_final = calcular_preco(nome, preco_usd, dolar_hoje)
                
                nova_lista.append({
                    "id": nome.lower().replace(" ", "_")[:15],
                    "nome": nome.strip(),
                    "precoBase": preco_final,
                    "precoDisplay": f"R$ {preco_final:,.2f}".replace(".", ","),
                    "estoque": tem_estoque
                })
            
            global CATALOGO_ATUALIZADO
            CATALOGO_ATUALIZADO = nova_lista

        except Exception as e:
            print("Erro na varredura:", e)
        
        await asyncio.sleep(300)

def iniciar_robo_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(varredura_telegram())

thread = threading.Thread(target=iniciar_robo_background, daemon=True)
thread.start()

# Rota para o seu site puxar o catálogo gerado pelo robô
@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def entregar_site():
    if request.method == 'OPTIONS':
        return {}
    
    response.content_type = 'application/json'
    return json.dumps(CATALOGO_ATUALIZADO)
# --- FIM DA AUTOMAÇÃO DO TELEGRAM ---


# --- INICIALIZAÇÃO DO SERVIDOR (DEVE FICAR SEMPRE NO FINAL) ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    run(app, host='0.0.0.0', port=port)
async def varredura_telegram():
    client = TelegramClient('sessao_secundaria', API_ID, API_HASH)
    await client.connect()

    while True:
        try:
            req = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            dolar_hoje = float(req.json()['USDBRL']['bid'])

            await client.send_message('@GGSoma_bot', '/products')
            await asyncio.sleep(5) 
            
            mensagens = await client.get_messages('@GGSoma_bot', limit=1)
            texto = mensagens[0].text
            
            # --- NOVO MOTOR BLINDADO ANTIFALHAS ---
            # Removemos todos os emojis (qualquer coisa que não seja letra, número, ponto, vírgula, parênteses ou $)
            texto_limpo = re.sub(r'[^\w\s\.\,\(\)\$\-]', '', texto)
            
            # O Regex agora ignora emojis e símbolos:
            # 1. Pega textos que começam com letra ou número (Nome)
            # 2. Pega um número entre parênteses opcional (Estoque)
            # 3. Pula pra linha de baixo e acha o primeiro número com casa decimal (Preço)
            padrao = r"([a-zA-Z0-9].*?)(?:\s*\((\d+)\))?\s*\n.*?([\d]+[\.,][\d]+)"
            itens = re.findall(padrao, texto_limpo)
            
            nova_lista = []
            for nome, estoque, preco_str in itens:
                tem_estoque = False if estoque == "0" else True
                
                # Força a troca de vírgula por ponto para não quebrar a matemática
                preco_usd = float(preco_str.replace(',', '.'))
                preco_final = calcular_preco(nome, preco_usd, dolar_hoje)
                
                nova_lista.append({
                    "id": nome.lower().replace(" ", "_")[:15],
                    "nome": nome.strip(),
                    "precoBase": preco_final,
                    "precoDisplay": f"R$ {preco_final:,.2f}".replace(".", ","),
                    "estoque": tem_estoque
                })
            
            # Trava de segurança: só atualiza o site se conseguiu extrair produtos
            if len(nova_lista) > 0:
                global CATALOGO_ATUALIZADO
                CATALOGO_ATUALIZADO = nova_lista

        except Exception as e:
            print("Erro na varredura:", e)
        
        await asyncio.sleep(300)
