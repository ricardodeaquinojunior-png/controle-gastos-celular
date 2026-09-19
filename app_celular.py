from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import psycopg2
import streamlit as st

# Configuração da página para dispositivos móveis
st.set_page_config(
    page_title="Controle Financeiro", page_icon="💰", layout="centered"
)


# Função de conexão inteligente (Pooler)
def conectar_banco():
  if "supabase" in st.secrets:
    db_conf = st.secrets["supabase"]
    return psycopg2.connect(
        host=db_conf["host"],
        database=db_conf["database"],
        user=db_conf["user"],
        password=db_conf["password"],
        port=db_conf["port"],
    )
  else:
    return psycopg2.connect(
        host="aws-0-us-east-1.pooler.supabase.com",
        database="postgres",
        user="postgres.vihsucqqzeaestnynffz",
        password=r"gPAc6c9P+_ZV2u$",
        port=6543,
    )


# --- Funções de Consulta ao Banco ---
def carregar_cartoes():
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
      cursor.execute(
          "SELECT id, nome, dia_fechamento, principal FROM cartoes ORDER BY"
          " nome;"
      )
      res = cursor.fetchall()
      cartoes = {row[1]: {"id": str(row[0]), "fechamento": row[2] or 24} for row in res}
      principal = next(
          (row[1] for row in res if len(row) > 3 and row[3]),
          list(cartoes.keys())[0] if cartoes else None,
      )
    except Exception:
      conn.rollback()
      cursor.execute("SELECT id, nome, dia_fechamento FROM cartoes ORDER BY nome;")
      res = cursor.fetchall()
      cartoes = {row[1]: {"id": str(row[0]), "fechamento": row[2] or 24} for row in res}
      principal = list(cartoes.keys())[0] if cartoes else None
    cursor.close()
    conn.close()
    return cartoes, principal
  except Exception as e:
    st.error(f"Erro ao carregar cartões: {e}")
    return {}, None


def carregar_categorias():
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT id_categoria, descricao FROM categorias ORDER BY descricao;")
    res = cursor.fetchall()
    cats = {row[1]: str(row[0]) for row in res}
    cursor.close()
    conn.close()
    return cats
  except Exception as e:
    st.error(f"Erro ao carregar categorias: {e}")
    return {}


def carregar_subcategorias(id_categoria):
  if not id_categoria:
    return {}
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id_subcategoria, descricao FROM subcategorias WHERE id_categoria = %s ORDER BY descricao;",
        (id_categoria,),
    )
    res = cursor.fetchall()
    subs = {row[1]: str(row[0]) for row in res}
    cursor.close()
    conn.close()
    return subs
  except Exception as e:
    st.error(f"Erro ao carregar subcategorias: {e}")
    return {}


def obter_resumo_mes(ano_mes):
  """Busca receitas e despesas com base no mês civil selecionado"""
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT tipo, SUM(valor) 
            FROM lancamentos 
            WHERE TO_CHAR(data_lancamento, 'YYYY-MM') = %s 
            GROUP BY tipo;
        """,
        (ano_mes,),
    )
    res = cursor.fetchall()
    cursor.close()
    conn.close()

    totais = {"Receita": 0.0, "Despesa": 0.0}
    for tipo, valor in res:
      if tipo in totais:
        totais[tipo] = float(valor)
    return totais
  except Exception:
    return {"Receita": 0.0, "Despesa": 0.0}


def obter_lancamentos_mes(tipo, ano_mes):
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT data_lancamento, descricao, valor 
            FROM lancamentos 
            WHERE tipo = %s AND TO_CHAR(data_lancamento, 'YYYY-MM') = %s 
            ORDER BY data_lancamento DESC;
        """,
        (tipo, ano_mes),
    )
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res
  except Exception:
    return []


def calcular_ciclo_fatura(d_date, dia_fechamento):
  """Aplica rigorosamente a regra de período de fechamento do cartão"""
  f_dia = min(dia_fechamento, calendar.monthrange(d_date.year, d_date.month)[1])
  if d_date.day > f_dia:
    r_next = d_date + relativedelta(months=1)
    r_ano, r_mes = r_next.year, r_next.month
  else:
    r_ano, r_mes = d_date.year, d_date.month

  max_dia_fim = calendar.monthrange(r_ano, r_mes)[1]
  fim_dia = min(dia_fechamento, max_dia_fim)
  fim = date(r_ano, r_mes, fim_dia)
  inicio = fim - relativedelta(months=1) + relativedelta(days=1)
  return inicio, fim


# --- Menu de Navegação Superior ---
st.title("💰 Meu Controle")

menu = st.radio(
    "Navegação", ["📊 Resumo do Mês", "💳 Nova Despesa"], horizontal=True
)
st.divider()

