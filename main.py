from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import uuid
import hmac
import hashlib
import requests
import json
import re

app = Bottle()

# 🔑 Chaves de API das CINCO plataformas
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PARTNER_API_KEY = os.environ.get('PARTNER_API_KEY') 
CANBOSO_API_KEY = os.environ.get('CANBOSO_API_KEY') 
BUNAI_API_KEY = os.environ.get('BUNAI_API_KEY')     
OPTIMUS_API_KEY = os.environ.get('OPTIMUS_API_KEY') 
NIMO_API_KEY = os.environ.get('NIMO_API_KEY')
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

# 🛡️ EXTRATORES INTELIGENTES
def extrair_preco_usd(val, moeda_padrao="USD"):
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        limpo = re.sub(r'[^\d.]', '', val)
        try: return float(limpo) if limpo else 0.0
        except: return 0.0
    if isinstance(val, dict):
        moeda = str(val.get("currency", moeda_padrao)).upper()
        for k in ["amount", "price", "unit_price", "effective_price", "value", "usd", "base_price"]:
            if k in val and val[k] is not None:
                v = extrair_preco_usd(val[k])
                if v > 0:
                    return v / 25000.0 if moeda == "VND" else v
    return 0.0

def extrair_estoque(p):
    if p.get("infinite_stock") is True or str(p.get("infinite_stock")).lower() == "true": return True
    if p.get("delivery_mode") == "manual" or p.get("stock_type") == "manual": return True
    
    if isinstance(p.get("stock"), dict):
        if p["stock"].get("inStock") is True: return True
        if p["stock"].get("available", 0) > 0: return True

    if isinstance(p.get("availability"), dict):
        av = p["availability"].get("available")
        if av is None or av == -1 or str(av) == "∞": return True
        try:
            if int(av) > 0: return True
        except: pass

    if isinstance(p.get("stats"), dict):
        av = p["stats"].get("available")
        if av is not None:
            try:
                if int(av) > 0: return True
            except: pass

    if isinstance(p.get("credit_tiers"), list) and len(p.get("credit_tiers")) > 0:
        for tier in p["credit_tiers"]:
            try:
                if int(tier.get("count", 0)) > 0: return True
            except: pass

    for k in ["stock", "stock_count", "available"]:
        val = p.get(k)
        if val is not None and not isinstance(val, dict):
            if str(val) == "∞" or val == -1: return True
            try:
                if int(val) > 0: return True
            except: pass

    return False

def gerar_codigo_pedido(payment_id):
    assinatura = hmac.new(SECRET_KEY.encode(), str(payment_id).encode(), hashlib.sha256).hexdigest()[:8].upper()
    return f"GP-{assinatura}"

