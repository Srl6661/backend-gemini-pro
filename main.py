from bottle import Bottle, request, response, run, static_file
import mercadopago
import os
import uuid
import hmac
import hashlib
import requests
import json
import re
import time
import threading

app = Bottle()

# 🔑 Chaves de API das QUATRO plataformas
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PARTNER_API_KEY = os.environ.get('PARTNER_API_KEY') 
CANBOSO_API_KEY = os.environ.get('CANBOSO_API_KEY') 
BUNAI_API_KEY = os.environ.get('BUNAI_API_KEY')     
OPTIMUS_API_KEY = os.environ.get('OPTIMUS_API_KEY') 
SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao-123')
# Número do WhatsApp (só dígitos, com 55 e DDD). Fica só no servidor e só é entregue após pagamento aprovado.
WHATSAPP_NUMERO = re.sub(r'\D', '', os.environ.get('WHATSAPP_NUMERO', ''))
INTERVALO_ATUALIZACAO = int(os.environ.get('CATALOGO_INTERVALO', 300))  # segundos entre atualizações do catálogo

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
    if 'perplexity' in nome: return 'perplexity.ai'
    if 'midjourney' in nome: return 'midjourney.com'
    return 'tech.com' 

def obter_categoria(nome_produto):
    nome = nome_produto.lower()
    if any(x in nome for x in ['chatgpt', 'gemini', 'google pro', 'google ai', 'chatprd', 'manus', 'grok', 'cursor', 'wispr', 'magic', 'supercut', 'pangram', 'claude', 'perplexity', 'midjourney', 'leonardo']): 
        return 'Inteligência Artificial'
    if any(x in nome for x in ['canva', 'framer', 'runway', 'elevenlabs', 'eleven', 'mobbin', 'capcut', 'descript', 'adobe', 'higgsfield', 'autodesk', 'autocad', 'figma']): 
        return 'Design & Criatividade'
    if any(x in nome for x in ['supabase', 'replit', 'railway', 'bolt', 'lovable', 'arize', 'warp', 'resend', 'api credits']): 
        return 'Desenvolvimento'
    if any(x in nome for x in ['n8n', 'gumloop']): 
        return 'Automação'
    if any(x in nome for x in ['telegram', 'linkedin', 'proton', 'nord', 'vpn', 'kaspersky', 'windows']): 
        return 'Redes & Segurança'
    if any(x in nome for x in ['duolingo', 'quillbot', 'coursera', 'memrise', 'grammarly', 'kahoot']): 
        return 'Educação & Idiomas'
    if any(x in nome for x in ['gamma', 'jam', 'linear', 'posthog', 'notion', 'airtable', 'microsoft', 'ms office', 'office', 'gmail', 'intercom', 'ilovepdf', 'zoom', 'granola']): 
        return 'Produtividade'
    if any(x in nome for x in ['youtube', 'crunchyroll', 'discord', 'roblox', 'spotify', 'netflix', 'amazon']): 
        return 'Entretenimento'
    return 'Licença Premium'

# 🕵️‍♂️ FILTRO BLINDADO ANTI-RASTREIO (Extrai infos úteis e destrói qualquer rastro do fornecedor)
def extrair_detalhes_seguros(desc_original, nome_lower=""):
    if not desc_original:
        return ""
    
    texto = str(desc_original)
    # 1. Destrói códigos de custom emoji do Telegram: {ce:123...} ou <<ce:123...>>
    texto = re.sub(r'[<\{]*ce:\d+[>\}]*', '', texto, flags=re.IGNORECASE)
    # 2. Remove HTML
    texto = re.sub(r'<[^>]+>', ' ', texto)
    
    texto_lower = texto.lower()
    avisos = []
    
    # 3. Reconstrói apenas as informações importantes em Português (Impossível buscar no Google!)
    if 'vietnam' in texto_lower or 'vietnã' in texto_lower:
        avisos.append("Requer VPN (Vietnã) apenas no 1º acesso")
    elif 'india' in texto_lower or 'índia' in texto_lower:
        avisos.append("Requer VPN (Índia) apenas na ativação")
    elif 'vpn' in texto_lower and 'vpn' not in nome_lower:
        avisos.append("Pode requerer VPN na ativação")
        
    if any(x in texto_lower for x in ['own account', 'your account', 'sua conta', 'personal account']):
        avisos.append("Ativação direto na sua conta")
    elif any(x in texto_lower for x in ['new account', 'provided account', 'conta pronta', 'full account']):
        avisos.append("Conta pronta exclusiva enviada após a compra")
        
    if any(x in texto_lower for x in ['coupon', 'redeem code', 'voucher', 'cupom']):
        avisos.append("Ativação via Código/Cupom Oficial")
        
    if any(x in texto_lower for x in ['need card', 'requires card', 'precisa de cartão', 'credit card']):
        avisos.append("Requer cartão para ativar assinatura")
        
    match_garantia = re.search(r'(\d+)[-\s]*days?\s*warranty', texto_lower)
    if match_garantia and 'gemini' not in nome_lower and 'google' not in nome_lower:
        avisos.append(f"Garantia de {match_garantia.group(1)} dias")
        
    if avisos:
        return " 📌 Especificações: " + " • ".join(avisos) + "."
    return ""

