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

# 🔑 Chaves de API das QUATRO plataformas
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PARTNER_API_KEY = os.environ.get('PARTNER_API_KEY') 
CANBOSO_API_KEY = os.environ.get('CANBOSO_API_KEY') 
BUNAI_API_KEY = os.environ.get('BUNAI_API_KEY')     
OPTIMUS_API_KEY = os.environ.get('OPTIMUS_API_KEY') 
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
    if 'capcut' in nome: return 'capcut.com'
    if 'grok' in nome: return 'x.ai'
    if 'coursera' in nome: return 'coursera.org'
    if 'youtube' in nome: return 'youtube.com'
    if 'cursor' in nome: return 'cursor.com'
    if 'notion' in nome: return 'notion.so'
    if 'arize' in nome: return 'arize.com'
    if 'airtable' in nome: return 'airtable.com'
    if 'descript' in nome: return 'descript.com'
    if 'microsoft' in nome: return 'microsoft.com'
    if 'wispr' in nome: return 'wisprflow.ai'
    if 'leonardo' in nome: return 'leonardo.ai'
    if 'adobe' in nome: return 'adobe.com'
    if 'higgsfield' in nome: return 'higgsfield.ai'
    return 'tech.com' 

def obter_categoria(nome_produto):
    nome = nome_produto.lower()
    if any(x in nome for x in ['chatgpt', 'gemini', 'google pro', 'google ai', 'chatprd', 'manus', 'grok', 'cursor', 'wispr']): 
        return 'Inteligência Artificial'
    if any(x in nome for x in ['canva', 'framer', 'runway', 'magic patterns', 'elevenlabs', 'mobbin', 'capcut', 'descript', 'leonardo', 'adobe', 'higgsfield']): 
        return 'Design & Criatividade'
    if any(x in nome for x in ['supabase', 'replit', 'railway', 'bolt', 'lovable', 'arize']): 
        return 'Desenvolvimento'
    if any(x in nome for x in ['n8n', 'gumloop']): 
        return 'Automação'
    if any(x in nome for x in ['telegram', 'linkedin', 'proton', 'nord', 'vpn']): 
        return 'Redes & Segurança'
    if any(x in nome for x in ['duolingo', 'quillbot', 'coursera']): 
        return 'Educação & Idiomas'
    if any(x in nome for x in ['gamma', 'jam', 'linear', 'posthog', 'notion', 'airtable', 'microsoft']): 
        return 'Produtividade'
    if 'youtube' in nome: return 'Entretenimento'
    return 'Licença Premium'

