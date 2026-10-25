// Roda sozinho a cada deploy no Netlify (veja netlify.toml).
// Busca o catálogo no backend, grava a prévia dentro do index.html e gera a pasta dist/.
// Se o backend estiver fora do ar, reaproveita a prévia do site já publicado. Nunca derruba o deploy.
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, readdirSync, statSync } from 'node:fs';

const API = process.env.CATALOGO_API || 'https://backend-gemini-pro-ocp5.onrender.com';
const SITE = process.env.URL || ''; // o Netlify já informa o endereço do site no build
const CAMPOS = ['id', 'nome', 'descricao', 'precoBase', 'categoria', 'logoDomain'];
const PADRAO = /(<script id="catalogo-inicial" type="application\/json">)([\s\S]*?)(<\/script>)/;
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

async function buscarCatalogo() {
  for (let i = 1; i <= 3; i++) {
    try {
      console.log(`Buscando catálogo (tentativa ${i}/3)...`);
      const r = await fetch(`${API}/api/catalogo`, { signal: AbortSignal.timeout(90000) });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const dados = await r.json();
      if (Array.isArray(dados) && dados.length) return dados;
      throw new Error('catálogo vazio');
    } catch (e) {
      console.log('Falhou:', e.message);
      await dormir(5000);
    }
  }
  return null;
}

async function previaJaPublicada() {
  if (!SITE) return null;
  try {
    const r = await fetch(`${SITE}/index.html`, { signal: AbortSignal.timeout(20000) });
    const m = (await r.text()).match(PADRAO);
    const texto = m && m[2].trim();
    return texto && texto !== '[]' ? texto : null;
  } catch {
    return null;
  }
}

// Acha o HTML do site: usa index.html; se não existir (ex.: subiu como "index (1).html"), usa o index*.html mais recente
function acharHtml() {
  if (existsSync('index.html')) return 'index.html';
  const candidatos = readdirSync('.')
    .filter((f) => /^index.*\.html$/i.test(f))
    .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs || b.localeCompare(a));
  if (candidatos.length) {
    console.log(`Aviso: index.html não encontrado; usando "${candidatos[0]}". Renomeie para index.html no GitHub.`);
    return candidatos[0];
  }
  console.error('ERRO: nenhum index.html na raiz do repositório. Arquivos na raiz: ' + readdirSync('.').join(', '));
  process.exit(1);
}

let html = readFileSync(acharHtml(), 'utf8');
if (!PADRAO.test(html)) {
  console.log('Aviso: bloco da prévia não encontrado no index.html; publicando sem prévia.');
} else {
  const produtos = await buscarCatalogo();
  let texto = null;
  if (produtos) {
    const enxuto = produtos.map((p) => Object.fromEntries(CAMPOS.filter((c) => c in p).map((c) => [c, p[c]])));
    texto = JSON.stringify(enxuto).replace(/<\//g, '<\\/');
    console.log(`Prévia gravada com ${enxuto.length} produtos.`);
  } else {
    texto = await previaJaPublicada();
    console.log(texto ? 'Backend indisponível: reaproveitei a prévia do site publicado.' : 'Backend indisponível e sem prévia anterior: publicando sem prévia.');
  }
  if (texto) html = html.replace(PADRAO, (_m, a, _b, c) => a + texto + c);
}

mkdirSync('dist', { recursive: true });
writeFileSync('dist/index.html', html);
// Arquivos extras que precisam ir para o site publicado (imagem que aparece ao compartilhar o link)
for (const arquivo of ['og-image.jpg']) {
  if (existsSync(arquivo)) {
    copyFileSync(arquivo, `dist/${arquivo}`);
    console.log(`${arquivo} copiado para dist/.`);
  } else {
    console.log(`Aviso: ${arquivo} não encontrado na raiz do repositório.`);
  }
}
console.log('dist/index.html pronto.');