# ==========================================
# ABA 1: RESUMO DO MÊS E FATURAS POR PERÍODO
# ==========================================
if menu == "📊 Resumo do Mês":
  # Seletor de Período (Passados, Atual e Futuros)
  hoje = datetime.now()
  lista_meses_opcoes = []
  for i in range(-6, 7):  # 6 meses para trás e 6 meses para frente
    m_ref = hoje + relativedelta(months=i)
    lista_meses_opcoes.append(m_ref.strftime("%Y-%m"))

  mes_selecionado = st.selectbox(
      "📅 Selecionar Período (Mês)",
      options=lista_meses_opcoes,
      index=6,  # Índice 6 é o mês atual
      format_func=lambda x: datetime.strptime(x, "%Y-%m").strftime("%B / %Y"),
  )

  st.divider()

  resumo = obter_resumo_mes(mes_selecionado)
  receitas = resumo.get("Receita", 0.0)
  despesas = resumo.get("Despesa", 0.0)
  saldo = receitas - despesas

  col1, col2 = st.columns(2)
  with col1:
    st.metric(label="🟢 Receitas", value=f"R$ {receitas:,.2f}")
  with col2:
    st.metric(label="🔴 Despesas", value=f"R$ {despesas:,.2f}")

  st.metric(
      label="💼 Saldo do Período",
      value=f"R$ {saldo:,.2f}",
      delta=f"R$ {saldo:,.2f}",
  )

  st.divider()

  # --- DETALHAMENTO DE RECEITAS ---
  with st.expander("🔍 Ver detalhes das Receitas"):
    lista_receitas = obter_lancamentos_mes("Receita", mes_selecionado)
    if lista_receitas:
      for data, desc, val in lista_receitas:
        data_fmt = (
            datetime.strptime(str(data), "%Y-%m-%d").strftime("%d/%m")
            if data
            else ""
        )
        st.markdown(f"**{data_fmt}** - {desc}: `R$ {val:,.2f}`")
    else:
      st.info("Nenhuma receita registrada neste período.")

  # --- DETALHAMENTO DE DESPESAS ---
  with st.expander("🔍 Ver detalhes das Despesas"):
    lista_despesas = obter_lancamentos_mes("Despesa", mes_selecionado)
    if lista_despesas:
      for data, desc, val in lista_despesas:
        data_fmt = (
            datetime.strptime(str(data), "%Y-%m-%d").strftime("%d/%m")
            if data
            else ""
        )
        st.markdown(f"**{data_fmt}** - {desc}: `R$ {val:,.2f}`")
    else:
      st.info("Nenhuma despesa registrada neste período.")

  st.divider()

  # --- FATURAS DOS CARTÕES BASEADAS NO PERÍODO SELECIONADO ---
  st.subheader("💳 Faturas dos Cartões (Regra de Período)")

  cartoes_dict, _ = carregar_cartoes()
  if cartoes_dict:
    # Converte mes_selecionado para referência de data do ciclo
    ano_sel, mes_sel = map(int, mes_selecionado.split("-"))

    try:
      conn = conectar_banco()
      cursor = conn.cursor()
      cursor.execute(
          """
                SELECT l.valor, l.data_lancamento, c.nome, c.dia_fechamento 
                FROM lancamentos l
                JOIN cartoes c ON l.id_cartao = c.id
                WHERE l.id_cartao IS NOT NULL;
            """
      )
      todos_lanc_cartoes = cursor.fetchall()
      cursor.close()
      conn.close()

      faturas_por_cartao = {}
      for val, ldata, c_nome, c_fech in todos_lanc_cartoes:
        if not ldata:
          continue
        d_date = ldata.date() if hasattr(ldata, "date") else ldata
        fechamento = c_fech or 24

        inicio_ciclo, fim_ciclo = calcular_ciclo_fatura(d_date, fechamento)

        # O ciclo pertence ao mês da data de fim da fatura
        ciclo_ano_mes = fim_ciclo.strftime("%Y-%m")

        if ciclo_ano_mes == mes_selecionado:
          if c_nome not in faturas_por_cartao:
            faturas_por_cartao[c_nome] = {
                "total": 0.0,
                "inicio": inicio_ciclo,
                "fim": fim_ciclo,
            }
          faturas_por_cartao[c_nome]["total"] += float(val or 0)

      if faturas_por_cartao:
        for c_nome, info in faturas_por_cartao.items():
          periodo_txt = (
              f"Período: {info['inicio'].strftime('%d/%m/%Y')} a"
              f" {info['fim'].strftime('%d/%m/%Y')}"
          )
          st.metric(
              label=f"Cartão: {c_nome} ({periodo_txt})",
              value=f"R$ {info['total']:,.2f}",
          )
      else:
        st.info("Nenhuma fatura calculada para este período específico.")

    except Exception as e:
      st.error(f"Erro ao calcular faturas: {e}")
  else:
    st.info("Nenhum cartão cadastrado.")