def traduzir_e_resumir(nome_original):
    nome_base = str(nome_original).replace("None", "").strip()
    nome_base = re.sub(r'(CDK\s*FW|CDK\s*NW|CDK|FW|NW|W5D|W6D|\(NW\)|\(FW\))', '', nome_base, flags=re.IGNORECASE).strip()
    
    # Filtro robusto para capturar os meses (com ou sem hífen)
    nome_base = re.sub(r'\b1[-\s]*months?\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'\b1[-\s]*m\b', '30 dias', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\d+)[-\s]*months?', r'\1 meses', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\d+)[-\s]*m\b', r'\1 meses', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'>', '-', nome_base)
    
    match_dias = re.search(r'(30\s*dias)', nome_base, re.IGNORECASE)
    match_meses = re.search(r'(\d+)\s*meses', nome_base, re.IGNORECASE)
    
    sufixo_tempo = ""
    if match_dias: sufixo_tempo = " (30 dias)"
    elif match_meses: sufixo_tempo = f" ({match_meses.group(1)} meses)"
    
    nome_lower = nome_base.lower()
    
    if 'gemini' in nome_lower: return f"Google Pro{sufixo_tempo}", "Pacote completo: Gemini Advanced, Veo, Meet/Agenda Premium e nuvem ampliada. BÔNUS: YouTube Premium Lite. 🛡️ GARANTIA: 20 dias específicos para a conta Google."
    if 'google ai' in nome_lower: return f"Google AI Pro{sufixo_tempo}", "Acesso completo à plataforma de Inteligência Artificial para desenvolvedores. 🛡️ GARANTIA: 20 dias específicos para a conta Google."
    if 'chatgpt' in nome_lower: return f"ChatGPT Plus{sufixo_tempo}", "Acesso ao GPT-4. Inteligência artificial avançada para textos, códigos, análises e criação de imagens."
    if 'framer' in nome_lower: return f"Framer Pro{sufixo_tempo}", "Crie e publique sites profissionais, rápidos e com animações incríveis sem precisar escrever código."
    if 'canva' in nome_lower: return f"Canva Pro{sufixo_tempo}", "Crie designs profissionais, apresentações e vídeos com acesso ilimitado a imagens e templates premium."
    if 'gamma' in nome_lower: return f"Gamma Pro{sufixo_tempo}", "Gere apresentações, documentos e sites inteiros em segundos utilizando o poder da Inteligência Artificial."
    if 'elevenlabs' in nome_lower: return f"ElevenLabs Creator{sufixo_tempo}", "O melhor gerador de vozes do mundo. Crie dublagens e narrações ultra-realistas com Inteligência Artificial."
    if 'runway' in nome_lower: return f"Runway Pro{sufixo_tempo}", "Geração e edição de vídeos impressionantes a partir de textos e imagens utilizando IA cinematográfica."
    if 'telegram' in nome_lower: return f"Telegram Premium{sufixo_tempo}", "Destaque seu perfil, faça downloads mais rápidos, transcrição de áudios e ganhe limites dobrados."
    if 'linkedin' in nome_lower: return f"LinkedIn Premium{sufixo_tempo}", "Destaque-se para recrutadores, veja quem visitou seu perfil e expanda sua rede profissional."
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
    if 'capcut' in nome_lower: return f"CapCut Premium{sufixo_tempo}", "Acesse todos os efeitos Pro, remova fundos facilmente e edite vídeos como um profissional."
    if 'grok' in nome_lower: return f"Grok AI (xAI){sufixo_tempo}", "Acesso ao poderoso modelo de Inteligência Artificial sem filtros desenvolvido pela xAI (Twitter/X)."
    if 'coursera' in nome_lower: return f"Coursera Premium{sufixo_tempo}", "Acesso ilimitado a milhares de cursos, projetos guiados e certificados nas melhores universidades."
    if 'youtube' in nome_lower: return f"YouTube Premium{sufixo_tempo}", "Assista a vídeos sem anúncios, baixe para ver offline e aproveite o YouTube Music Premium."
    if 'cursor' in nome_lower: return f"Cursor Pro{sufixo_tempo}", "O editor de código revolucionário impulsionado por IA que escreve software junto com você."
    if 'notion' in nome_lower: return f"Notion Business{sufixo_tempo}", "O espaço de trabalho definitivo. Notas, wikis e gerenciamento de projetos com IA integrada."
    if 'arize' in nome_lower: return f"Arize Pro{sufixo_tempo}", "Plataforma avançada de observabilidade e avaliação de modelos de Inteligência Artificial."
    if 'airtable' in nome_lower: return f"Airtable Team{sufixo_tempo}", "Crie aplicativos poderosos para o seu negócio conectando seus dados de forma visual."
    if 'descript' in nome_lower: return f"Descript Creator{sufixo_tempo}", "A maneira mais fácil e rápida de gravar, transcrever e editar vídeos e podcasts."
    if 'microsoft 365' in nome_lower: return f"Microsoft 365 Premium{sufixo_tempo}", "O pacote Office completo com Word, Excel, PowerPoint e armazenamento em nuvem seguro."
    if 'wispr' in nome_lower: return f"Wispr Flow Pro{sufixo_tempo}", "Ditado por voz revolucionário. Fale e deixe a IA formatar e escrever por você no Mac ou Windows."
    if 'leonardo' in nome_lower: return f"Leonardo AI Premium{sufixo_tempo}", "Geração de imagens incríveis e artes digitais usando modelos de IA de ponta."
    if 'adobe express' in nome_lower: return f"Adobe Express Premium{sufixo_tempo}", "Crie posts sociais, vídeos curtos, flyers e logos em minutos com IA generativa da Adobe."
    if 'higgsfield' in nome_lower: return f"Higgsfield Pro{sufixo_tempo}", "Plataforma de criação de vídeos cinemáticos e comerciais por Inteligência Artificial."

    return f"{nome_base}{sufixo_tempo}", "Licença premium oficial e original. Entrega rápida via WhatsApp após confirmação do Pix."

def calcular_preco_dinamico(custo_usd):
    custo_brl = custo_usd * 6.00
    if custo_usd <= 2.00: 
        return round(custo_brl + 75.40, 2)
    elif custo_usd <= 10.00: 
        return round(custo_brl * 4.0, 2)
    elif custo_usd <= 20.00: 
        return round(custo_brl * 3.0, 2)
    elif custo_usd <= 50.00: 
        return round(custo_brl * 2.0, 2)
    else: 
        return round(custo_brl * 1.5, 2)

@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))