def traduzir_e_resumir(nome_original, desc_original=""):
    nome_base = str(nome_original).replace("None", "").strip()
    
    # Remove qualquer código {ce:...} que porventura venha no título também
    nome_base = re.sub(r'[<\{]*ce:\d+[>\}]*', '', nome_base, flags=re.IGNORECASE)
    
    # Limpa códigos internos de fornecedores mantendo o nome real da variação
    nome_base = re.sub(r'\b(CDK\s*FW|CDK\s*NW|CDK|FW|NW|W5D|W6D)\b', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'(\(NW\)|\(FW\)|\(W5D\)|\(W6D\))', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'Link to Receive\s*', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'REDEEM LINK\s*', '', nome_base, flags=re.IGNORECASE)
    nome_base = re.sub(r'>', '-', nome_base)
    nome_base = re.sub(r'\|', '-', nome_base)
    
    # Padroniza o tempo e termos em inglês no título
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
    
    if 'gemini pro' in nome_lower:
        match_t = re.search(r'(\d+\s*meses|\d+\s*dias)', nome_lower)
        t_str = f" ({match_t.group(1)})" if match_t else sufixo_tempo
        nome_lindo = f"Google Pro Gemini{t_str}"
    else:
        nome_lindo = f"{nome_base}{sufixo_tempo}"

    # 🌟 TEXTOS DESCRITIVOS PRÓPRIOS (100% White-Label)
    desc_linda = "Licença premium oficial e original. Entrega rápida via WhatsApp após confirmação do Pix."
    
    if 'gemini' in nome_lower: desc_linda = "Pacote completo: Gemini Advanced, Veo, Meet Premium e nuvem ampliada. BÔNUS: YouTube Premium Lite. 🛡️ GARANTIA: 20 dias específicos para a conta Google."
    elif 'google ai' in nome_lower: desc_linda = "Acesso completo à plataforma de Inteligência Artificial para desenvolvedores. 🛡️ GARANTIA: 20 dias específicos para a conta Google."
    elif 'chatgpt' in nome_lower: desc_linda = "Acesso oficial à Inteligência Artificial da OpenAI para textos, códigos, análises e criação de imagens."
    elif 'framer' in nome_lower: desc_linda = "Crie e publique sites profissionais, rápidos e com animações incríveis sem precisar escrever código."
    elif 'canva' in nome_lower: desc_linda = "Crie designs profissionais, apresentações e vídeos com acesso ilimitado a imagens e templates premium."
    elif 'gamma' in nome_lower: desc_linda = "Gere apresentações, documentos e sites inteiros em segundos utilizando o poder da Inteligência Artificial."
    elif 'elevenlabs' in nome_lower or 'eleven' in nome_lower: desc_linda = "O melhor gerador de vozes do mundo. Crie dublagens e narrações ultra-realistas com Inteligência Artificial."
    elif 'runway' in nome_lower: desc_linda = "Geração e edição de vídeos impressionantes a partir de textos e imagens utilizando IA cinematográfica."
    elif 'telegram' in nome_lower: desc_linda = "Destaque seu perfil, faça downloads mais rápidos, transcrição de áudios e ganhe limites dobrados."
    elif 'linkedin' in nome_lower: desc_linda = "Destaque-se para recrutadores, veja quem visitou seu perfil e expanda sua rede profissional."
    elif 'duolingo' in nome_lower: desc_linda = "Aprenda novos idiomas sem anúncios, com vidas ilimitadas e lições offline no seu ritmo."
    elif 'nord' in nome_lower or 'vpn' in nome_lower: desc_linda = "Navegação totalmente anônima, segura e sem bloqueios geográficos na internet."
    elif 'replit' in nome_lower: desc_linda = "Ambiente de desenvolvimento na nuvem com IA integrada para programar direto do navegador."
    elif 'supabase' in nome_lower: desc_linda = "Banco de dados e autenticação escalável para desenvolvedores. A melhor alternativa ao Firebase."
    elif 'capcut' in nome_lower: desc_linda = "Acesse todos os efeitos Pro, remova fundos facilmente e edite vídeos como um profissional."
    elif 'youtube' in nome_lower: desc_linda = "Assista a vídeos sem anúncios, baixe para ver offline e aproveite o YouTube Music Premium."
    elif 'microsoft' in nome_lower or 'ms office' in nome_lower or 'office' in nome_lower: desc_linda = "O pacote Office completo com Word, Excel, PowerPoint e armazenamento em nuvem seguro."
    elif 'kaspersky' in nome_lower: desc_linda = "Proteção total contra vírus, malware e ameaças online para os seus dispositivos."
    elif 'spotify' in nome_lower: desc_linda = "Música sem limites. Ouça as suas músicas e podcasts favoritos sem anúncios e offline."
    elif 'cursor' in nome_lower: desc_linda = "O editor de código revolucionário impulsionado por IA que escreve software junto com você."
    elif 'notion' in nome_lower: desc_linda = "O espaço de trabalho definitivo. Notas, wikis e gerenciamento de projetos com IA integrada."
    elif 'grok' in nome_lower: desc_linda = "Acesso ao poderoso modelo de Inteligência Artificial desenvolvido pela xAI."
    elif 'coursera' in nome_lower: desc_linda = "Acesso a milhares de cursos, projetos guiados e certificados nas melhores universidades."
    elif 'crunchyroll' in nome_lower: desc_linda = "Assista aos melhores animes do mundo sem anúncios e em alta definição."
    elif 'discord' in nome_lower: desc_linda = "Melhore seu servidor, ganhe emojis personalizados, avatares animados e uploads maiores."
    elif 'grammarly' in nome_lower: desc_linda = "Escreva com confiança. Corretor gramatical e assistente de redação inteligente."
    elif 'autodesk' in nome_lower: desc_linda = "Softwares líderes para design 3D, engenharia e entretenimento (AutoCAD, Revit, Maya)."
    elif 'ilovepdf' in nome_lower: desc_linda = "Ferramentas completas para editar, converter, mesclar e dividir arquivos PDF facilmente."
    elif 'zoom' in nome_lower: desc_linda = "Reuniões sem limite de tempo, gravações na nuvem e recursos premium de colaboração."
    elif 'windows' in nome_lower: desc_linda = "Licença de ativação original do Windows. Mais segurança e desempenho para seu PC."
    elif 'adobe' in nome_lower: desc_linda = "Crie posts sociais, vídeos curtos, flyers e edições incríveis com a suíte criativa da Adobe."
    elif 'leonardo' in nome_lower: desc_linda = "Geração de imagens incríveis e artes digitais usando modelos de IA de ponta."
    elif 'granola' in nome_lower: desc_linda = "Assistente de reuniões com Inteligência Artificial que transforma suas conversas em notas organizadas."
    elif 'linear' in nome_lower: desc_linda = "A ferramenta de gerenciamento de projetos e tarefas mais rápida e moderna para equipes."
    elif 'n8n' in nome_lower: desc_linda = "Automatize processos e integre centenas de sistemas e IAs de forma visual."

    # 📌 Anexa APENAS especificações traduzidas e 100% impossíveis de rastrear no Google
    detalhes_seguros = extrair_detalhes_seguros(desc_original, nome_lower)
    if detalhes_seguros:
        desc_linda += detalhes_seguros
            
    return nome_lindo, desc_linda

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

