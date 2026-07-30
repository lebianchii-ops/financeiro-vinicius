import streamlit as st
import json, io, uuid, base64
import requests
from datetime import date, datetime
import calendar as cal_module
import pandas as pd

st.set_page_config(
    page_title="Financeiro — Bruna & Vinicius",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Senha de acesso (opcional) ──────────────────────────────────────
# Escolha da Bruna em 27/07/2026: o painel abre SEM senha. O link e publico,
# entao quem tiver o endereco entra direto.
# Pra voltar a pedir senha depois, basta criar o secret `painel_senha` com a
# senha desejada (Streamlit Cloud > Settings > Secrets) — nada no codigo muda.
def _senha_configurada():
    try:
        return str(st.secrets.get("painel_senha", "")).strip()
    except Exception:
        return ""

_certa = _senha_configurada()
if _certa and not st.session_state.get("autenticado"):
    st.markdown(
        "<h2 style='text-align:center;margin-top:12%'>💰 Financeiro — Bruna & Vinicius</h2>",
        unsafe_allow_html=True,
    )
    _, _meio, _ = st.columns([1, 1, 1])
    with _meio:
        _senha = st.text_input("Senha de acesso", type="password", key="senha_input")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if _senha and _senha == _certa:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    st.stop()

st.markdown("""
<style>
.block-container { padding-top: 1.2rem !important; max-width: 1200px; }
.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background: #f1f5f9; padding: 5px; border-radius: 14px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px; padding: 8px 26px; font-weight: 600;
    color: #64748b; font-size: 0.9rem;
}
.stTabs [aria-selected="true"] {
    background: white !important; color: #4f46e5 !important;
    box-shadow: 0 1px 6px rgba(79,70,229,0.15);
}
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.4rem; }
.stButton > button[kind="primary"] {
    background: #4f46e5; border: none; border-radius: 10px;
    font-weight: 600; transition: background 0.2s;
}
.stButton > button[kind="primary"]:hover { background: #4338ca; }
.stButton > button[kind="secondary"] {
    background: white; border: 1px solid #e2e8f0; border-radius: 8px;
    color: #64748b; font-size: 1rem; padding: 4px 0; min-height: 36px;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.stButton > button[kind="secondary"]:hover {
    background: #f8fafc; border-color: #cbd5e1; color: #1e293b;
}
div[data-testid="metric-container"] {
    background: white; border-radius: 14px; padding: 16px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
[data-testid="stDataFrameContainer"] {
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
div[data-testid="stForm"] {
    background: white; padding: 28px; border-radius: 18px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06); border: none;
}
.stAlert > div { border-radius: 12px; }
.hist-row {
    background: white; border: 1px solid #f1f5f9; border-radius: 12px;
    padding: 12px 16px; margin-bottom: 6px; transition: box-shadow 0.15s;
}
.hist-row:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.07); }
</style>
""", unsafe_allow_html=True)

# ── Constantes ──────────────────────────────────────────────────────
REPO      = "lebianchii-ops/financeiro-vinicius"
DATA_FILE = "lancamentos.json"

TIPOS = [
    "Compra Mercadoria", "Transferência Estoque",
    "Empréstimo Pessoal", "Empréstimo Empresarial",
    "Gasto Empresarial", "Acerto (Pix / Desconto)",
]
DIVISOES    = ["Meio a Meio", "100% Bruna", "100% Vinicius", "% Personalizado"]
STATUS_OPTS = ["Pendente", "Confirmado", "Cancelado"]
MESES_PT    = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
               "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
DIAS_PT     = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]

TIPO_COR = {
    "Compra Mercadoria":       "#f97316",
    "Transferência Estoque":   "#3b82f6",
    "Empréstimo Pessoal":      "#a855f7",
    "Empréstimo Empresarial":  "#7c3aed",
    "Gasto Empresarial":       "#ef4444",
    "Acerto (Pix / Desconto)": "#22c55e",
}
STATUS_COR = {"Pendente": "#f59e0b", "Confirmado": "#22c55e", "Cancelado": "#94a3b8"}

# ── GitHub helpers ──────────────────────────────────────────────────
def get_token():
    """Token do GitHub — vem SO do secrets, nunca escrito aqui no codigo.

    O token e guardado em base64 porque a caixa de Secrets do Streamlit Cloud
    corrompe token colado em texto puro (so os ~8 primeiros caracteres
    sobrevivem). `get_token()` aceita os dois formatos.
    """
    try:
        t = str(st.secrets["github_token"])
    except Exception:
        st.error("❌ Falta o secret `github_token` nas configuracoes do app.")
        st.stop()
    t = ''.join(c for c in t if ord(c) < 128).strip()
    if t.startswith("ghp_") or t.startswith("github_pat_"):
        return t
    try:
        return base64.b64decode(t).decode("ascii").strip()
    except Exception:
        return t

def _headers():
    return {"Authorization": f"token {get_token()}"}

def carregar():
    # Leitura pela API com token — funciona com o repositorio publico OU privado
    # (a leitura por raw.githubusercontent so funcionava enquanto ele fosse publico)
    url = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE}"
    try:
        r = requests.get(url, headers=_headers(), timeout=20)
    except Exception:
        st.error("❌ Sem conexao com o GitHub. Recarregue a pagina.")
        st.stop()
    if r.status_code == 200:
        info = r.json()
        st.session_state["sha"] = info["sha"]
        return json.loads(base64.b64decode(info["content"]).decode())
    st.session_state["sha"] = None
    return []

