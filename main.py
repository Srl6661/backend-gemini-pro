from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import uuid
import hmac
import hashlib

app = Bottle()

# TOKEN DE PRODUÇÃO DO MERCADO PAGO — nunca deixe escrito aqui.
# Configure a variável de ambiente ACCESS_TOKEN no painel do Render (Settings > Environment).
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise RuntimeError(
        "Variável de ambiente ACCESS_TOKEN não definida. "
        "Configure-a no Render com o token de produção do Mercado Pago."
    )
sdk = mercadopago.SDK(ACCESS_TOKEN)

# Chave secreta usada só pra gerar o código de pedido (referência que o cliente te manda no WhatsApp).
SECRET_KEY = os.environ.get('SECRET_KEY', 'troque-essa-chave-em-producao')

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'


def gerar_codigo_pedido(payment_id):
    """Código curto que o cliente te manda no WhatsApp pra você achar o pagamento dele."""
    assinatura = hmac.new(SECRET_KEY.encode(), str(payment_id).encode(), hashlib.sha256).hexdigest()[:8].upper()
    return f"GP-{assinatura}"


def validar_codigo_pedido(payment_id, codigo):
    return hmac.compare_digest(gerar_codigo_pedido(payment_id), codigo or "")


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

    # 1. Recebe os dados dinâmicos da nova vitrine do site
    produto = dados.get("produto", "Serviço de Tecnologia")
    quantidade = dados.get("quantidade", 1)
    
    # Tenta converter o valor total de forma segura
    try:
        valor_total = float(dados.get("valor_total", 0))
    except (ValueError, TypeError):
        return {"error": "Valor inválido enviado pelo site."}

    # Trava de segurança: impede gerar Pix zerado
    if valor_total <= 0:
        return {"error": "O valor da transação deve ser maior que zero."}

    # 2. Descrição dinâmica pro seu extrato do Mercado Pago
    descricao_dinamica = f"{quantidade}x {produto}"

    # 3. Email fantasma: O MP exige, mas pra encurtar o tempo do cliente, geramos um automaticamente
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    run(app, host='0.0.0.0', port=port)