@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def get_catalogo():
    response.content_type = 'application/json'
    if request.method == 'OPTIONS': return json.dumps({})
    
    catalogo_tratado = []
    produtos_processados = set() 
    
    if PARTNER_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {PARTNER_API_KEY}"}
            resp_gg = requests.get(f"{PARTNER_API_URL}/catalog/products", headers=headers, timeout=10)
            if resp_gg.status_code == 200:
                for p in resp_gg.json().get("data", []):
                    if p.get("stock", {}).get("inStock", False):
                        custo_usd = float(p.get("yourPrice", 0))
                        preco_calculado = calcular_preco_dinamico(custo_usd)
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
        except Exception as e: print(f"Erro GGSoma: {e}")

    if CANBOSO_API_KEY:
        try:
            resp_canboso = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={CANBOSO_API_KEY}", timeout=10)
            if resp_canboso.status_code == 200:
                for p in resp_canboso.json().get("products", []):
                    estoque = p.get("availability", {}).get("available")
                    if estoque is None or estoque != 0: 
                        moeda = p.get("price", {}).get("currency", "USD")
                        valor_bruto = float(p.get("price", {}).get("amount", 0))
                        custo_usd = valor_bruto / 25000.0 if moeda == "VND" else valor_bruto
                        
                        preco_calculado = calcular_preco_dinamico(custo_usd)
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
        except Exception as e: print(f"Erro Canboso: {e}")

    if BUNAI_API_KEY:
        try:
            headers_bunai = {"X-API-Key": BUNAI_API_KEY}
            resp_bunai = requests.get("https://api.bunaistore.shop/v1/products?view=variants&limit=100", headers=headers_bunai, timeout=10)
            if resp_bunai.status_code == 200:
                for p in resp_bunai.json():
                    estoque_valido = p.get("infinite_stock", False) or p.get("stock_count", 0) > 0
                    if estoque_valido:
                        custo_usd = float(p.get("price", 0))
                        
                        preco_calculado = calcular_preco_dinamico(custo_usd)
                        nome_ptbr, resumo_ptbr = traduzir_e_resumir(p.get("display_name", ""))
                        
                        if nome_ptbr not in produtos_processados:
                            catalogo_tratado.append({
                                "id": str(p["product_id"]),
                                "nome": nome_ptbr,
                                "precoBase": preco_calculado,
                                "logoDomain": obter_dominio_logo(nome_ptbr),
                                "categoria": obter_categoria(nome_ptbr),
                                "estoque": True,
                                "descricao": resumo_ptbr
                            })
                            produtos_processados.add(nome_ptbr)
        except Exception as e: print(f"Erro Bunai: {e}")

    if OPTIMUS_API_KEY:
        try:
            headers_optimus = {"X-API-Key": OPTIMUS_API_KEY}
            resp_optimus = requests.get("https://optimusprime.click/api/telegram-buyer/products", headers=headers_optimus, timeout=10)
            if resp_optimus.status_code == 200:
                data_optimus = resp_optimus.json()
                prod_list = data_optimus.get("products", []) if isinstance(data_optimus, dict) else data_optimus
                for p in prod_list:
                    estoque_valido = p.get("purchasable", True) and (p.get("stock", 0) > 0 or p.get("infinite_stock", False) or p.get("delivery_mode") == "manual")
                    if estoque_valido:
                        custo_usd = float(p.get("price", 0))
                        
                        preco_calculado = calcular_preco_dinamico(custo_usd)
                        raw_name = p.get("name", p.get("product_name", ""))
                        nome_ptbr, resumo_ptbr = traduzir_e_resumir(raw_name)
                        
                        if nome_ptbr not in produtos_processados:
                            catalogo_tratado.append({
                                "id": str(p.get("product_id")),
                                "nome": nome_ptbr,
                                "precoBase": preco_calculado,
                                "logoDomain": obter_dominio_logo(nome_ptbr),
                                "categoria": obter_categoria(nome_ptbr),
                                "estoque": True,
                                "descricao": resumo_ptbr
                            })
                            produtos_processados.add(nome_ptbr)
        except Exception as e: print(f"Erro Optimus: {e}")

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

    if BUNAI_API_KEY and custo_usd is None:
        try:
            resp_bunai = requests.get("https://api.bunaistore.shop/v1/products?view=variants&limit=100", headers={"X-API-Key": BUNAI_API_KEY}, timeout=10)
            if resp_bunai.status_code == 200:
                for p in resp_bunai.json():
                    if str(p.get("product_id")) == produto_id:
                        custo_usd = float(p.get("price", 0))
                        nome_original = p.get("display_name", "")
                        break
        except: pass

    if OPTIMUS_API_KEY and custo_usd is None:
        try:
            resp_optimus = requests.get("https://optimusprime.click/api/telegram-buyer/products", headers={"X-API-Key": OPTIMUS_API_KEY}, timeout=10)
            if resp_optimus.status_code == 200:
                data_optimus = resp_optimus.json()
                prod_list = data_optimus.get("products", []) if isinstance(data_optimus, dict) else data_optimus
                for p in prod_list:
                    if str(p.get("product_id")) == produto_id:
                        custo_usd = float(p.get("price", 0))
                        nome_original = p.get("name", p.get("product_name", ""))
                        break
        except: pass

    if custo_usd is None:
        return {"error": "Produto indisponível no estoque dos fornecedores."}

    preco_base = calcular_preco_dinamico(custo_usd)
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
