from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import re
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

# Chave secreta usada só pra gerar o código de pedido (referência que o cliente te manda
# no WhatsApp). Configure SECRET_KEY como variável de ambiente em produção.
SECRET_KEY = os.environ.get('SECRET_KEY', 'troque-essa-chave-em-producao')

# Ajuste aqui o valor e a descrição da oferta.
VALOR_OFERTA = 60.00
DESCRICAO_OFERTA = "Gemini Pro - 18 meses"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'


def gerar_codigo_pedido(payment_id):
    """Código curto que o cliente te manda no WhatsApp pra você achar o pagamento dele.
    É assinado com HMAC, então ninguém consegue inventar um código válido na mão."""
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

    # Email de quem está comprando — nunca o seu, senão toda cobrança te notifica sobre si mesma.
    email_comprador = (dados.get("email") or "").strip()
    if not EMAIL_REGEX.match(email_comprador):
        return {"error": "Informe um email válido para gerar o Pix"}

    payment_data = {
        "transaction_amount": VALOR_OFERTA,
        "description": DESCRICAO_OFERTA,
        "payment_method_id": "pix",
        "external_reference": client_id,
        "payer": {
            "email": email_comprador
        }
    }

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        'x-idempotency-key': str(uuid.uuid4())
    }

    result = sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})

    if "id" not in payment:
        return {"error": "Erro ao gerar PIX", "detalhes": payment}

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
