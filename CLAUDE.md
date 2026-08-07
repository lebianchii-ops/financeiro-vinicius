# Financeiro — Bruna & Vinicius

App Streamlit de acerto de contas entre a Bruna e o Vinicius (compra de mercadoria,
transferencia de estoque, emprestimos, acertos por Pix).

- **Pasta local:** `C:\Users\brubi\B.Bianchi\Dashboard Financeiro`
- **Repo:** `lebianchii-ops/financeiro-vinicius`
- **App:** **https://financeiro-bruna-vini.streamlit.app** (subdominio curto, definido em
  27/07/2026). O endereco antigo `financeiro-vinicius-3etyrkwsf9rzoaxvwmb22a.streamlit.app`
  ainda responde, mas e o aleatorio que o Streamlit gera — dificil de digitar no celular,
  foi ele que deu "Safari nao conecta ao servidor" (uma letra errada e o dominio nao existe).
  Sempre passar o curto.
- **Rodar local:** `rodar_dashboard.bat`
- **Dados:** `lancamentos.json` **no proprio repo**, lidos e gravados pela GitHub
  Contents API (`carregar()` / `salvar()` em `dashboard.py`) — igual ao painel da
  funcionaria. O disco do Streamlit Cloud e descartavel; sem isso os lancamentos
  sumiriam a cada restart.

## Secrets (Streamlit Cloud > Settings > Secrets, e `.streamlit/secrets.toml` local)

```
github_token = "<base64 do token ghp_...>"
```

O token **tem que ser em base64** — a caixa de Secrets do Streamlit Cloud corrompe
token colado em texto puro (so os ~8 primeiros caracteres sobrevivem). `get_token()`
aceita os dois formatos. Mesmo problema documentado no painel da funcionaria.

## Senha do painel — DESLIGADA (escolha da Bruna, 27/07/2026)

O app abre **sem senha**: e publico no Streamlit Cloud e quem tiver o link entra direto.
A Bruna decidiu assim depois de eu explicar o risco — e como o repositorio tambem e
publico, os dados ja estavam abertos de qualquer jeito; a senha nao mudaria isso.

A tela de senha continua no codigo, so desligada: **basta criar o secret `painel_senha`**
com a senha desejada que ela volta a aparecer. Sem o secret, o app abre direto.

## 🚨 Token exposto (27/07/2026) — nao repetir

O `dashboard.py` tinha o token do GitHub escrito dentro do codigo, dividido em duas
strings (`"ghp_2grvYh88u6TN18" + "QO9t0..."`) para escapar do push protection do GitHub.
Como o repositorio e **publico**, esse token ficou a vista de qualquer pessoa — com
escopo `repo`, ou seja, acesso de leitura e escrita a **todos** os repositorios privados
da conta. Removido do codigo em 27/07/2026; o token antigo tem que ser **revogado**
(ele continua no historico do git, entao apagar o codigo nao basta).

**Regra:** token nunca entra no codigo — so em `st.secrets`. Se o secret faltar, o app
avisa e para, em vez de cair num token embutido.

## O repositorio e PUBLICO — decisao da Bruna (27/07/2026)

`lancamentos.json` (os acertos de conta dos dois) esta legivel por qualquer um em
github.com/lebianchii-ops/financeiro-vinicius. Expliquei o alcance disso e a Bruna
decidiu **manter publico**. Nao levantar de novo — ja foi perguntado e respondido.

Se um dia ela mudar de ideia: o codigo ja le pela API com token, entao funciona igual
com o repo privado; so e preciso dar ao Streamlit Cloud a permissao de ler repositorios
privados.

## Correcoes de 27/07/2026

- `carregar()` lia por `raw.githubusercontent.com` (so funciona com repo publico) —
  passou a ler pela API com token, que funciona nos dois casos.
- `salvar()` usava o SHA guardado na sessao; agora busca o SHA atual antes de gravar
  (se os dois mexerem quase junto, o SHA velho fazia o GitHub recusar) e mostra o
  erro na tela quando falha.
- 3 telas (editar lancamento, mudar status, excluir) chamavam `salvar()` sem olhar o
  resultado e davam `st.rerun()` logo depois — a edicao parecia ter salvado mesmo
  quando falhava. Agora param no erro.

## Correcoes de 30/07/2026

- **Aba Historico** — cada combinacao de filtro (Tipo/Quem/Status/Periodo) agora mostra
  o total somado e o impacto no saldo dos lancamentos filtrados, ao lado da contagem
  ("9 lancamento(s) · Total: R$ X · Impacto no saldo: +R$ Y").