def obter_dominio_logo(nome_produto):
    nome = nome_produto.lower()
    if 'chatgpt' in nome or 'openai' in nome: return 'openai.com'
    if 'framer' in nome: return 'framer.com'
    if 'lovable' in nome: return 'lovable.dev'
    if 'magic patterns' in nome or 'magic' in nome: return 'magicpatterns.com'
    if 'gamma' in nome: return 'gamma.app'
    if 'n8n' in nome: return 'n8n.io'
    if 'jam' in nome: return 'jam.dev'
    if 'linear' in nome: return 'linear.app'
    if 'gumloop' in nome: return 'gumloop.com'
    if 'elevenlabs' in nome or 'eleven' in nome: return 'elevenlabs.io'
    if 'supabase' in nome: return 'supabase.com'
    if 'replit' in nome: return 'replit.com'
    if 'granola' in nome: return 'granola.so'
    if 'railway' in nome: return 'railway.app'
    if 'posthog' in nome: return 'posthog.com'
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
    if 'capcut' in nome: return 'capcut.com'
    if 'grok' in nome: return 'x.ai'
    if 'coursera' in nome: return 'coursera.org'
    if 'youtube' in nome: return 'youtube.com'
    if 'cursor' in nome: return 'cursor.com'
    if 'notion' in nome: return 'notion.so'
    if 'arize' in nome: return 'arize.com'
    if 'airtable' in nome: return 'airtable.com'
    if 'descript' in nome: return 'descript.com'
    if 'wispr' in nome: return 'wisprflow.ai'
    if 'leonardo' in nome: return 'leonardo.ai'
    if 'adobe' in nome: return 'adobe.com'
    if 'higgsfield' in nome: return 'higgsfield.ai'
    if 'crunchyroll' in nome: return 'crunchyroll.com'
    if 'mobbin' in nome: return 'mobbin.com'
    if 'microsoft' in nome or 'ms office' in nome or 'windows' in nome or 'office' in nome: return 'microsoft.com'
    if 'gmail' in nome or 'google' in nome or 'gemini' in nome: return 'google.com'
    if 'manus' in nome: return 'manus.com'
    if 'warp' in nome: return 'warp.dev'
    if 'memrise' in nome: return 'memrise.com'
    if 'resend' in nome: return 'resend.com'
    if 'supercut' in nome: return 'supercut.ai'
    if 'intercom' in nome: return 'intercom.com'
    if 'kaspersky' in nome: return 'kaspersky.com'
    if 'discord' in nome: return 'discord.com'
    if 'grammarly' in nome: return 'grammarly.com'
    if 'kahoot' in nome: return 'kahoot.com'
    if 'roblox' in nome: return 'roblox.com'
    if 'spotify' in nome: return 'spotify.com'
    if 'zoom' in nome: return 'zoom.us'
    if 'autodesk' in nome or 'autocad' in nome: return 'autodesk.com'
    if 'ilovepdf' in nome: return 'ilovepdf.com'
    if 'figma' in nome: return 'figma.com'
    if 'netflix' in nome: return 'netflix.com'
    if 'prime' in nome or 'amazon' in nome: return 'amazon.com'
    if 'claude' in nome or 'anthropic' in nome: return 'anthropic.com'
    if 'codex' in nome: return 'openai.com'
    if 'muse' in nome: return 'muse.ai'
    if 'quizlet' in nome: return 'quizlet.com'
    if 'reddit' in nome: return 'reddit.com'
    if 'skillshare' in nome: return 'skillshare.com'
    if 'vieon' in nome: return 'vieon.vn'
    if 'wink' in nome: return 'wink.com'
    return 'tech.com' 

def obter_categoria(nome_produto):
    nome = nome_produto.lower()
    if any(x in nome for x in ['chatgpt', 'gemini', 'google pro', 'google ai', 'chatprd', 'manus', 'grok', 'cursor', 'wispr', 'magic', 'supercut', 'pangram', 'claude', 'perplexity', 'midjourney', 'leonardo', 'codex', 'muse']): 
        return 'Inteligência Artificial'
    if any(x in nome for x in ['canva', 'framer', 'runway', 'elevenlabs', 'eleven', 'mobbin', 'capcut', 'descript', 'adobe', 'higgsfield', 'autodesk', 'autocad', 'figma', 'wink']): 
        return 'Design & Criatividade'
    if any(x in nome for x in ['supabase', 'replit', 'railway', 'bolt', 'lovable', 'arize', 'warp', 'resend', 'api credits']): 
        return 'Desenvolvimento'
    if any(x in nome for x in ['n8n', 'gumloop']): 
        return 'Automação'
    if any(x in nome for x in ['telegram', 'linkedin', 'proton', 'nord', 'vpn', 'kaspersky', 'windows']): 
        return 'Redes & Segurança'
    if any(x in nome for x in ['duolingo', 'quillbot', 'coursera', 'memrise', 'grammarly', 'kahoot', 'quizlet', 'skillshare']): 
        return 'Educação & Idiomas'
    if any(x in nome for x in ['gamma', 'jam', 'linear', 'posthog', 'notion', 'airtable', 'microsoft', 'ms office', 'office', 'gmail', 'intercom', 'ilovepdf', 'zoom', 'granola', 'reddit']): 
        return 'Produtividade'
    if any(x in nome for x in ['youtube', 'crunchyroll', 'discord', 'roblox', 'spotify', 'netflix', 'amazon', 'vieon']): 
        return 'Entretenimento'
    return 'Licença Premium'