# ==========================================
# ABA 2: NOVA DESPESA CARTÃO
# ==========================================
elif menu == "💳 Nova Despesa":
  st.markdown("### 💳 Nova despesa cartão")

  valor = st.number_input(
      "Valor da despesa cartão (R$)",
      min_value=0.01,
      format="%.2f",
      step=10.0,
      value=0.01,
  )

  col_d1, col_d2, col_d3 = st.columns(3)
  with col_d1:
    btn_hoje = st.button("📅 Hoje", use_container_width=True)
  with col_d2:
    btn_ontem = st.button("↩️ Ontem", use_container_width=True)
  with col_d3:
    btn_outro = st.button("🗓️ Outra", use_container_width=True)

  if "data_compra" not in st.session_state:
    st.session_state.data_compra = datetime.now().date()

  if btn_hoje:
    st.session_state.data_compra = datetime.now().date()
  elif btn_ontem:
    st.session_state.data_compra = datetime.now().date() - timedelta(days=1)

  data_compra = st.date_input("Data da Compra", value=st.session_state.data_compra)
  descricao = st.text_input("📝 Descrição", placeholder="Ex: Supermercado, Uber...")

  cartoes_dict, cartao_principal = carregar_cartoes()
  if not cartoes_dict:
    st.warning("Nenhum cartão encontrado. Verifique sua tabela de cartões.")
    st.stop()

  cartao_selecionado = st.selectbox(
      "💳 Cartão de Crédito",
      options=list(cartoes_dict.keys()),
      index=(
          list(cartoes_dict.keys()).index(cartao_principal)
          if cartao_principal in cartoes_dict
          else 0
      ),
  )

  cats_dict = carregar_categorias()
  cat_selecionada = st.selectbox(
      "📂 Categoria", options=list(cats_dict.keys()) if cats_dict else []
  )

  id_cat = cats_dict.get(cat_selecionada) if cat_selecionada else None
  subs_dict = carregar_subcategorias(id_cat)
  sub_selecionada = st.selectbox(
      "📂 Subcategoria", options=list(subs_dict.keys()) if subs_dict else []
  )
  id_sub = subs_dict.get(sub_selecionada) if sub_selecionada else None

  parcelado = st.checkbox("🔁 Despesa Parcelada")
  qtd_parcelas = 1
  if parcelado:
    qtd_parcelas = st.selectbox(
        "Número de parcelas",
        options=list(range(2, 13)),
        format_func=lambda x: f"{x}x",
    )

  st.divider()

  if st.button("✔ Cadastrar Despesa", type="primary", use_container_width=True):
    if not descricao.strip():
      st.error("Por favor, preencha a descrição da despesa.")
    elif not cat_selecionada:
      st.error("Selecione uma categoria.")
    elif valor <= 0:
      st.error("O valor da despesa deve ser maior que zero.")
    else:
      try:
        id_cartao = cartoes_dict[cartao_selecionado]["id"]
        conn = conectar_banco()
        cursor = conn.cursor()
        desc_base = descricao.strip()

        if parcelado:
          valor_parcela = valor / qtd_parcelas
          for i in range(qtd_parcelas):
            data_parcela = data_compra + relativedelta(months=i)
            desc_parcela = f"{desc_base} ({i+1}/{qtd_parcelas})"
            cursor.execute(
                """
                            INSERT INTO lancamentos (tipo, valor, recebido, data_lancamento, descricao, id_categoria, id_subcategoria, id_cartao, repeticoes)
                            VALUES ('Despesa', %s, FALSE, %s, %s, %s, %s, %s, %s);
                        """,
                (
                    valor_parcela,
                    data_parcela.strftime("%Y-%m-%d"),
                    desc_parcela,
                    id_cat,
                    id_sub,
                    id_cartao,
                    qtd_parcelas,
                ),
            )
          st.success(
              f"Despesa parcelada em {qtd_parcelas}x cadastrada com sucesso!"
          )
        else:
          cursor.execute(
              """
                        INSERT INTO lancamentos (tipo, valor, recebido, data_lancamento, descricao, id_categoria, id_subcategoria, id_cartao, repeticoes)
                        VALUES ('Despesa', %s, FALSE, %s, %s, %s, %s, %s, %s);
                    """,
              (
                  valor,
                  data_compra.strftime("%Y-%m-%d"),
                  desc_base,
                  id_cat,
                  id_sub,
                  id_cartao,
                  1,
              ),
          )
          st.success("✔ Despesa de cartão cadastrada com sucesso!")

        conn.commit()
        cursor.close()
        conn.close()
      except Exception as ex:
        st.error(f"Erro ao salvar no banco de dados: {ex}")