def salvar(dados):
    url = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE}"

    # Busca o SHA atual ANTES de gravar — se a Bruna e o Vinicius mexerem quase
    # ao mesmo tempo, o SHA guardado na sessao fica velho e o GitHub recusa
    sha = st.session_state.get("sha")
    try:
        r_get = requests.get(url, headers=_headers(), timeout=20)
        if r_get.status_code == 200:
            sha = r_get.json()["sha"]
    except Exception:
        pass

    payload = {
        "message": f"update {datetime.now().strftime('%d/%m %H:%M')}",
        "content": base64.b64encode(
            json.dumps(dados, ensure_ascii=False, indent=2).encode()
        ).decode(),
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(url, headers=_headers(), json=payload, timeout=60)
    except Exception:
        st.error("❌ Sem conexao ao salvar. Tente de novo.")
        return False
    if r.status_code in [200, 201]:
        st.session_state["sha"] = r.json()["content"]["sha"]
        return True
    st.error(f"❌ Nao consegui salvar (codigo {r.status_code}). Recarregue a pagina e tente de novo.")
    return False

# ── Helpers ─────────────────────────────────────────────────────────
def brl(v):
    s = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return f"R$ {s}"

def calcular_valor_liquido(valor_total, divisao, pct_bruna, quem_arcou):
    pct_v = 100 - pct_bruna
    if quem_arcou == "Bruna":
        return round(valor_total * pct_v / 100, 2)
    return -round(valor_total * pct_bruna / 100, 2)

def calcular_saldo(lcs):
    saldo = 0.0
    for l in lcs:
        v = l.get("valor_liquido", 0.0)
        if l["tipo"] == "Acerto (Pix / Desconto)":
            saldo = saldo - v if l["quem_arcou"] == "Vinicius" else saldo + v
        else:
            saldo += v
    return round(saldo, 2)

def fmt_data(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%y")
    except Exception:
        return d

def badge(texto, cor):
    return (f"<span style='background:{cor}22;color:{cor};padding:2px 9px;"
            f"border-radius:6px;font-size:0.76rem;font-weight:700;"
            f"white-space:nowrap'>{texto}</span>")

def gerar_calendario_html(lcs, ano, mes):
    datas_map = {}
    for l in lcs:
        d = l["data"][:10]
        if d.startswith(f"{ano:04d}-{mes:02d}"):
            day = int(d[8:10])
            datas_map.setdefault(day, []).append(l["tipo"])

    first_wd, num_days = cal_module.monthrange(ano, mes)
    first_wd = (first_wd + 1) % 7
    cells = [None] * first_wd + list(range(1, num_days + 1))
    while len(cells) % 7 != 0:
        cells.append(None)

    hoje = date.today()
    html = """<div style="background:white;border-radius:16px;padding:18px;
                          box-shadow:0 2px 12px rgba(0,0,0,0.06)">"""
    html += """<div style="display:grid;grid-template-columns:repeat(7,1fr);
                           gap:2px;text-align:center;margin-bottom:6px">"""
    for d in DIAS_PT:
        html += f'<div style="font-size:0.7rem;color:#94a3b8;font-weight:700;padding:3px 0">{d}</div>'
    html += "</div><div style='display:grid;grid-template-columns:repeat(7,1fr);gap:3px;text-align:center'>"

    for cell in cells:
        if cell is None:
            html += "<div></div>"
            continue
        is_hoje = (ano == hoje.year and mes == hoje.month and cell == hoje.day)
        has = cell in datas_map
        if is_hoje:
            bg = "background:#4f46e5;border-radius:10px;"
            nc = "color:white;font-weight:800;"
        elif has:
            bg = "background:#eef2ff;border-radius:10px;"
            nc = "color:#4f46e5;font-weight:700;"
        else:
            bg = ""
            nc = "color:#374151;"
        dots = ""
        if has:
            tipos_u = list(dict.fromkeys(datas_map[cell]))[:4]
            dots = '<div style="display:flex;justify-content:center;gap:2px;margin-top:2px">'
            for t in tipos_u:
                c = TIPO_COR.get(t, "#999")
                dots += f'<span style="width:5px;height:5px;border-radius:50%;background:{c};display:inline-block"></span>'
            dots += "</div>"
        html += f'<div style="padding:5px 2px;{bg}"><div style="font-size:0.82rem;{nc}">{cell}</div>{dots}</div>'

    html += "</div></div>"
    return html

def historico_saldo(lcs):
    if not lcs:
        return pd.DataFrame()
    sl = sorted(lcs, key=lambda x: x["data"])
    run = 0.0
    rows = []
    for l in sl:
        v = l.get("valor_liquido", 0.0)
        if l["tipo"] == "Acerto (Pix / Desconto)":
            run = run - v if l["quem_arcou"] == "Vinicius" else run + v
        else:
            run += v
        rows.append({"Data": pd.to_datetime(l["data"]), "Saldo": round(run, 2)})
    return pd.DataFrame(rows).set_index("Data")

# ── Session state ────────────────────────────────────────────────────
defaults = {
    "mes_cal": date.today().month,
    "ano_cal": date.today().year,
    "editando_id": None,
    "confirmar_delete": None,
    "status_id": None,
    "form_v": 0,
    "lancou_ok": False,
    "sha": None,
    "dados_carregados": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Dados ────────────────────────────────────────────────────────────
if not st.session_state["dados_carregados"]:
    st.session_state["lancamentos"] = carregar()
    st.session_state["dados_carregados"] = True

lancamentos = st.session_state["lancamentos"]
saldo = calcular_saldo(lancamentos)

# ── Header ───────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.markdown("## 💰 Financeiro — Bruna & Vinicius")
with hc2:
    if st.button("🔄 Atualizar", help="Recarregar dados", use_container_width=True):
        st.session_state["dados_carregados"] = False
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📊  Visão Geral", "➕  Lançar", "📋  Histórico"])

# ════════════════════════════════════════════════════════
# TAB 1 — VISÃO GERAL
# ════════════════════════════════════════════════════════
with tab1:
    pendentes   = [l for l in lancamentos if l.get("status","Pendente") == "Pendente"]
    confirmados = [l for l in lancamentos if l.get("status","") == "Confirmado"]
    acertos_lc  = [l for l in lancamentos if l["tipo"] == "Acerto (Pix / Desconto)"]
    total_movimentado = sum(l["valor_total"] for l in lancamentos)

    saldo_confirmado = calcular_saldo(confirmados)
    saldo_pendente   = calcular_saldo(pendentes)

    ultima_data = lancamentos[0]["data"] if lancamentos else None
    ultima_str  = fmt_data(ultima_data) if ultima_data else "—"

    if saldo > 0:
        grad  = "linear-gradient(135deg,#22c55e,#16a34a)"
        quem  = "Vinicius deve para a Bruna"
        emoji = "📤"
    elif saldo < 0:
        grad  = "linear-gradient(135deg,#f87171,#dc2626)"
        quem  = "Bruna deve para o Vinicius"
        emoji = "📥"
    else:
        grad  = "linear-gradient(135deg,#818cf8,#4f46e5)"
        quem  = "Estão quites!"
        emoji = "✅"
    st.markdown(
        f"""<div style="background:{grad};border-radius:20px;padding:28px 36px;
            color:white;box-shadow:0 6px 28px rgba(0,0,0,0.15)">
            <div style="font-size:0.82rem;font-weight:600;opacity:0.85;
                 letter-spacing:.04em;text-transform:uppercase;margin-bottom:4px">
                 {emoji} {quem} — saldo total</div>
            <div style="font-size:3rem;font-weight:800;letter-spacing:-2px;line-height:1">
                 {brl(abs(saldo))}</div>
            <div style="font-size:0.8rem;opacity:0.8;margin-top:10px">
                 Último lançamento: {ultima_str}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)

    def kpi_card(titulo, valor, sub, cor_sub="#64748b", cor_borda=None):
        borda = f"border-left:4px solid {cor_borda};" if cor_borda else ""
        return (
            f"<div style='background:white;border-radius:14px;padding:20px 18px;"
            f"box-shadow:0 2px 10px rgba(0,0,0,0.06);{borda}'>"
            f"<div style='font-size:0.72rem;font-weight:700;color:#94a3b8;"
            f"text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px'>{titulo}</div>"
            f"<div style='font-size:1.4rem;font-weight:800;color:#1e293b;line-height:1.1'>{valor}</div>"
            f"<div style='font-size:0.78rem;color:{cor_sub};margin-top:4px'>{sub}</div>"
            f"</div>"
        )

    with k1:
        cor_conf = "#22c55e" if saldo_confirmado > 0 else ("#dc2626" if saldo_confirmado < 0 else "#94a3b8")
        txt_conf = ("Vinicius deve" if saldo_confirmado > 0 else ("Bruna deve" if saldo_confirmado < 0 else "Quites"))
        st.markdown(
            kpi_card("✅ Confirmado", brl(abs(saldo_confirmado)),
                     f"{txt_conf} — {len(confirmados)} lançamento(s)",
                     cor_conf, "#22c55e"),
            unsafe_allow_html=True,
        )
    with k2:
        cor_pend = "#f59e0b" if pendentes else "#22c55e"
        txt_pend = ("Vinicius deve" if saldo_pendente > 0 else ("Bruna deve" if saldo_pendente < 0 else "Neutro"))
        st.markdown(
            kpi_card("⏳ Aguardando confirmação", brl(abs(saldo_pendente)),
                     f"{txt_pend} — {len(pendentes)} lançamento(s)" if pendentes else "Tudo confirmado ✅",
                     cor_pend, "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_card("💰 Total movimentado", brl(total_movimentado),
                     f"{len(lancamentos)} lançamento(s) no total",
                     "#64748b", "#818cf8"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    col_rec, col_graf = st.columns([1.5, 1])

    with col_rec:
        st.markdown(
            "<div style='font-size:0.8rem;font-weight:700;color:#94a3b8;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px'>"
            "📋 Últimas transações</div>",
            unsafe_allow_html=True,
        )
        recentes = lancamentos[:7]
        for l in recentes:
            tc  = TIPO_COR.get(l["tipo"], "#999")
            stc = STATUS_COR.get(l.get("status","Pendente"), "#999")
            vl  = l.get("valor_liquido", 0.0)
            cor_vl = "#16a34a" if vl >= 0 else "#dc2626"
            sinal  = "+" if vl >= 0 else "−"
            st.markdown(
                f"""<div style='display:flex;align-items:center;gap:12px;
                    background:white;border-radius:10px;padding:10px 14px;
                    margin-bottom:6px;box-shadow:0 1px 4px rgba(0,0,0,0.05)'>
                  <div style='min-width:52px;font-size:0.78rem;font-weight:700;
                       color:#374151'>{fmt_data(l['data'])}</div>
                  <div style='flex:1;min-width:0'>
                    <div style='background:{tc}22;color:{tc};font-size:0.68rem;
                         font-weight:700;border-radius:4px;display:inline-block;
                         padding:1px 6px;margin-bottom:2px'>{l['tipo']}</div>
                    <div style='font-size:0.85rem;font-weight:600;color:#1e293b;
                         white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>
                         {l.get('descricao','—')}</div>
                  </div>
                  <div style='text-align:right;min-width:80px'>
                    <div style='font-size:0.88rem;font-weight:700;color:#1e293b'>
                         {brl(l['valor_total'])}</div>
                    <div style='font-size:0.72rem;color:{cor_vl};font-weight:600'>
                         {sinal}{brl(abs(vl))}</div>
                  </div>
                  <div style='min-width:70px;text-align:right'>
                    <span style='background:{stc}22;color:{stc};font-size:0.68rem;
                         font-weight:700;border-radius:4px;padding:2px 7px'>
                         {l.get('status','Pendente')}</span>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    with col_graf:
        st.markdown(
            "<div style='font-size:0.8rem;font-weight:700;color:#94a3b8;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px'>"
            "📈 Evolução do saldo</div>",
            unsafe_allow_html=True,
        )
        df_hist = historico_saldo(lancamentos)
        if not df_hist.empty:
            st.line_chart(df_hist, color="#4f46e5", use_container_width=True, height=200)
        else:
            st.info("Nenhum dado ainda.")

        st.markdown(
            "<div style='font-size:0.8rem;font-weight:700;color:#94a3b8;"
            "text-transform:uppercase;letter-spacing:.05em;margin:14px 0 8px'>"
            "Por tipo</div>",
            unsafe_allow_html=True,
        )
        tipo_res = {}
        for l in lancamentos:
            t = l["tipo"]
            tipo_res[t] = tipo_res.get(t, {"qtd":0,"total":0.0})
            tipo_res[t]["qtd"]   += 1
            tipo_res[t]["total"] += l["valor_total"]
        for t, info in sorted(tipo_res.items(), key=lambda x: -x[1]["total"]):
            cor = TIPO_COR.get(t, "#999")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:5px 0;border-bottom:1px solid #f1f5f9'>"
                f"<span style='font-size:0.78rem;color:#374151'>"
                f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;"
                f"background:{cor};margin-right:6px'></span>{t}</span>"
                f"<span style='font-size:0.78rem;font-weight:700;color:#1e293b'>{brl(info['total'])}"
                f" <span style='color:#94a3b8;font-weight:400'>({info['qtd']}x)</span></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ════════════════════════════════════════════════════════
# TAB 2 — LANÇAR
# ════════════════════════════════════════════════════════
with tab2:
    fv = st.session_state.form_v

    fornecedores_hist = list(dict.fromkeys(
        l.get("fornecedor","") for l in lancamentos if l.get("fornecedor","").strip()
    ))

    c1, c2, c3 = st.columns(3)

    with c1:
        data_lanc  = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", key=f"data_{fv}")
        tipo       = st.selectbox("Tipo", TIPOS, key=f"tipo_{fv}")
        quem_arcou = st.selectbox("Quem pagou / transferiu / emprestou", ["Bruna","Vinicius"], key=f"quem_{fv}")
        categoria  = st.radio("Categoria", ["💼 Empresarial", "🏠 Pessoal"], horizontal=True, key=f"cat_{fv}")

    with c2:
        descricao = st.text_input("Descrição", key=f"desc_{fv}")

        if fornecedores_hist:
            opcoes_forn = [""] + fornecedores_hist + ["✏️ Outro (digitar)"]
            sel_forn = st.selectbox("Fornecedor / Pessoa", opcoes_forn, key=f"forn_sel_{fv}")
            if sel_forn == "✏️ Outro (digitar)":
                fornecedor = st.text_input("Nome do fornecedor", key=f"forn_novo_{fv}")
            else:
                fornecedor = sel_forn
        else:
            fornecedor = st.text_input("Fornecedor / Pessoa", key=f"forn_{fv}")

        referencia = st.text_input("Referência (opcional)", key=f"ref_{fv}")

    with c3:
        comprovante = st.file_uploader(
            "📎 Comprovante (PDF, imagem)",
            type=["pdf","jpg","jpeg","png","gif"],
            key=f"comp_{fv}",
        )
        if tipo == "Transferência Estoque":
            sku = st.text_input("SKU do produto (ex: LB00123)", key=f"sku_{fv}")
        else:
            sku = ""
        obs = st.text_area("Observação (opcional)", height=100, key=f"obs_{fv}")

    st.markdown("**💰 Valor**")
    va, vb = st.columns([1, 2])
    with va:
        qtd_calc = st.number_input("Quantidade", min_value=1, value=1, step=1, key=f"qtd_calc_{fv}")
    with vb:
        vunit_str = st.text_input("Valor unitário (R$)", key=f"vunit_{fv}", placeholder="ex: 573 ou 573,50")
    try:
        valor_unit = float(vunit_str.replace("R$","").replace(".","").replace(",",".").strip()) if vunit_str.strip() else 0.0
    except ValueError:
        valor_unit = 0.0

    if valor_unit > 0:
        valor_total = round(qtd_calc * valor_unit, 2)
        origem_txt = f"{qtd_calc} × {brl(valor_unit)}" if qtd_calc > 1 else "valor informado"
    else:
        valor_total = 0.0
        origem_txt  = "⚠️ preencha o valor unitário acima"
    cor_total = "#4f46e5" if valor_total > 0 else "#ef4444"
    st.markdown(
        f"<div style='background:#f1f5f9;border-radius:8px;padding:10px 18px;"
        f"margin:4px 0 12px;display:flex;justify-content:space-between;align-items:center'>"
        f"<span style='font-size:0.85rem;color:#64748b;font-weight:600'>{origem_txt}</span>"
        f"<span style='font-size:1.3rem;font-weight:800;color:{cor_total}'>{brl(valor_total)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    pct_bruna    = 50.0
    divisao      = "Integral"
    valor_liquido = abs(valor_total)

    if tipo != "Acerto (Pix / Desconto)":
        st.markdown("---")
        st.markdown("**Como dividir?**")
        divisao = st.radio("Divisão", DIVISOES, horizontal=True, key=f"div_{fv}")

        if divisao == "Meio a Meio":
            pct_bruna = 50.0
        elif divisao == "100% Bruna":
            pct_bruna = 100.0
        elif divisao == "100% Vinicius":
            pct_bruna = 0.0
        else:
            pct_bruna = float(st.number_input(
                "% Bruna (digite e pressione Enter)",
                min_value=0.0, max_value=100.0, value=50.0,
                step=5.0, format="%.0f", key=f"pct_b_{fv}",
            ))
            pct_v = round(100 - pct_bruna, 2)
            vl_b  = round(valor_total * pct_bruna / 100, 2)
            vl_v  = round(valor_total * pct_v    / 100, 2)
            st.markdown(
                f"""<div style='display:flex;gap:14px;margin:8px 0 10px'>
                    <div style='flex:1;background:#fce4ec;border-radius:12px;padding:18px;text-align:center'>
                        <div style='font-size:0.78rem;color:#999;margin-bottom:4px;font-weight:600'>🧑‍💻 BRUNA</div>
                        <div style='font-size:2.2rem;font-weight:800;color:#c62828;line-height:1'>{int(pct_bruna)}%</div>
                        <div style='font-size:1rem;color:#374151;font-weight:700;margin-top:6px'>{brl(vl_b)}</div>
                    </div>
                    <div style='flex:1;background:#e3f2fd;border-radius:12px;padding:18px;text-align:center'>
                        <div style='font-size:0.78rem;color:#999;margin-bottom:4px;font-weight:600'>👤 VINICIUS</div>
                        <div style='font-size:2.2rem;font-weight:800;color:#1565c0;line-height:1'>{int(pct_v)}%</div>
                        <div style='font-size:1rem;color:#374151;font-weight:700;margin-top:6px'>{brl(vl_v)}</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        valor_liquido = calcular_valor_liquido(valor_total, divisao, pct_bruna, quem_arcou)

        if valor_liquido > 0:
            st.caption(f"➡️ Vinicius ficará devendo **{brl(valor_liquido)}** a mais para a Bruna")
        elif valor_liquido < 0:
            st.caption(f"➡️ Bruna ficará devendo **{brl(abs(valor_liquido))}** a mais para o Vinicius")
        else:
            st.caption("➡️ Sem impacto no saldo")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.lancou_ok:
        st.session_state.lancou_ok = False
        st.success("✅ Lançamento registrado com sucesso!")

    if st.button("✅ Lançar", type="primary", use_container_width=True, key=f"btn_lancar_{fv}"):
        if not descricao.strip():
            st.error("Preencha a descrição.")
        elif valor_total <= 0:
            st.error("Preencha o valor total ou o valor unitário.")
        else:
            # Comprovante salvo como base64 no JSON
            comp_b64 = ""
            comp_nome = ""
            if comprovante is not None:
                comp_b64  = base64.b64encode(comprovante.read()).decode()
                comp_nome = comprovante.name

            vl_salvar = abs(valor_total) if tipo == "Acerto (Pix / Desconto)" else valor_liquido
            novo = {
                "id":            str(uuid.uuid4())[:8],
                "data":          str(data_lanc),
                "tipo":          tipo,
                "status":        "Pendente",
                "quem_arcou":    quem_arcou,
                "descricao":     descricao.strip(),
                "fornecedor":    fornecedor.strip(),
                "referencia":    referencia.strip(),
                "comprovante":   comp_nome,
                "comprovante_b64": comp_b64,
                "valor_total":   round(valor_total, 2),
                "divisao":       divisao,
                "pct_bruna":     pct_bruna,
                "valor_liquido": round(vl_salvar, 2),
                "sku":           sku,
                "qtd":           qtd_calc,
                "valor_unit":    round(valor_unit, 2),
                "categoria":     categoria,
                "obs":           obs.strip(),
                "criado_em":     datetime.now().isoformat(),
            }
            lancamentos.insert(0, novo)
            st.session_state["lancamentos"] = lancamentos
            if salvar(lancamentos):
                st.session_state.form_v   += 1
                st.session_state.lancou_ok = True
                st.rerun()
            else:
                st.error("Erro ao salvar. Tente novamente.")

# ════════════════════════════════════════════════════════
# TAB 3 — HISTÓRICO
# ════════════════════════════════════════════════════════
with tab3:

    if st.session_state.editando_id:
        l_edit = next((l for l in lancamentos if l["id"] == st.session_state.editando_id), None)
        if l_edit:
            st.markdown("### ✏️ Editando lançamento")
            with st.form("form_editar"):
                e1, e2, e3 = st.columns(3)
                with e1:
                    nova_data = st.date_input(
                        "Data",
                        value=datetime.strptime(l_edit["data"], "%Y-%m-%d").date(),
                        format="DD/MM/YYYY",
                    )
                    novo_quem = st.selectbox(
                        "Quem pagou",
                        ["Bruna","Vinicius"],
                        index=["Bruna","Vinicius"].index(l_edit.get("quem_arcou","Bruna")),
                    )
                with e2:
                    nova_desc       = st.text_input("Descrição", value=l_edit.get("descricao",""))
                    novo_fornecedor = st.text_input("Fornecedor / Pessoa", value=l_edit.get("fornecedor",""))
                    nova_ref        = st.text_input("Referência", value=l_edit.get("referencia",""))
                with e3:
                    novo_valor = st.number_input(
                        "Valor total (R$)",
                        min_value=0.01,
                        value=float(l_edit.get("valor_total", 0.01)),
                        format="%.2f",
                    )
                    nova_obs = st.text_area("Observação", value=l_edit.get("obs",""), height=90)

                eb1, eb2 = st.columns(2)
                with eb1:
                    salvar_edit = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                with eb2:
                    cancelar    = st.form_submit_button("✖ Cancelar", use_container_width=True)

                if salvar_edit:
                    for i, l in enumerate(lancamentos):
                        if l["id"] == st.session_state.editando_id:
                            novo_vl = calcular_valor_liquido(
                                novo_valor,
                                lancamentos[i].get("divisao", "Meio a Meio"),
                                lancamentos[i].get("pct_bruna", 50.0),
                                novo_quem,
                            )
                            lancamentos[i].update({
                                "data":          str(nova_data),
                                "quem_arcou":    novo_quem,
                                "descricao":     nova_desc.strip(),
                                "fornecedor":    novo_fornecedor.strip(),
                                "referencia":    nova_ref.strip(),
                                "valor_total":   round(novo_valor, 2),
                                "valor_liquido": round(novo_vl, 2),
                                "obs":           nova_obs.strip(),
                            })
                            break
                    st.session_state["lancamentos"] = lancamentos
                    if not salvar(lancamentos):
                        st.stop()
                    st.session_state.editando_id = None
                    st.rerun()
                if cancelar:
                    st.session_state.editando_id = None
                    st.rerun()
            st.divider()

    # Calculadora
    with st.expander("🧮 Calculadora"):
        st.html("""
<style>
  body { margin:0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
  .calc { background:#1e293b; border-radius:16px; padding:16px; max-width:280px; margin:0 auto; }
  .display {
    background:#0f172a; color:#f8fafc; font-size:1.8rem; font-weight:700;
    text-align:right; padding:12px 16px; border-radius:10px;
    margin-bottom:12px; min-height:54px; word-break:break-all; letter-spacing:-0.5px;
  }
  .sub { font-size:0.8rem; color:#64748b; min-height:20px; text-align:right;
         padding:0 16px 4px; }
  .grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
  button {
    background:#334155; color:#f8fafc; border:none; border-radius:10px;
    font-size:1.05rem; font-weight:600; padding:14px 0; cursor:pointer;
    transition:background 0.12s;
  }
  button:hover { background:#475569; }
  button.op  { background:#4f46e5; color:white; }
  button.op:hover { background:#4338ca; }
  button.eq  { background:#22c55e; color:white; grid-column:span 2; }
  button.eq:hover { background:#16a34a; }
  button.cl  { background:#ef4444; color:white; }
  button.cl:hover { background:#dc2626; }
  button.zero { grid-column:span 2; }
</style>
<div class="calc">
  <div class="sub" id="sub"></div>
  <div class="display" id="disp">0</div>
  <div class="grid">
    <button class="cl" data-act="ce">C</button>
    <button data-act="sign">+/−</button>
    <button data-act="pct">%</button>
    <button class="op" data-act="op" data-arg="/">÷</button>
    <button data-act="num" data-arg="7">7</button>
    <button data-act="num" data-arg="8">8</button>
    <button data-act="num" data-arg="9">9</button>
    <button class="op" data-act="op" data-arg="*">×</button>
    <button data-act="num" data-arg="4">4</button>
    <button data-act="num" data-arg="5">5</button>
    <button data-act="num" data-arg="6">6</button>
    <button class="op" data-act="op" data-arg="-">−</button>
    <button data-act="num" data-arg="1">1</button>
    <button data-act="num" data-arg="2">2</button>
    <button data-act="num" data-arg="3">3</button>
    <button class="op" data-act="op" data-arg="+">+</button>
    <button class="zero" data-act="num" data-arg="0">0</button>
    <button data-act="dot">.</button>
    <button class="eq" data-act="eq">=</button>
  </div>
</div>
<script>
  let cur='0', prev='', pendOp='', fresh=false;
  const D=document.getElementById('disp');
  const S=document.getElementById('sub');
  const fmt=v=>{
    const n=parseFloat(v);
    if(isNaN(n))return v;
    return n.toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:8});
  };
  function show(){ D.textContent=fmt(cur); }
  function num(d){ if(fresh){cur='0';fresh=false;} cur=cur==='0'?d:cur+d; show(); }
  function dot(){ if(fresh){cur='0';fresh=false;} if(!cur.includes('.'))cur+='.'; show(); }
  function ce(){ cur='0';prev='';pendOp='';fresh=false;S.textContent='';show(); }
  function sign(){ cur=String(-parseFloat(cur)); show(); }
  function pct(){ cur=String(parseFloat(cur)/100); show(); }
  function op(o){ if(pendOp&&!fresh) eq(); prev=cur; pendOp=o; fresh=true; S.textContent=fmt(prev)+' '+o; }
  function eq(){
    if(!pendOp)return;
    const a=parseFloat(prev), b=parseFloat(cur);
    let r;
    if(pendOp=='/') r=b!==0?a/b:'Erro';
    else if(pendOp=='*') r=a*b;
    else if(pendOp=='-') r=a-b;
    else r=a+b;
    S.textContent=fmt(prev)+' '+pendOp+' '+fmt(cur)+' =';
    cur=String(r); pendOp=''; fresh=true; show();
  }
  document.addEventListener('keydown', function(e){
    const k = e.key;
    if(k>='0' && k<='9'){ num(k); e.preventDefault(); }
    else if(k==='.' || k===','){ dot(); e.preventDefault(); }
    else if(k==='+'){ op('+'); e.preventDefault(); }
    else if(k==='-'){ op('-'); e.preventDefault(); }
    else if(k==='*'){ op('*'); e.preventDefault(); }
    else if(k==='/'){ op('/'); e.preventDefault(); }
    else if(k==='Enter' || k==='='){ eq(); e.preventDefault(); }
    else if(k==='Escape' || k==='Delete'){ ce(); e.preventDefault(); }
    else if(k==='Backspace'){
      cur = cur.length>1 ? cur.slice(0,-1) : '0';
      show(); e.preventDefault();
    }
    else if(k==='%'){ pct(); e.preventDefault(); }
  });
  document.querySelectorAll('.calc button[data-act]').forEach(function(btn){
    btn.addEventListener('click', function(){
      const act = btn.getAttribute('data-act');
      const arg = btn.getAttribute('data-arg');
      if(act==='num') num(arg);
      else if(act==='op') op(arg);
      else if(act==='ce') ce();
      else if(act==='sign') sign();
      else if(act==='pct') pct();
      else if(act==='dot') dot();
      else if(act==='eq') eq();
    });
  });
</script>
""", unsafe_allow_javascript=True)

    # Filtros
    f1, f2, f3, f4 = st.columns([1.4, 1, 1, 1.4])
    with f1:
        filtro_tipo   = st.multiselect("Tipo",   TIPOS,               default=[], placeholder="Todos os tipos")
    with f2:
        filtro_quem   = st.multiselect("Quem",   ["Bruna","Vinicius"],default=[], placeholder="Todos")
    with f3:
        filtro_status = st.multiselect("Status", STATUS_OPTS,         default=[], placeholder="Todos")
    with f4:
        filtro_data   = st.date_input("Período", value=(), format="DD/MM/YYYY")

    dados_filtrados = lancamentos[:]
    if filtro_tipo:
        dados_filtrados = [l for l in dados_filtrados if l["tipo"] in filtro_tipo]
    if filtro_quem:
        dados_filtrados = [l for l in dados_filtrados if l["quem_arcou"] in filtro_quem]
    if filtro_status:
        dados_filtrados = [l for l in dados_filtrados if l.get("status","Pendente") in filtro_status]
    if isinstance(filtro_data, (list, tuple)) and len(filtro_data) == 2:
        d0, d1 = str(filtro_data[0]), str(filtro_data[1])
        dados_filtrados = [l for l in dados_filtrados if d0 <= l["data"] <= d1]

    total_filtrado = sum(l["valor_total"] for l in dados_filtrados)
    impacto_filtrado = 0.0
    for l in dados_filtrados:
        vl = l.get("valor_liquido", 0.0)
        if l["tipo"] == "Acerto (Pix / Desconto)":
            impacto_filtrado += -vl if l["quem_arcou"] == "Vinicius" else vl
        else:
            impacto_filtrado += vl

    hh1, hh2 = st.columns([5, 1])
    with hh1:
        cor_imp_f = "#16a34a" if impacto_filtrado >= 0 else "#dc2626"
        sinal_f   = "+" if impacto_filtrado >= 0 else "−"
        st.markdown(
            f"<div style='color:#64748b;font-size:0.85rem;padding:4px 0'>"
            f"{len(dados_filtrados)} lançamento(s) &nbsp;·&nbsp; "
            f"Total: <b style='color:#1e293b'>{brl(total_filtrado)}</b> &nbsp;·&nbsp; "
            f"Impacto no saldo: <b style='color:{cor_imp_f}'>{sinal_f} {brl(abs(impacto_filtrado))}</b>"
            f"</div>",
            unsafe_allow_html=True)
    with hh2:
        if dados_filtrados:
            df_exp = pd.DataFrame([{
                "Data":        fmt_data(l["data"]),
                "Tipo":        l["tipo"],
                "Status":      l.get("status",""),
                "Quem pagou":  l["quem_arcou"],
                "Descrição":   l.get("descricao",""),
                "Fornecedor":  l.get("fornecedor",""),
                "Valor Total": l["valor_total"],
                "Divisão":     l.get("divisao",""),
                "Referência":  l.get("referencia",""),
                "Obs":         l.get("obs",""),
            } for l in dados_filtrados])
            buf = io.BytesIO()
            df_exp.to_excel(buf, index=False)
            st.download_button("📥 Excel", buf.getvalue(), "lancamentos.xlsx", use_container_width=True)

    ch1, ch2, ch3, ch4, ch5 = st.columns([0.85, 3.2, 1.5, 1.1, 1.2])
    for col, txt in zip([ch1,ch2,ch3,ch4,ch5], ["Data","Descrição","Valor","Status",""]):
        col.markdown(
            f"<div style='font-size:0.72rem;font-weight:700;color:#94a3b8;"
            f"text-transform:uppercase;letter-spacing:.05em;padding-bottom:4px'>{txt}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='border:none;border-top:1.5px solid #e2e8f0;margin:0 0 8px'>",
                unsafe_allow_html=True)

    if not dados_filtrados:
        st.info("Nenhum lançamento encontrado.")
    else:
        for l in dados_filtrados:
            tipo_cor = TIPO_COR.get(l["tipo"], "#999")
            st_cor   = STATUS_COR.get(l.get("status","Pendente"), "#999")
            vl = l.get("valor_liquido", 0.0)
            if l["tipo"] == "Acerto (Pix / Desconto)":
                impacto = -vl if l["quem_arcou"] == "Vinicius" else vl
            else:
                impacto = vl
            cor_imp = "#16a34a" if impacto >= 0 else "#dc2626"
            sinal   = "+" if impacto >= 0 else "−"

            r1, r2, r3, r4, r5 = st.columns([0.85, 3.2, 1.5, 1.1, 1.2])

            with r1:
                criado = l.get("criado_em", "")
                hora_txt = criado[11:16] if len(criado) >= 16 else ""
                st.markdown(
                    f"<div style='font-size:0.85rem;font-weight:700;color:#1e293b'>{fmt_data(l['data'])}</div>"
                    f"<div style='font-size:0.72rem;color:#94a3b8;margin-top:1px'>{hora_txt}</div>"
                    f"<div style='font-size:0.72rem;color:#94a3b8'>{l['quem_arcou']}</div>",
                    unsafe_allow_html=True,
                )
            with r2:
                forn    = f"<span style='color:#94a3b8'> · {l.get('fornecedor','')}</span>" if l.get("fornecedor") else ""
                sku_txt = f"<span style='color:#94a3b8'> · {l.get('sku','')} ({l.get('qtd',1)}x)</span>" if l.get("sku") else ""
                comp_ic = "&nbsp;📎" if l.get("comprovante") or l.get("comprovante_b64") else ""
                obs_ic  = "&nbsp;💬" if l.get("obs") else ""
                st.markdown(
                    f"<div style='margin-bottom:3px'>{badge(l['tipo'], tipo_cor)}</div>"
                    f"<div style='font-size:0.88rem;color:#1e293b;font-weight:600'>"
                    f"{l.get('descricao','')}{comp_ic}{obs_ic}</div>"
                    f"<div style='font-size:0.78rem'>{forn}{sku_txt}</div>",
                    unsafe_allow_html=True,
                )
            with r3:
                st.markdown(
                    f"<div style='font-size:0.92rem;font-weight:700;color:#1e293b'>{brl(l['valor_total'])}</div>"
                    f"<div style='font-size:0.76rem;color:{cor_imp};font-weight:600;margin-top:1px'>"
                    f"{sinal} {brl(abs(impacto))} no saldo</div>",
                    unsafe_allow_html=True,
                )
            with r4:
                st.markdown(badge(l.get("status","Pendente"), st_cor), unsafe_allow_html=True)

            with r5:
                ba, bb, bc = st.columns(3)
                with ba:
                    if st.button("📋", key=f"s_{l['id']}", help="Atualizar status", use_container_width=True):
                        st.session_state.status_id = None if st.session_state.status_id == l["id"] else l["id"]
                        st.rerun()
                with bb:
                    if st.button("✏️", key=f"e_{l['id']}", help="Editar lançamento", use_container_width=True):
                        st.session_state.editando_id = l["id"]
                        st.session_state.status_id   = None
                        st.rerun()
                with bc:
                    if st.button("🗑", key=f"d_{l['id']}", help="Excluir", use_container_width=True):
                        st.session_state.confirmar_delete = l["id"]
                        st.rerun()

            if st.session_state.status_id == l["id"]:
                with st.container():
                    st.markdown(
                        "<div style='background:#f8fafc;border-radius:12px;padding:14px 18px;"
                        "border:1px solid #e2e8f0;margin:4px 0 8px'>",
                        unsafe_allow_html=True,
                    )
                    sp1, sp2, sp3 = st.columns([1, 2, 1])
                    with sp1:
                        novo_status = st.radio(
                            "Status",
                            STATUS_OPTS,
                            index=STATUS_OPTS.index(l.get("status","Pendente")),
                            key=f"st_radio_{l['id']}",
                        )
                    with sp2:
                        nova_obs_inline = st.text_area(
                            "Observação",
                            value=l.get("obs",""),
                            height=80,
                            key=f"st_obs_{l['id']}",
                        )
                        # Download comprovante se houver
                        if l.get("comprovante_b64"):
                            comp_bytes = base64.b64decode(l["comprovante_b64"])
                            st.download_button(
                                "📎 Baixar comprovante",
                                comp_bytes,
                                l.get("comprovante", "comprovante"),
                                key=f"dl_{l['id']}",
                            )
                    with sp3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾 Salvar", type="primary", key=f"sv_st_{l['id']}", use_container_width=True):
                            for i, lc in enumerate(lancamentos):
                                if lc["id"] == l["id"]:
                                    lancamentos[i]["status"] = novo_status
                                    lancamentos[i]["obs"]    = nova_obs_inline.strip()
                                    break
                            st.session_state["lancamentos"] = lancamentos
                            if not salvar(lancamentos):
                                st.stop()
                            st.session_state.status_id = None
                            st.rerun()
                        if st.button("✖ Fechar", key=f"cl_st_{l['id']}", use_container_width=True):
                            st.session_state.status_id = None
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.confirmar_delete == l["id"]:
                st.warning(f"Excluir **{l.get('descricao','')}**? Não pode ser desfeito.")
                cd1, cd2, _ = st.columns([1, 1, 4])
                with cd1:
                    if st.button("✅ Confirmar", key=f"conf_{l['id']}"):
                        lancamentos = [x for x in lancamentos if x["id"] != l["id"]]
                        st.session_state["lancamentos"] = lancamentos
                        if not salvar(lancamentos):
                            st.stop()
                        st.session_state.confirmar_delete = None
                        st.rerun()
                with cd2:
                    if st.button("✖ Não", key=f"canc_{l['id']}"):
                        st.session_state.confirmar_delete = None
                        st.rerun()

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