def extrair_detalhes_seguros(desc_original, nome_lower=""):
    if not desc_original: return ""
    texto = str(desc_original)
    texto = re.sub(r'[<\{]*ce:\d+[>\}]*', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto_lower = texto.lower()
    avisos = []
    
    if 'vietnam' in texto_lower or 'vietnã' in texto_lower: avisos.append("Requer VPN (Vietnã) apenas no 1º acesso")
    elif 'india' in texto_lower or 'índia' in texto_lower: avisos.append("Requer VPN (Índia) apenas na ativação")
    elif 'vpn' in texto_lower and 'vpn' not in nome_lower: avisos.append("Pode requerer VPN na ativação")
        
    if any(x in texto_lower for x in ['own account', 'your account', 'sua conta', 'personal account']): avisos.append("Ativação direto na sua conta")
    elif any(x in texto_lower for x in ['new account', 'provided account', 'conta pronta', 'full account']): avisos.append("Conta pronta exclusiva enviada após a compra")
        
    if any(x in texto_lower for x in ['coupon', 'redeem code', 'voucher', 'cupom']): avisos.append("Ativação via Código/Cupom Oficial")
    if any(x in texto_lower for x in ['need card', 'requires card', 'precisa de cartão', 'credit card']): avisos.append("Requer cartão para ativar assinatura")
        
    match_garantia = re.search(r'(\d+)[-\s]*days?\s*warranty', texto_lower)
    if match_garantia and 'gemini' not in nome_lower and 'google' not in nome_lower:
        avisos.append(f"Garantia de {match_garantia.group(1)} dias")
        
    if avisos: return " 📌 Especificações: " + " • ".join(avisos) + "."
    return ""

def traduzir_e_resumir(nome_original, desc_original=""):
    nome_base = str(nome_original).replace("None", "").strip()
    nome_base = re.sub(r'[<\{]*ce:\d+[>\}]*', '', nome_base, flags=re.IGNORECASE)
    
    nome_base = re.sub(r'\b(CDK\s*FW|CDK\s*NW|CDK|FW|NW|W5D|W6D)\b', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\(NW\)|\(FW\)|\(W5D\)|\(W6D\))', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'Link to Receive\s*', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'REDEEM LINK\s*', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'>', '-', nome_base)
    nome_base = re.sub(r'\|', '-', nome_base)
    
    nome_base = re.sub(r'\b(\d+)\s*Years?\b', lambda m: f"{int(m.group(1))*12} meses", nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b1[-\s]*months?\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b1[-\s]*m\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)[-\s]*months?\b', r'\1 meses', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)[-\s]*m\b', r'\1 meses', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)[-\s]*d\b', r'\1 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)[-\s]*days?\b', r'\1 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)\s*seats?\b', r'\1 vagas', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b(\d+)\s*users?\b', r'\1 usuários', nome_base, flags=re.IGNORECASE)
    
    nome_base = re.sub(r'\s+', ' ', nome_base).strip(' -')
    nome_lower = nome_base.lower()
    
    tem_tempo = re.search(r'(\d+\s*dias|\d+\s*meses|\d+\s*anos|vital[ií]cio|lifetime|credit|cr[eé]dito)', nome_lower)
    sufixo_tempo = "" if tem_tempo else " (30 dias)"
    nome_lindo = f"{nome_base}{sufixo_tempo}"

    desc_linda = "Licença premium oficial e original. Entrega rápida via WhatsApp após confirmação do Pix."
    if 'gemini' in nome_lower: desc_linda = "Pacote IA Avançado: Gemini, Veo, Meet Premium. 🛡️ GARANTIA 20 DIAS."
    elif 'google ai' in nome_lower: desc_linda = "Plataforma IA para desenvolvedores do Google Cloud."
    elif 'chatgpt' in nome_lower: desc_linda = "Acesso oficial ao ChatGPT Plus/Team. IA de ponta para textos e imagens."
    elif 'claude' in nome_lower: desc_linda = "Créditos de API ou acesso à Inteligência Artificial da Anthropic."
    elif 'codex' in nome_lower: desc_linda = "Créditos e acesso à API Codex para geração de código avançado."
    elif 'muse' in nome_lower: desc_linda = "Criação de vídeos incríveis com IA gerativa da Muse."
    elif 'quizlet' in nome_lower: desc_linda = "Aprenda qualquer assunto com cartões e testes interativos gerados por IA."
    elif 'skillshare' in nome_lower: desc_linda = "Acesso premium a milhares de aulas focadas em criatividade e negócios."
    elif 'canva' in nome_lower: desc_linda = "Crie designs incríveis com acesso ilimitado a templates premium."
    elif 'capcut' in nome_lower: desc_linda = "Todos os efeitos Pro liberados. Edite vídeos pelo celular ou PC."
    elif 'microsoft' in nome_lower or 'office' in nome_lower: desc_linda = "Pacote Office completo com armazenamento seguro em nuvem."
    elif 'youtube' in nome_lower: desc_linda = "YouTube e Music sem anúncios. Assista vídeos offline."
    
    detalhes_seguros = extrair_detalhes_seguros(desc_original, nome_lower)
    if detalhes_seguros: desc_linda += detalhes_seguros
            
    return nome_lindo, desc_linda