# 🔍 FUNÇÃO CENTRAL QUE VARRE TODOS OS 4 FORNECEDORES SEM PERDER NADA
def buscar_todos_fornecedores():
    catalogo_tratado = []
    chaves_processadas = set()

    def adicionar_ao_catalogo(id_prod, raw_name, custo_usd, desc_original):
        if not raw_name or custo_usd <= 0:
            return
        nome_ptbr, resumo_ptbr = traduzir_e_resumir(raw_name, desc_original)
        
        chave = nome_ptbr.lower().strip()
        if chave not in chaves_processadas:
            preco_calculado = calcular_preco_dinamico(custo_usd)
            catalogo_tratado.append({
                "id": str(id_prod),
                "nome": nome_ptbr,
                "precoBase": preco_calculado,
                "logoDomain": obter_dominio_logo(raw_name + " " + nome_ptbr),
                "categoria": obter_categoria(raw_name + " " + nome_ptbr),
                "estoque": True,
                "descricao": resumo_ptbr
            })
            chaves_processadas.add(chave)

    # 1. MOTOR GGSOMA
    if PARTNER_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {PARTNER_API_KEY}"}
            resp_gg = requests.get(f"{PARTNER_API_URL}/catalog/products", headers=headers, timeout=20)
            if resp_gg.status_code == 200:
                dados = resp_gg.json()
                lista = dados.get("data", []) if isinstance(dados, dict) else dados
                for p in lista:
                    try:
                        if extrair_estoque(p):
                            custo = extrair_preco_usd(p.get("yourPrice") or p.get("price"))
                            adicionar_ao_catalogo(p.get("slug") or p.get("id"), p.get("name"), custo, p.get("description", ""))
                    except: pass
        except Exception as e: print(f"Erro GGSoma: {e}")

    # 2. MOTOR CANBOSO
    if CANBOSO_API_KEY:
        try:
            resp_canboso = requests.get(f"https://canboso.com/api/v2/telegram-buyer/products?key={CANBOSO_API_KEY}", timeout=20)
            if resp_canboso.status_code == 200:
                dados = resp_canboso.json()
                lista = dados.get("products", []) if isinstance(dados, dict) else dados
                for p in lista:
                    try:
                        if extrair_estoque(p):
                            custo = extrair_preco_usd(p.get("price"))
                            adicionar_ao_catalogo(p.get("productId") or p.get("id"), p.get("name"), custo, p.get("description", ""))
                    except: pass
        except Exception as e: print(f"Erro Canboso: {e}")

    # 3. MOTOR BUNAI STORE
    if BUNAI_API_KEY:
        try:
            headers_bunai = {"X-API-Key": BUNAI_API_KEY}
            for offset in [0, 100, 200, 300]:
                resp_bunai = requests.get(f"https://api.bunaistore.shop/v1/products?view=variants&limit=100&offset={offset}", headers=headers_bunai, timeout=20)
                if resp_bunai.status_code == 200:
                    lista = resp_bunai.json()
                    if not isinstance(lista, list) or len(lista) == 0:
                        break
                    for p in lista:
                        try:
                            if extrair_estoque(p):
                                custo = extrair_preco_usd(p.get("price"))
                                nome_b = p.get("display_name") or p.get("name") or f"{p.get('group_name','')} {p.get('variant_name','')}".strip()
                                adicionar_ao_catalogo(p.get("product_id"), nome_b, custo, p.get("note", ""))
                        except: pass
                    if len(lista) < 100:
                        break
                else:
                    break
        except Exception as e: print(f"Erro Bunai: {e}")

    # 4. MOTOR OPTIMUS PRIME
    if OPTIMUS_API_KEY:
        try:
            headers_optimus = {"X-API-Key": OPTIMUS_API_KEY}
            resp_optimus = requests.get("https://optimusprime.click/api/telegram-buyer/products", headers=headers_optimus, params={"key": OPTIMUS_API_KEY}, timeout=25)
            if resp_optimus.status_code == 200:
                data_optimus = resp_optimus.json()
                prod_list = data_optimus.get("products", data_optimus.get("data", [])) if isinstance(data_optimus, dict) else data_optimus
                for p in prod_list:
                    try:
                        purchasable_val = p.get("purchasable", True)
                        if isinstance(purchasable_val, str):
                            purchasable_val = purchasable_val.lower() != "false"
                        
                        if purchasable_val and extrair_estoque(p):
                            custo = extrair_preco_usd(p.get("price"))
                            if custo <= 0: custo = extrair_preco_usd(p.get("base_price"))
                            if custo <= 0: custo = extrair_preco_usd(p.get("pricing"))
                            if custo <= 0: custo = extrair_preco_usd(p.get("walletPricing"))
                            if custo <= 0 and isinstance(p.get("credit_tiers"), list) and len(p["credit_tiers"]) > 0:
                                custo = extrair_preco_usd(p["credit_tiers"][0].get("unit_price"))

                            raw_name = p.get("custom_name") or p.get("name") or p.get("product_name") or ""
                            desc_orig = p.get("custom_description") or p.get("description") or p.get("note") or ""
                            id_opt = p.get("product_id") or p.get("id") or p.get("_id")
                            
                            adicionar_ao_catalogo(id_opt, raw_name, custo, desc_orig)
                    except: pass
        except Exception as e: print(f"Erro Optimus: {e}")

    return catalogo_tratado

