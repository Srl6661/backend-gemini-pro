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

# Chaves de API das três plataformas
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PARTNER_API_KEY = os.environ.get('PARTNER_API_KEY') # GGSoma
CANBOSO_API_KEY = os.environ.get('CANBOSO_API_KEY') # Canboso
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
    return 'tech.com' 

def obter_categoria(nome_produto):
    nome = nome_produto.lower()
    if any(x in nome for x in ['chatgpt', 'gemini', 'google pro', 'google ai', 'chatprd', 'manus']): 
        return 'Inteligência Artificial'
    if any(x in nome for x in ['canva', 'framer', 'runway', 'magic patterns', 'elevenlabs', 'mobbin']): 
        return 'Design & Criatividade'
    if any(x in nome for x in ['supabase', 'replit', 'railway', 'bolt', 'lovable']): 
        return 'Desenvolvimento'
    if any(x in nome for x in ['n8n', 'gumloop']): 
        return 'Automação'
    if any(x in nome for x in ['telegram', 'linkedin', 'proton', 'nord', 'vpn']): 
        return 'Redes & Segurança'
    if any(x in nome for x in ['duolingo', 'quillbot']): 
        return 'Educação & Idiomas'
    if any(x in nome for x in ['gamma', 'jam', 'linear', 'posthog']): 
        return 'Produtividade'
    return 'Licença Premium'

def traduzir_e_resumir(nome_original):
    nome_base = str(nome_original).replace("None", "").strip()
    
    nome_base = re.sub(r'\b1\s*months?\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b1\s*m\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\d+)\s*months?', r'\1 meses', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\d+)\s*m\b', r'\1 meses', nome_base, flags=re.IGNORECASE)
    
    match_dias = re.search(r'(30\s*dias)', nome_base, re.IGNORECASE)
    match_meses = re.search(r'(\d+)\s*meses', nome_base, re.IGNORECASE)
    
    sufixo_tempo = ""
    if match_dias: sufixo_tempo = " (30 dias)"
    elif match_meses: sufixo_tempo = f" ({match_meses.group(1)} meses)"
    
    nome_lower = nome_base.lower()
    
    if 'gemini' in nome_lower: return f"Google Pro{sufixo_tempo}", "Nosso carro-chefe! Pacote completo com 7 ferramentas premium: Gemini Advanced, Google Flow (Veo), Health Premium, Meet Premium, Agenda Avançada, Gemini no Docs/Gmail e Armazenamento Compartilhado. + BÔNUS: YouTube Premium Lite."
    if 'google ai' in nome_lower: return f"Google AI Pro{sufixo_tempo}", "Acesso completo à plataforma de Inteligência Artificial do Google AI Studio para desenvolvedores."
    if 'chatgpt' in nome_lower: return f"ChatGPT Plus{sufixo_tempo}", "Acesso ao GPT-4. Inteligência artificial avançada para textos, códigos, análises e criação de imagens."
    if 'framer' in nome_lower: return f"Framer Pro{sufixo_tempo}", "Crie e publique sites profissionais, rápidos e com animações incríveis sem precisar escrever código."
    if 'canva' in nome_lower: return f"Canva Pro{sufixo_tempo}", "Crie designs profissionais, apresentações e vídeos com acesso ilimitado a imagens e templates premium."
    if 'gamma' in nome_lower: return f"Gamma Pro{sufixo_tempo}", "Gere apresentações, documentos e sites inteiros em segundos utilizando o poder da Inteligência Artificial."
    if 'elevenlabs' in nome_lower: return f"ElevenLabs Creator{sufixo_tempo}", "O melhor gerador de vozes do mundo. Crie dublagens e narrações ultra-realistas com Inteligência Artificial."
    if 'runway' in nome_lower: return f"Runway Pro{sufixo_tempo}", "Geração e edição de vídeos impressionantes a partir de textos e imagens utilizando IA cinematográfica."
    if 'telegram' in nome_lower: return f"Telegram Premium{sufixo_tempo}", "Destaque seu perfil, faça downloads mais rápidos, transcrição de áudios e ganhe limites dobrados."
    if 'linkedin' in nome_lower or 'career' in nome_lower: return f"LinkedIn Premium{sufixo_tempo}", "Destaque-se para recrutadores, veja quem visitou seu perfil e expanda sua rede profissional."
    if 'duolingo' in nome_lower: return f"Duolingo Super{sufixo_tempo}", "Aprenda novos idiomas sem anúncios, com vidas ilimitadas e lições offline no seu ritmo."
    if 'nord' in nome_lower or 'vpn' in nome_lower: return f"NordVPN Premium{sufixo_tempo}", "Navegação totalmente anônima, segura e sem bloqueios geográficos na internet."
    if 'replit' in nome_lower: return f"Replit Core{sufixo_tempo}", "Ambiente de desenvolvimento na nuvem com IA integrada para você programar direto do navegador."
    if 'supabase' in nome_lower: return f"Supabase Pro{sufixo_tempo}", "Banco de dados e autenticação escalável para desenvolvedores. A melhor alternativa ao Firebase."
    if 'n8n' in nome_lower: return f"n8n Starter{sufixo_tempo}", "Automatize tarefas repetitivas e integre centenas de aplicativos de forma simples e visual."
    if 'lovable' in nome_lower: return f"Lovable Pro{sufixo_tempo}", "Criação de aplicativos e sistemas completos impulsionados por inteligência artificial."
    if 'bolt' in nome_lower: return f"Bolt.new Pro{sufixo_tempo}", "Desenvolvimento web full-stack direto no navegador com assistência avançada de IA."
    if 'quillbot' in nome_lower: return f"QuillBot Premium{sufixo_tempo}", "Reescreva textos, corrija a gramática e melhore sua fluência em inglês com um clique."
    if 'magic patterns' in nome_lower: return f"Magic Patterns{sufixo_tempo}", "Gere componentes de UI e interfaces completas usando Inteligência Artificial."
    if 'jam team' in nome_lower or 'jam' in nome_lower: return f"Jam Team{sufixo_tempo}", "Reporte bugs em segundos com gravação de tela e logs automáticos do navegador."
    if 'linear' in nome_lower: return f"Linear Business{sufixo_tempo}", "A ferramenta de gerenciamento de projetos e issues mais rápida do mercado."
    if 'gumloop' in nome_lower: return f"Gumloop Pro{sufixo_tempo}", "Automatize workflows complexos sem código de forma visual."
    if 'railway' in nome_lower: return f"Railway Hobby{sufixo_tempo}", "Implante e hospede seus aplicativos na nuvem de forma instantânea e sem complicações."
    if 'manus' in nome_lower: return f"Manus Pro{sufixo_tempo}", "Agente de IA revolucionário que controla seu navegador e completa tarefas complexas autonomamente."
    if 'posthog' in nome_lower: return f"PostHog Scale{sufixo_tempo}", "Plataforma completa de análise de dados, heatmaps e testes A/B para o seu produto."
    if 'mobbin' in nome_lower: return f"Mobbin 10x Seat{sufixo_tempo}", "A maior biblioteca de referências de design UI/UX do mundo para aplicativos móveis e web."
    if 'chatprd' in nome_lower: return f"ChatPRD Pro{sufixo_tempo}", "O copiloto de IA definitivo para Product Managers escreverem requisitos e estratégias."
    if 'proton' in nome_lower: return f"Proton Unlimited{sufixo_tempo}", "E-mail criptografado, calendário, drive e VPN em um ecossistema com privacidade máxima."

    return f"{nome_base}{sufixo_tempo}", "Licença premium oficial e original. Entrega rápida via WhatsApp após confirmação do Pix."