def calcular_preco_dinamico(custo_usd):
    custo_brl = custo_usd * 6.00
    if custo_usd <= 2.00: return round(custo_brl + 75.40, 2)
    elif custo_usd <= 10.00: return round(custo_brl * 4.0, 2)
    elif custo_usd <= 20.00: return round(custo_brl * 3.0, 2)
    elif custo_usd <= 50.00: return round(custo_brl * 2.0, 2)
    else: return round(custo_brl * 1.5, 2)

def buscar_todos_fornecedores():
    catalogo_tratado = []
    chaves_processadas = set()

    def adicionar_ao_catalogo(id_prod, raw_name, custo_usd, desc_original):
        if not raw_name or custo_usd <= 0: return
        nome_ptbr, resumo_ptbr = traduzir_e_resumir(raw_name, desc_original)
        chave = nome_ptbr.lower().strip()
        if chave not in chaves_processadas:
            catalogo_tratado.append({
                "id": str(id_prod),
                "nome": nome_ptbr,
                "precoBase": calcular_preco_dinamico(custo_usd),
                "logoDomain": obter_dominio_logo(raw_name + " " + nome_ptbr),
                "categoria": obter_categoria(raw_name + " " + nome_ptbr),
                "estoque": True,
                "descricao": resumo_ptbr
            })
            chaves_processadas.add(chave)

    # 1. GGSOMA
    if PARTNER_API_KEY:
        try:
            for page in range(1, 10):
                resp_gg = requests.get(f"{PARTNER_API_URL}/catalog/products?limit=100&page={page}", headers={"Authorization": f"Bearer {PARTNER_API_KEY}"}, timeout=15)
                if resp_gg.status_code != 200: break
                dados = resp_gg.json().get("data", [])
                if not dados: break
                for p in dados:
                    if extrair_estoque(p):
                        adicionar_ao_catalogo(p.get("slug") or p.get("id"), p.get("name"), extrair_preco_usd(p.get("yourPrice")), p.get("description", ""))
                if len(dados) < 100: break
        except: pass

    # 2. CANBOSO
    if CANBOSO_API_KEY:
        try:
            for page in range(1, 10):
                resp_can = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={CANBOSO_API_KEY}&limit=100&page={page}", timeout=15)
                if resp_can.status_code != 200: break
                dados = resp_can.json().get("products", [])
                if not dados: break
                for p in dados:
                    if extrair_estoque(p):
                        adicionar_ao_catalogo(p.get("productId") or p.get("id"), p.get("name"), extrair_preco_usd(p.get("price")), p.get("description", ""))
                if len(dados) < 100: break
        except: pass

    # 3. BUNAI STORE
    if BUNAI_API_KEY:
        try:
            for offset in [0, 100, 200, 300, 400]:
                resp_bunai = requests.get(f"https://api.bunaistore.shop/v1/products?view=variants&limit=100&offset={offset}", headers={"X-API-Key": BUNAI_API_KEY}, timeout=15)
                if resp_bunai.status_code != 200: break
                lista = resp_bunai.json()
                if not lista: break
                for p in lista:
                    if extrair_estoque(p):
                        nome_b = p.get("display_name") or p.get("name") or f"{p.get('group_name','')} {p.get('variant_name','')}".strip()
                        adicionar_ao_catalogo(p.get("product_id"), nome_b, extrair_preco_usd(p.get("price")), p.get("note", ""))
                if len(lista) < 100: break
        except: pass

    # 4. OPTIMUS PRIME
    if OPTIMUS_API_KEY:
        try:
            for page in range(1, 15):
                resp_opt = requests.get(f"https://optimusprime.click/api/telegram-buyer/products?limit=100&page={page}", headers={"X-API-Key": OPTIMUS_API_KEY}, timeout=20)
                if resp_opt.status_code != 200: break
                dt = resp_opt.json()
                prod_list = dt.get("products", dt.get("data", []))
                if not prod_list: break
                for p in prod_list:
                    if str(p.get("purchasable", True)).lower() != "false" and extrair_estoque(p):
                        custo = extrair_preco_usd(p.get("price") or p.get("base_price") or p.get("pricing") or p.get("walletPricing"))
                        if custo <= 0 and p.get("credit_tiers"):
                            custo = extrair_preco_usd(p["credit_tiers"][0].get("unit_price"))
                        raw_name = p.get("custom_name") or p.get("name") or p.get("product_name") or ""
                        adicionar_ao_catalogo(p.get("product_id") or p.get("id"), raw_name, custo, p.get("custom_description") or p.get("description") or p.get("note") or "")
                if len(prod_list) < 100: break
        except: pass

    # 5. NIMO SHOP
    if NIMO_API_KEY:
        try:
            for page in range(1, 15):
                resp_nimo = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={NIMO_API_KEY}&limit=100&page={page}", timeout=20)
                if resp_nimo.status_code != 200: break
                dados = resp_nimo.json().get("products", [])
                if not dados: break
                for p in dados:
                    if extrair_estoque(p):
                        adicionar_ao_catalogo(p.get("productId") or p.get("id"), p.get("name"), extrair_preco_usd(p.get("price")), p.get("description", ""))
                if len(dados) < 100: break
        except: pass

    return catalogo_tratado