- **Calculadora estava 100% quebrada (clique E teclado) — corrigido.** Causa raiz:
  `st.html()` ignora `<script>` e atributos `onclick` por padrao (precisa do parametro
  `unsafe_allow_javascript=True`, que nao estava sendo passado). Mesmo com esse parametro,
  o sanitizador (DOMPurify) continua removendo atributos `onclick` inline — a correcao
  definitiva foi trocar `onclick="..."` por `data-act`/`data-arg` + `addEventListener`
  no JS, que sobrevive a sanitizacao. Tambem foi adicionado suporte a digitar pelo
  teclado (numeros, `+ - * /`, Enter/`=`, Backspace, Escape/Delete, `%`) via
  `document.addEventListener('keydown', ...)`. Testado com cliques reais de mouse
  (7×6=42) e teclas reais simuladas via DOM (7+5=12) — funcionando.
- **Regra para qualquer `st.html()` com JS neste projeto (ou outros com calculadora/widget
  custom em HTML):** sempre passar `unsafe_allow_javascript=True` E nunca usar `onclick=`
  inline — usar `data-*` + `addEventListener`, senao o clique fica mudo mesmo com o
  parametro certo.

## Correcoes de 07/08/2026

- **🚨 CAUSA RAIZ REAL de "nao consigo digitar numero, so letra funciona":** a
  **Calculadora** (aba Historico) registra `document.addEventListener('keydown', ...)`
  **sem escopo nenhum** — ela intercepta digitos/`,`/`.`/`+`/`-`/Enter/Backspace da
  PAGINA INTEIRA, mesmo com o expander da calculadora **fechado**, porque o
  `<script>` roda uma vez e o listener fica vivo em `document` pro resto da sessao.
  Resultado: depois de abrir a aba Historico (mesmo sem abrir a calculadora), digitar
  numero em QUALQUER campo do app (ex: Valor unitario no Lancar) parava de funcionar —
  so letras passavam, porque letras nao sao interceptadas pelo handler. Confirmado
  tecnicamente (`event.dispatchEvent` retornando `false` = `preventDefault` disparado
  pela calculadora num campo que nao tinha nada a ver com ela).
  **Correcao:** o wrapper da calculadora ganhou `id="calcWrap"`, e o handler de teclado
  agora checa **`elemento.closest('details').open`** antes de fazer qualquer coisa —
  so intercepta teclado quando a calculadora esta REALMENTE aberta. Importante:
  `offsetParent`/`display` do wrapper NAO sao confiaveis pra essa checagem (o
  Streamlit usa `<details>` nativo por baixo do expander e o conteudo pode ficar
  "visivel" via CSS mesmo fechado) — o unico sinal correto e o `.open` do `<details>`.
  Logica testada isolada (Enter em `document.getElementById('calcWrap').closest('details').open`):
  fechada ignora teclado, aberta processa normal (7+5=12, mesmo teste do fix de 30/07).
- **Regra nova para qualquer widget custom em HTML/JS neste projeto (calculadora ou
  futuro): NUNCA usar `document.addEventListener` sem checar se o proprio widget esta
  visivel/aberto primeiro.** Um listener global de teclado/clique sem esse guard
  vaza pra pagina inteira e quebra outros campos de forma silenciosa e dificil de
  diagnosticar (o campo "parece" quebrado, mas o bug esta em outro componente).
- **Campo "Valor unitario (R$)" (e outros campos de texto livre do Lancar/editar)** —
  alem da causa raiz acima, tambem tinha a caixinha de sugestao nativa do navegador
  (Chrome/Edge) aparecendo por cima, o que so piorava a confusao visual. `st.text_input`
  aceita o parametro `autocomplete` desde a versao instalada (1.57.0) — adicionado
  `autocomplete="off"` em: Descricao, Fornecedor/Pessoa, Referencia, SKU do produto e
  Valor unitario (formulario de lancar) e nos mesmos campos + Valor total do formulario
  de editar lancamento. Testado local: digitou "250,90"/"160,00→160,0099", calculo/valor
  atualizou certo, sem a caixinha de sugestao.
- **Regra para qualquer `st.text_input` novo neste projeto:** sempre passar `autocomplete="off"`.
- **Tela de editar lancamento usava `st.number_input` DENTRO de `st.form`** pro campo
  "Valor total (R$)" — exatamente o padrao ja documentado no CLAUDE.md global como
  perigoso (perde o valor digitado silenciosamente, sem erro nenhum, ja confirmado no
  funcionaria-lb). Era o unico lugar do app que editava valor real de um lancamento ja
  existente sem a protecao que o Lancar (criar) ja tinha. Trocado por `st.text_input` +
  parse manual (mesmo padrao do Valor unitario), com validacao no submit (recusa salvar
  se o valor digitado for invalido ou <= 0, mostra erro e nao fecha o form).

⏳ **Comando de fechamento de sessao** (mesmo texto padrao dos outros projetos):
descreva o que foi feito, regras descobertas, dificuldades — depois salve neste CLAUDE.md.
