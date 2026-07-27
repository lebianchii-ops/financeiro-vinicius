# Financeiro — Bruna & Vinicius

App Streamlit de acerto de contas entre a Bruna e o Vinicius (compra de mercadoria,
transferencia de estoque, emprestimos, acertos por Pix).

- **Pasta local:** `C:\Users\brubi\B.Bianchi\Dashboard Financeiro`
- **Repo:** `lebianchii-ops/financeiro-vinicius`
- **App:** `financeiro-vinicius-3etyrkwsf9rzoaxvwmb22a.streamlit.app`
- **Rodar local:** `rodar_dashboard.bat`
- **Dados:** `lancamentos.json` **no proprio repo**, lidos e gravados pela GitHub
  Contents API (`carregar()` / `salvar()` em `dashboard.py`) — igual ao painel da
  funcionaria. O disco do Streamlit Cloud e descartavel; sem isso os lancamentos
  sumiriam a cada restart.

## Secrets (Streamlit Cloud > Settings > Secrets, e `.streamlit/secrets.toml` local)

```
github_token = "<base64 do token ghp_...>"
painel_senha = "brunavini2026"
```

O token **tem que ser em base64** — a caixa de Secrets do Streamlit Cloud corrompe
token colado em texto puro (so os ~8 primeiros caracteres sobrevivem). `get_token()`
aceita os dois formatos. Mesmo problema documentado no painel da funcionaria.

## Senha do painel

O app e **publico** no Streamlit Cloud (o link abre pra qualquer um, sem pedir login
do Streamlit) mas pede a senha do secret `painel_senha` antes de mostrar qualquer coisa.

Se o secret `painel_senha` nao existir, o app **trava** com "Senha ainda nao configurada"
em vez de abrir com o campo vazio — de proposito: melhor fechado do que aberto pra todo mundo.

## 🚨 Token exposto (27/07/2026) — nao repetir

O `dashboard.py` tinha o token do GitHub escrito dentro do codigo, dividido em duas
strings (`"ghp_2grvYh88u6TN18" + "QO9t0..."`) para escapar do push protection do GitHub.
Como o repositorio e **publico**, esse token ficou a vista de qualquer pessoa — com
escopo `repo`, ou seja, acesso de leitura e escrita a **todos** os repositorios privados
da conta. Removido do codigo em 27/07/2026; o token antigo tem que ser **revogado**
(ele continua no historico do git, entao apagar o codigo nao basta).

**Regra:** token nunca entra no codigo — so em `st.secrets`. Se o secret faltar, o app
avisa e para, em vez de cair num token embutido.

## ⚠️ O repositorio e PUBLICO

`lancamentos.json` (os acertos de conta de voces dois) esta legivel por qualquer um em
github.com/lebianchii-ops/financeiro-vinicius. A senha protege o **app**, nao o
repositorio. Deixar o repo privado resolve — o codigo ja le pela API com token, entao
funciona igual depois de privado; so e preciso dar ao Streamlit Cloud a permissao de
ler repositorios privados.

## Correcoes de 27/07/2026

- `carregar()` lia por `raw.githubusercontent.com` (so funciona com repo publico) —
  passou a ler pela API com token, que funciona nos dois casos.
- `salvar()` usava o SHA guardado na sessao; agora busca o SHA atual antes de gravar
  (se os dois mexerem quase junto, o SHA velho fazia o GitHub recusar) e mostra o
  erro na tela quando falha.
- 3 telas (editar lancamento, mudar status, excluir) chamavam `salvar()` sem olhar o
  resultado e davam `st.rerun()` logo depois — a edicao parecia ter salvado mesmo
  quando falhava. Agora param no erro.

⏳ **Comando de fechamento de sessao** (mesmo texto padrao dos outros projetos):
descreva o que foi feito, regras descobertas, dificuldades — depois salve neste CLAUDE.md.