@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))

@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def get_catalogo():
    response.content_type = 'application/json'
    if request.method == 'OPTIONS': return json.dumps({})
    return json.dumps(buscar_todos_fornecedores())

@app.route('/gerar-pix', method=['POST', 'OPTIONS'])
def gerar_pix():
    if request.method == 'OPTIONS': return {}
    dados = request.json or {}
    client_id, produto_id = dados.get("client_id", ""), str(dados.get("produto_id", ""))
    
    try: quantidade = max(1, int(dados.get("quantidade", 1)))
    except: return {"error": "Quantidade inválida."}

    catalogo = buscar_todos_fornecedores()
    prod = next((item for item in catalogo if str(item.get("id")) == produto_id), None)
    if not prod: return {"error": "Produto indisponível no estoque dos fornecedores."}

    preco_base = prod["precoBase"]
    preco_unitario = preco_base * (70.00 / 85.00) if quantidade >= 5 else preco_base
    valor_total = round(preco_unitario * quantidade, 2)
    
    payment_data = {
        "transaction_amount": valor_total,
        "description": f"{quantidade}x {prod['nome']}",
        "payment_method_id": "pix",
        "external_reference": client_id,
        "payer": {"email": f"comprador_{client_id[:8]}@tecnologia.com"},
        "metadata": {"produto_id": produto_id, "quantidade": quantidade}
    }

    req_opts = mercadopago.config.RequestOptions()
    req_opts.custom_headers = {'x-idempotency-key': str(uuid.uuid4())}
    payment = sdk.payment().create(payment_data, req_opts).get("response", {})

    if "id" not in payment: return {"error": "Erro ao gerar PIX com o Banco."}
    t_data = payment.get("point_of_interaction", {}).get("transaction_data", {})

    return {"id_pagamento_mp": str(payment["id"]), "copia_e_cola": t_data.get("qr_code", ""), "qr_code_base64": t_data.get("qr_code_base64", "")}

@app.route('/status/<id>', method=['GET', 'OPTIONS'])
def status_pagamento(id):
    if request.method == 'OPTIONS': return {}
    payment = sdk.payment().get(id).get("response", {})
    status = payment.get("status", "nao_encontrado")
    return {"status": status, "codigo_pedido": gerar_codigo_pedido(id)} if status == "approved" else {"status": status}

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