@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))

@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def get_catalogo():
    response.content_type = 'application/json'
    if request.method == 'OPTIONS': return json.dumps({})
    
    catalogo_tratado = []
    produtos_processados = set() # Evita duplicatas caso os fornecedores tenham o mesmo produto
    
    # 1. Puxa do Fornecedor Primário (GGSoma)
    if PARTNER_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {PARTNER_API_KEY}"}
            resp_gg = requests.get(f"{PARTNER_API_URL}/catalog/products", headers=headers, timeout=10)
            if resp_gg.status_code == 200:
                for p in resp_gg.json().get("data", []):
                    if p.get("stock", {}).get("inStock", False):
                        custo_usd = float(p.get("yourPrice", 0))
                        preco_calculado = round((custo_usd * 6.00) + 75.40, 2)
                        
                        nome_ptbr, resumo_ptbr = traduzir_e_resumir(p.get("name", ""))
                        if nome_ptbr not in produtos_processados:
                            catalogo_tratado.append({
                                "id": p["slug"],
                                "nome": nome_ptbr,
                                "precoBase": preco_calculado,
                                "logoDomain": obter_dominio_logo(nome_ptbr),
                                "categoria": obter_categoria(nome_ptbr),
                                "estoque": True,
                                "descricao": resumo_ptbr
                            })
                            produtos_processados.add(nome_ptbr)
        except Exception as e:
            print(f"Erro GGSoma: {e}")

    # 2. Puxa do Fornecedor Secundário (Canboso)
    if CANBOSO_API_KEY:
        try:
            resp_canboso = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={CANBOSO_API_KEY}", timeout=10)
            if resp_canboso.status_code == 200:
                for p in resp_canboso.json().get("products", []):
                    estoque = p.get("availability", {}).get("available", 0)
                    if estoque > 0:
                        moeda = p.get("price", {}).get("currency", "USD")
                        valor_bruto = float(p.get("price", {}).get("amount", 0))
                        
                        # Conversão caso a carteira Canboso esteja em VND (1 USD ~ 25000 VND)
                        custo_usd = valor_bruto / 25000.0 if moeda == "VND" else valor_bruto
                        preco_calculado = round((custo_usd * 6.00) + 75.40, 2)

                        nome_ptbr, resumo_ptbr = traduzir_e_resumir(p.get("name", ""))
                        if nome_ptbr not in produtos_processados:
                            catalogo_tratado.append({
                                "id": str(p["productId"]),
                                "nome": nome_ptbr,
                                "precoBase": preco_calculado,
                                "logoDomain": obter_dominio_logo(nome_ptbr),
                                "categoria": obter_categoria(nome_ptbr),
                                "estoque": True,
                                "descricao": resumo_ptbr
                            })
                            produtos_processados.add(nome_ptbr)
        except Exception as e:
            print(f"Erro Canboso: {e}")

    return json.dumps(catalogo_tratado)