# ⚡ CACHE DO CATÁLOGO: o site responde na hora e a atualização com os fornecedores roda em segundo plano
CACHE_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalogo_cache.json')
_cache = {"dados": [], "atualizado_em": 0}
_cache_lock = threading.Lock()
_primeira_carga = threading.Event()

def _salvar_cache_disco(dados):
    try:
        tmp = CACHE_ARQUIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False)
        os.replace(tmp, CACHE_ARQUIVO)
    except Exception as e:
        print(f"Aviso: não salvou cache em disco: {e}")

def _carregar_cache_disco():
    try:
        with open(CACHE_ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, list) else []
    except Exception:
        return []

def atualizar_catalogo():
    try:
        novo = buscar_todos_fornecedores()
    except Exception as e:
        print(f"Erro ao atualizar catálogo: {e}")
        novo = []
    salvar = False
    with _cache_lock:
        antigo = len(_cache["dados"])
        # Só troca se veio algo e não parece uma queda de fornecedor (menos da metade do que já tínhamos)
        if novo and (antigo == 0 or len(novo) >= antigo * 0.5):
            _cache["dados"] = novo
            _cache["atualizado_em"] = time.time()
            salvar = True
        else:
            print(f"Catálogo mantido (novo={len(novo)}, antigo={antigo}).")
    if salvar:
        _salvar_cache_disco(novo)
    _primeira_carga.set()

