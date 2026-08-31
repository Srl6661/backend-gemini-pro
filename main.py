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
from telethon.errors import SessionPasswordNeededError

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


# --- INÍCIO DA AUTOMAÇÃO DO TELEGRAM (MOTOR BLINDADO) ---
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

def gerar_id_produto(nome_limpo):
    # Hash estável em vez de truncar o nome: evita dois produtos diferentes
    # colidirem no mesmo id quando os 15 primeiros caracteres são iguais.
    slug = re.sub(r"[^a-z0-9]+", "_", nome_limpo.lower()).strip("_")[:30]
    assinatura = hashlib.md5(nome_limpo.encode()).hexdigest()[:6]
    return f"{slug}_{assinatura}"


async def buscar_dolar_hoje():
    try:
        req = requests.get(
            "https://economia.awesomeapi.com.br/last/USD-BRL",
            timeout=10
        )
        req.raise_for_status()
        return float(req.json()['USDBRL']['bid'])
    except Exception as e:
        print("Falha ao buscar cotação do dólar, usando fallback:", e)
        return 5.50  # valor de segurança para não travar o pipeline inteiro


async def varredura_telegram():
    client = TelegramClient('sessao_secundaria', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("ERRO CRÍTICO: sessão do Telegram não está autorizada. "
              "Confira se o arquivo 'sessao_secundaria.session' é o correto "
              "e foi gerado com essa mesma API_ID/API_HASH.")

    while True:
        try:
            dolar_hoje = await buscar_dolar_hoje()
            texto = None

            async with client.conversation('@GGSoma_bot', timeout=30) as conv:
                await conv.send_message('/products')
                menu = await conv.get_response()

                # Procura o botão "Available"/"Products" no teclado inline
                botao = None
                if menu.buttons:
                    for linha in menu.buttons:
                        for btn in linha:
                            rotulo = (btn.text or "").lower()
                            if "available" in rotulo or "products" in rotulo:
                                botao = btn
                                break
                        if botao:
                            break

                if botao is None:
                    # Bot já mandou o texto puro, sem precisar clicar em nada
                    texto = menu.text
                else:
                    await botao.click()

                    # O bot pode EDITAR a msg do menu OU mandar uma NOVA.
                    # Espera os dois em paralelo e usa o que chegar primeiro.
                    tarefa_edicao = asyncio.create_task(conv.wait_edit(menu.id))
                    tarefa_nova = asyncio.create_task(conv.get_response())

                    concluidas, pendentes = await asyncio.wait(
                        {tarefa_edicao, tarefa_nova},
                        timeout=15,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for pendente in pendentes:
                        pendente.cancel()
                        try:
                            await pendente
                        except (asyncio.CancelledError, Exception):
                            pass

                    if concluidas:
                        texto = concluidas.pop().result().text
                    else:
                        print("Timeout esperando a lista aparecer após o clique.")

            if not texto:
                raise ValueError("Nenhum texto de lista recebido do bot.")

            # Motor blindado: Nome | $Preço | (Estoque)
            padrao = r"(.*?)\s*\|\s*\$([\d\.]+)\s*\|\s*\((\d+)\)"
            itens = re.findall(padrao, texto)

            nova_lista = []
            for nome, preco_usd_str, estoque in itens:
                nome_limpo = nome.strip()
                if not nome_limpo or "bot shop" in nome_limpo.lower():
                    continue

                tem_estoque = False if estoque == "0" else True
                preco_usd = float(preco_usd_str)
                preco_final = calcular_preco(nome_limpo, preco_usd, dolar_hoje)

                nova_lista.append({
                    "id": gerar_id_produto(nome_limpo),
                    "nome": nome_limpo,
                    "precoBase": preco_final,
                    "precoDisplay": f"R$ {preco_final:,.2f}".replace(".", ","),
                    "estoque": tem_estoque
                })

            # Trava de segurança: só atualiza se extraiu produtos com sucesso
            if len(nova_lista) > 0:
                global CATALOGO_ATUALIZADO
                CATALOGO_ATUALIZADO = nova_lista
            else:
                print("Regex não encontrou itens no texto recebido:", texto[:200])

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
