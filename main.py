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
                # Pega o preço em dólar da fornecedora
                custo_usd = float(p.get("yourPrice", 0))
                
                # Multiplica pela sua margem (1.60 -> 85.00 = 53.125)
                preco_calculado = round(custo_usd * 53.125, 2)
                
                catalogo_tratado.append({
                    "id": p["slug"],
                    "nome": p["name"],
                    "precoBase": preco_calculado,
                    "dominio": p["provider"]["key"] + ".com",
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
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Setup VIP BR - Licenças Premium</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        // Configuração da sua API no Render
        const API_BASE_URL = "https://backend-gemini-pro-ocp5.onrender.com";
        
        // Variáveis de estado
        let produtoSelecionado = null;
        let precoBaseAtual = 85.00; 
        let precoComDesconto = 70.00; // Valor unitário se comprar 5 ou mais

        // 1. Carregar o Catálogo do Render
        async function carregarCatalogo() {
            const vitrine = document.getElementById('vitrine');
            vitrine.innerHTML = '<p class="text-center text-gray-500 col-span-full">Carregando produtos...</p>';
            
            try {
                const response = await fetch(`${API_BASE_URL}/api/catalogo`);
                const produtos = await response.json();
                
                if(produtos.length === 0) {
                    vitrine.innerHTML = '<p class="text-center text-gray-500 col-span-full">Nenhum produto disponível no momento.</p>';
                    return;
                }
                
                vitrine.innerHTML = '';
                produtos.forEach(p => {
                    const card = document.createElement('div');
                    card.className = "bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow";
                    card.innerHTML = `
                        <div class="text-sm text-blue-600 font-semibold mb-2">${p.dominio}</div>
                        <h3 class="text-xl font-bold text-gray-800 mb-2">${p.nome}</h3>
                        <p class="text-gray-500 text-sm mb-4 h-10 overflow-hidden">${p.descricao || 'Licença premium original com entrega automática.'}</p>
                        <div class="flex justify-between items-center mt-4">
                            <span class="text-2xl font-extrabold text-gray-900">R$ 85,00</span>
                            <button onclick="abrirCheckout('${p.id}', '${p.nome}', ${p.precoBase})" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors">
                                Comprar
                            </button>
                        </div>
                    `;
                    vitrine.appendChild(card);
                });
            } catch (error) {
                console.error("Erro ao carregar:", error);
                vitrine.innerHTML = '<p class="text-center text-red-500 col-span-full">Erro ao conectar com o servidor. Tente atualizar a página.</p>';
            }
        }

        // 2. Controlar o Modal de Checkout e Descontos
        function abrirCheckout(id, nome, preco) {
            produtoSelecionado = { id, nome };
            precoBaseAtual = preco;
            
            document.getElementById('modal-nome-produto').innerText = nome;
            document.getElementById('quantidade').value = 1;
            atualizarPreco();
            
            document.getElementById('modal-checkout').classList.remove('hidden');
            document.getElementById('area-pagamento').classList.add('hidden');
            document.getElementById('btn-gerar-pix').classList.remove('hidden');
        }

        function fecharModal() {
            document.getElementById('modal-checkout').classList.add('hidden');
        }

        // Atualiza a faixa de preço com base na regra de 5 unidades
        function atualizarPreco() {
            const qtd = parseInt(document.getElementById('quantidade').value) || 1;
            
            // Regra de Desconto (Acima de 5 unidades, o preço unitário cai)
            const precoUnitario = qtd >= 5 ? precoComDesconto : precoBaseAtual;
            const total = (precoUnitario * qtd).toFixed(2);
            
            document.getElementById('preco-total').innerText = `R$ ${total.replace('.', ',')}`;
            
            const aviso = document.getElementById('aviso-desconto');
            if (qtd >= 5) {
                aviso.innerText = `🔥 Desconto de atacado aplicado! (R$ ${precoComDesconto.toFixed(2).replace('.', ',')} cada)`;
                aviso.classList.remove('hidden');
            } else {
                aviso.classList.add('hidden');
            }
        }

        // 3. Gerar o Pix com o Backend
        async function gerarPix() {
            const qtd = parseInt(document.getElementById('quantidade').value) || 1;
            const precoUnitario = qtd >= 5 ? precoComDesconto : precoBaseAtual;
            const valorTotal = precoUnitario * qtd;
            
            const btn = document.getElementById('btn-gerar-pix');
            btn.innerText = "Gerando Pix...";
            btn.disabled = true;

            const payload = {
                client_id: "site_" + Math.random().toString(36).substring(2, 10), // Gera um ID único para a compra
                produto: produtoSelecionado.nome,
                produto_id: produtoSelecionado.id,
                quantidade: qtd,
                valor_total: parseFloat(valorTotal.toFixed(2))
            };

            try {
                const response = await fetch(`${API_BASE_URL}/gerar-pix`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const dados = await response.json();
                
                if(dados.error) {
                    alert("Erro ao gerar Pix: " + dados.error);
                } else {
                    mostrarPix(dados.qr_code_base64, dados.copia_e_cola);
                }
            } catch (error) {
                alert("Erro de conexão ao tentar gerar o Pix.");
                console.error(error);
            } finally {
                btn.innerText = "Gerar Pix";
                btn.disabled = false;
            }
        }

        function mostrarPix(qrBase64, copiaCola) {
            document.getElementById('btn-gerar-pix').classList.add('hidden');
            document.getElementById('area-pagamento').classList.remove('hidden');
            
            document.getElementById('qr-code-img').src = `data:image/jpeg;base64,${qrBase64}`;
            document.getElementById('input-copia-cola').value = copiaCola;
        }

        function copiarPix() {
            const input = document.getElementById('input-copia-cola');
            input.select();
            document.execCommand('copy');
            alert("Código Pix Copiado!");
        }

        // Inicia o carregamento ao abrir a página
        window.onload = carregarCatalogo;
    </script>
</head>
<body class="bg-gray-50 text-gray-800 font-sans antialiased">

    <!-- Cabeçalho -->
    <header class="bg-gradient-to-r from-blue-900 to-blue-700 text-white py-16 text-center">
        <h1 class="text-4xl font-extrabold mb-4">Setup VIP BR</h1>
        <p class="text-lg text-blue-100 max-w-xl mx-auto">Licenças premium originais com entrega e liberação 100% automática.</p>
    </header>

    <!-- Vitrine de Produtos -->
    <main class="max-w-5xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div class="flex items-center mb-8">
            <span class="bg-blue-100 text-blue-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">Destaque</span>
            <h2 class="ml-4 text-2xl font-bold text-gray-900">Produtos Disponíveis</h2>
        </div>
        
        <!-- Grid gerado dinamicamente -->
        <div id="vitrine" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <!-- Os cards entrarão aqui pelo JS -->
        </div>
    </main>

    <!-- Modal de Checkout -->
    <div id="modal-checkout" class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center hidden z-50 px-4">
        <div class="bg-white rounded-2xl w-full max-w-md p-6 relative shadow-2xl">
            <button onclick="fecharModal()" class="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
            
            <h3 class="text-xl font-bold text-gray-900 mb-1">Finalizar Compra</h3>
            <p id="modal-nome-produto" class="text-gray-500 mb-6"></p>

            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">Quantidade (A partir de 5 un. ganhe desconto)</label>
                <input type="number" id="quantidade" min="1" max="50" value="1" onchange="atualizarPreco()" onkeyup="atualizarPreco()" class="w-full border-gray-300 border rounded-lg px-4 py-2 text-lg focus:ring-blue-500 focus:border-blue-500">
            </div>

            <div class="bg-gray-50 p-4 rounded-lg mb-6 text-center border border-gray-100">
                <span class="block text-sm text-gray-500 mb-1">Total a pagar</span>
                <span id="preco-total" class="text-3xl font-extrabold text-green-600">R$ 0,00</span>
                <p id="aviso-desconto" class="text-sm text-orange-600 font-bold mt-2 hidden"></p>
            </div>

            <button id="btn-gerar-pix" onclick="gerarPix()" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg text-lg transition-colors shadow-lg">
                Gerar Pix
            </button>

            <!-- Área do QR Code (Oculta até gerar) -->
            <div id="area-pagamento" class="hidden mt-6 text-center border-t pt-6">
                <h4 class="font-bold text-gray-900 mb-2">Escaneie o QR Code</h4>
                <img id="qr-code-img" src="" alt="QR Code Pix" class="mx-auto w-48 h-48 border rounded-lg p-2 mb-4">
                
                <h4 class="font-bold text-gray-900 mb-2">Ou use o Pix Copia e Cola</h4>
                <div class="flex">
                    <input type="text" id="input-copia-cola" readonly class="w-full border rounded-l-lg px-3 py-2 text-xs bg-gray-100 text-gray-600">
                    <button onclick="copiarPix()" class="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-r-lg font-bold text-sm">Copiar</button>
                </div>
                <p class="text-xs text-gray-500 mt-4">Após o pagamento, o sistema processará automaticamente a entrega.</p>
            </div>
        </div>
    </div>

</body>
</html>