def _loop_atualizacao():
    while True:
        atualizar_catalogo()
        time.sleep(INTERVALO_ATUALIZACAO)

def obter_catalogo():
    if not _cache["dados"]:
        _primeira_carga.wait(timeout=40)  # só acontece se o servidor acabou de ligar sem cache
    with _cache_lock:
        return list(_cache["dados"])

def iniciar_atualizacao_em_segundo_plano():
    dados = _carregar_cache_disco()
    if dados:
        _cache["dados"] = dados
        _cache["atualizado_em"] = time.time()
        _primeira_carga.set()
    threading.Thread(target=_loop_atualizacao, daemon=True).start()

iniciar_atualizacao_em_segundo_plano()

@app.route('/health')
def health():
    return {"ok": True, "produtos": len(_cache["dados"])}

@app.route('/')
def index():
    return static_file('index.html', root=os.path.abspath(os.path.dirname(__file__)))

@app.route('/api/catalogo', method=['GET', 'OPTIONS'])
def get_catalogo():
    response.content_type = 'application/json'
    if request.method == 'OPTIONS': return json.dumps({})
    
    response.set_header('Cache-Control', 'public, max-age=60')
    return json.dumps(obter_catalogo())

@app.route('/gerar-pix', method=['POST', 'OPTIONS'])
def gerar_pix():
    if request.method == 'OPTIONS': return {}
    dados = request.json or {}
    client_id = dados.get("client_id", "")
    produto_id = str(dados.get("produto_id", ""))
    
    try:
        quantidade = int(dados.get("quantidade", 1))
    except:
        return {"error": "Quantidade inválida."}
        
    if quantidade <= 0: return {"error": "Quantidade deve ser maior que zero."}
    if quantidade > 50: return {"error": "Quantidade máxima por pedido: 50."}
    if not client_id: return {"error": "Pedido inválido."}

    catalogo = obter_catalogo()
    produto_encontrado = None
    for item in catalogo:
        if str(item.get("id")) == produto_id:
            produto_encontrado = item
            break

    if not produto_encontrado:
        return {"error": "Produto indisponível no estoque dos fornecedores."}

    preco_base = produto_encontrado["precoBase"]
    preco_unitario = preco_base * (70.00 / 85.00) if quantidade >= 5 else preco_base
    valor_total_seguro = round(preco_unitario * quantidade, 2)
    
    descricao_dinamica = f"{quantidade}x {produto_encontrado['nome']}"
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
        # O WhatsApp só é entregue a quem gerou aquele Pix (confere o client_id do pedido)
        cid = request.query.get('cid', '')
        if WHATSAPP_NUMERO and cid and hmac.compare_digest(str(payment.get("external_reference", "")), cid):
            resposta["whatsapp"] = WHATSAPP_NUMERO

    return resposta

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    run(app, host='0.0.0.0', port=port)