@app.route('/gerar-pix', method=['POST', 'OPTIONS'])
def gerar_pix():
    if request.method == 'OPTIONS': return {}
    dados = request.json or {}
    client_id = dados.get("client_id", "")
    produto_id = dados.get("produto_id", "") 
    
    try:
        quantidade = int(dados.get("quantidade", 1))
    except:
        return {"error": "Quantidade inválida."}
        
    if quantidade <= 0: return {"error": "Quantidade deve ser maior que zero."}

    custo_usd = None
    nome_original = ""

    # 1. Procura o custo real na GGSoma
    if PARTNER_API_KEY and custo_usd is None:
        try:
            resp_gg = requests.get(f"{PARTNER_API_URL}/catalog/products", headers={"Authorization": f"Bearer {PARTNER_API_KEY}"}, timeout=10)
            if resp_gg.status_code == 200:
                for p in resp_gg.json().get("data", []):
                    if p.get("slug") == produto_id:
                        custo_usd = float(p.get("yourPrice", 0))
                        nome_original = p.get("name", "")
                        break
        except: pass

    # 2. Procura o custo real na Canboso caso não seja da GGSoma
    if CANBOSO_API_KEY and custo_usd is None:
        try:
            resp_canboso = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={CANBOSO_API_KEY}", timeout=10)
            if resp_canboso.status_code == 200:
                for p in resp_canboso.json().get("products", []):
                    if str(p.get("productId")) == produto_id:
                        moeda = p.get("price", {}).get("currency", "USD")
                        valor = float(p.get("price", {}).get("amount", 0))
                        custo_usd = valor / 25000.0 if moeda == "VND" else valor
                        nome_original = p.get("name", "")
                        break
        except: pass

    if custo_usd is None:
        return {"error": "Produto indisponível no estoque dos fornecedores."}

    # Aplica a margem de lucro blindada
    preco_base = round((custo_usd * 6.00) + 75.40, 2)
    preco_unitario = preco_base * (70.00 / 85.00) if quantidade >= 5 else preco_base
    valor_total_seguro = round(preco_unitario * quantidade, 2)
    
    nome_traduzido, _ = traduzir_e_resumir(nome_original)
    descricao_dinamica = f"{quantidade}x {nome_traduzido}"
    email_fantasma = f"comprador_{client_id[:8]}@tecnologia.com"

    payment_data = {
        "transaction_amount": valor_total_seguro,
        "description": descricao_dinamica,
        "payment_method_id": "pix",
        "external_reference": client_id,
        "payer": {"email": email_fantasma},
        "metadata": {"produto_id": produto_id, "quantidade": quantidade}
    }

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {'x-idempotency-key': str(uuid.uuid4())}

    result = sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})

    if "id" not in payment: return {"error": "Erro ao gerar PIX com o Banco."}
    transaction_data = payment.get("point_of_interaction", {}).get("transaction_data", {})

    return {
        "id_pagamento_mp": str(payment["id"]),
        "copia_e_cola": transaction_data.get("qr_code", ""),
        "qr_code_base64": transaction_data.get("qr_code_base64", "")
    }

@app.route('/status/<id>', method=['GET', 'OPTIONS'])
def status_pagamento(id):
    if request.method == 'OPTIONS': return {}
        
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
