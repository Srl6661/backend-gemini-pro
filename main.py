from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import uuid
import hmac
import hashlib
import requests
import json

app = Bottle()

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PARTNER_API_KEY = os.environ.get('PARTNER_API_KEY')
SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao-123')
PARTNER_API_URL = "https://ggsoma.store/api/partner/v1"

if ACCESS_TOKEN:
    sdk = mercadopago.SDK(ACCESS_TOKEN)
else:
    print("AVISO: ACCESS_TOKEN não configurado.")

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

def gerar_codigo_pedido(payment_id):
    assinatura = hmac.new(SECRET_KEY.encode(), str(payment_id).encode(), hashlib.sha256).hexdigest()[:8].upper()
    return f"GP-{assinatura}"

# Dicionário invisível: Puxa o link do logo original, mas não exibe o texto no site
def obter_dominio_logo(nome_produto):
    nome = nome_produto.lower()
    if 'chatgpt' in nome or 'openai' in nome: return 'openai.com'
    if 'framer' in nome: return 'framer.com'
    if 'lovable' in nome: return 'lovable.dev'
    if 'magic patterns' in nome: return 'magicpatterns.com'
    if 'gamma' in nome: return 'gamma.app'
    if 'n8n' in nome: return 'n8n.io'
    if 'jam' in nome: return 'jam.dev'
    if 'linear' in nome: return 'linear.app'
    if 'gumloop' in nome: return 'gumloop.com'
    if 'elevenlabs' in nome: return 'elevenlabs.io'
    if 'supabase' in nome: return 'supabase.com'
    if 'replit' in nome: return 'replit.com'
    if 'granola' in nome: return 'granola.so'
    if 'railway' in nome: return 'railway.app'
    if 'posthog' in nome: return 'posthog.com'
    if 'mobbin' in nome: return 'mobbin.com'
    if 'runway' in nome: return 'runwayml.com'
    if 'chatprd' in nome: return 'chatprd.ai'
    if 'proton' in nome: return 'proton.me'
    if 'nord' in nome or 'vpn' in nome: return 'nordvpn.com'
    if 'quillbot' in nome: return 'quillbot.com'
    if 'linkedin' in nome or 'career' in nome: return 'linkedin.com'
    if 'telegram' in nome: return 'telegram.org'
    if 'duolingo' in nome: return 'duolingo.com'
    if 'bolt' in nome: return 'bolt.new'
    if 'canva' in nome: return 'canva.com'
    if 'google' in nome or 'gemini' in nome: return 'google.com'
    return 'ggsoma.store'

@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))

@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def get_catalogo():
    response.content_type = 'application/json'
    
    if request.method == 'OPTIONS':
        return json.dumps({})
    
    headers = {"Authorization": f"Bearer {PARTNER_API_KEY}"}
    try:
        resp = requests.get(f"{PARTNER_API_URL}/catalog/products", headers=headers)
        if resp.status_code != 200:
            return json.dumps([])
            
        produtos_fornecedor = resp.json().get("data", [])
        catalogo_tratado = []
        
        for p in produtos_fornecedor:
            if p.get("stock", {}).get("inStock", False):
                custo_usd = float(p.get("yourPrice", 0))
                preco_calculado = round((custo_usd * 6.00) + 75.40, 2)
                
                # Limpeza do nome: tira qualquer "None" que vem da loja parceira
                nome_limpo = str(p.get("name", "")).replace("None", "").strip()
                dominio_logo = obter_dominio_logo(nome_limpo)
                
                catalogo_tratado.append({
                    "id": p["slug"],
                    "nome": nome_limpo,
                    "precoBase": preco_calculado,
                    "logoDomain": dominio_logo,
                    "estoque": True,
                    "descricao": p.get("description", "")
                })
        return json.dumps(catalogo_tratado)
    except Exception as e:
        print(f"Erro ao buscar catálogo: {e}")
        return json.dumps([])

@app.route('/gerar-pix', method=['POST', 'OPTIONS'])
def gerar_pix():
    if request.method == 'OPTIONS':
        return {}

    dados = request.json or {}
    client_id = dados.get("client_id", "")
    produto_nome = dados.get("produto", "Serviço de Tecnologia")
    produto_id = dados.get("produto_id", "") 
    quantidade = dados.get("quantidade", 1)
    
    try:
        valor_total = float(dados.get("valor_total", 0))
    except (ValueError, TypeError):
        return {"error": "Valor inválido enviado pelo site."}

    if valor_total <= 0:
        return {"error": "O valor da transação deve ser maior que zero."}

    descricao_dinamica = f"{quantidade}x {produto_nome}"
    email_fantasma = f"comprador_{client_id[:8]}@tecnologia.com"

    payment_data = {
        "transaction_amount": valor_total,
        "description": descricao_dinamica,
        "payment_method_id": "pix",
        "external_reference": client_id,
        "payer": {
            "email": email_fantasma
        },
        "metadata": {
            "produto_id": produto_id,
            "quantidade": quantidade
        }
    }

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {'x-idempotency-key': str(uuid.uuid4())}

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
        
        produto_id = payment.get("metadata", {}).get("produto_id")
        quantidade = payment.get("metadata", {}).get("quantidade", 1)
        
        if produto_id and not produto_id.startswith("inst_"):
            headers = {
                "Authorization": f"Bearer {PARTNER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload_compra = {
                "productSlug": produto_id,
                "quantity": int(quantidade),
                "externalOrderId": str(id) 
            }
            
            try:
                compra_resp = requests.post(f"{PARTNER_API_URL}/orders", json=payload_compra, headers=headers)
                dados_compra = compra_resp.json()
                
                if dados_compra.get("ok"):
                    resposta["delivery"] = dados_compra.get("delivery", {})
                else:
                    resposta["erro_entrega"] = "Pagamento ok, mas falha na API parceira."
            except Exception as e:
                print(f"Erro de integração na compra: {e}")
            
    return resposta

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    run(app, host='0.0.0.0', port=port)
