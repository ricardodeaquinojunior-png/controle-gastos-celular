from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
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
      cursor.execute("SELECT id, nome, principal FROM cartoes ORDER BY nome;")
      res = cursor.fetchall()
      cartoes = {row[1]: str(row[0]) for row in res}
      principal = next(
          (row[1] for row in res if len(row) > 2 and row[2]),
          list(cartoes.keys())[0] if cartoes else None,
      )
    except Exception:
      conn.rollback()
      cursor.execute("SELECT id, nome FROM cartoes ORDER BY nome;")
      res = cursor.fetchall()
      cartoes = {row[1]: str(row[0]) for row in res}
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


def obter_resumo_mes():
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    ano_mes_atual = datetime.now().strftime("%Y-%m")
    cursor.execute(
        """
            SELECT tipo, SUM(valor) 
            FROM lancamentos 
            WHERE TO_CHAR(data_lancamento, 'YYYY-MM') = %s 
            GROUP BY tipo;
        """,
        (ano_mes_atual,),
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


# --- Menu de Navegação Superior ---
st.title("💰 Meu Controle")

menu = st.radio(
    "Navegação", ["📊 Resumo do Mês", "💳 Nova Despesa"], horizontal=True
)
st.divider()

# ==========================================
# ABA 1: RESUMO DO MÊS
# ==========================================
if menu == "📊 Resumo do Mês":
  st.subheader("📅 Resumo de " + datetime.now().strftime("%B / %Y"))

  resumo = obter_resumo_mes()
  receitas = resumo.get("Receita", 0.0)
  despesas = resumo.get("Despesa", 0.0)
  saldo = receitas - despesas

  col1, col2 = st.columns(2)
  with col1:
    st.metric(label="🟢 Receitas", value=f"R$ {receitas:,.2f}")
  with col2:
    st.metric(label="🔴 Despesas", value=f"R$ {despesas:,.2f}")

  st.metric(
      label="💼 Saldo do Mês",
      value=f"R$ {saldo:,.2f}",
      delta=f"R$ {saldo:,.2f}",
  )

  st.info(
      "Dica: Toque em 'Nova Despesa' no menu acima para registrar um gasto com"
      " cartão de forma rápida."
  )

# ==========================================
# ABA 2: NOVA DESPESA CARTÃO (Estilo Limpo)
# ==========================================
elif menu == "💳 Nova Despesa":
  st.markdown("### 💳 Nova despesa cartão")

  # 1. Campo de Valor em destaque no topo
  valor = st.number_input(
      "Valor da despesa cartão (R$)",
      min_value=0.01,
      format="%.2f",
      step=10.0,
      value=0.00,
  )

  # 2. Atalhos de Data rápidos (Hoje / Ontem)
  col_d1, col_d2, col_d3 = st.columns(3)
  with col_d1:
    btn_hoje = st.button("📅 Hoje", use_container_width=True)
  with col_d2:
    btn_ontem = st.button("↩️ Ontem", use_container_width=True)
  with col_d3:
    btn_outro = st.button("🗓️ Outra", use_container_width=True)

  # Controla a data selecionada baseada nos botões ou no seletor
  if "data_compra" not in st.session_state:
    st.session_state.data_compra = datetime.now().date()

  if btn_hoje:
    st.session_state.data_compra = datetime.now().date()
  elif btn_ontem:
    st.session_state.data_compra = datetime.now().date() - timedelta(days=1)

  data_compra = st.date_input("Data da Compra", value=st.session_state.data_compra)

  # 3. Descrição
  descricao = st.text_input("📝 Descrição", placeholder="Ex: Supermercado, Uber...")

  # 4. Cartão de Crédito
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

  # 5. Categoria e Subcategoria dinâmicas
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

  # 6. Opção de Parcelamento
  parcelado = st.checkbox("🔁 Despesa Parcelada")
  qtd_parcelas = 1
  if parcelado:
    qtd_parcelas = st.selectbox(
        "Número de parcelas",
        options=list(range(2, 13)),
        format_func=lambda x: f"{x}x",
    )

  st.divider()

  # Botão de Ação Principal (Estilo Concluir)
  if st.button("✔ Cadastrar Despesa", type="primary", use_container_width=True):
    if not descricao.strip():
      st.error("Por favor, preencha a descrição da despesa.")
    elif not cat_selecionada:
      st.error("Selecione uma categoria.")
    elif valor <= 0:
      st.error("O valor da despesa deve ser maior que zero.")
    else:
      try:
        id_cartao = cartoes_dict[cartao_selecionado]
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