from datetime import datetime
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
  """Busca o total de receitas e despesas do mês atual"""
  try:
    conn = conectar_banco()
    cursor = conn.cursor()
    # Pega o ano e mês atuais
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


# --- Menu de Navegação Superior (Estilo App) ---
st.title("💰 Meu Controle")

menu = st.radio(
    "Navegação", ["📊 Resumo do Mês", "💳 Lançar Cartão"], horizontal=True
)
st.divider()

# ==========================================
# ABA 1: RESUMO / DASHBOARD (TELA INICIAL)
# ==========================================
if menu == "📊 Resumo do Mês":
  st.subheader("📅 Resumo de " + datetime.now().strftime("%B / %Y"))

  resumo = obter_resumo_mes()
  receitas = resumo.get("Receita", 0.0)
  despesas = resumo.get("Despesa", 0.0)
  saldo = receitas - despesas

  # Cards de Resumo estilo Bancário
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
      "Dica: Use a aba 'Lançar Cartão' acima para registrar novas despesas de"
      " forma rápida."
  )

# ==========================================
# ABA 2: LANÇAMENTO DE CARTÃO
# ==========================================
elif menu == "💳 Lançar Cartão":
  st.subheader("💳 Lançamento de Cartão")
  st.write("Adicione suas despesas de cartão rapidamente.")

  cartoes_dict, cartao_principal = carregar_cartoes()
  if not cartoes_dict:
    st.warning("Nenhum cartão encontrado. Verifique sua tabela de cartões.")
    st.stop()

  cartao_selecionado = st.selectbox(
      "Cartão de Crédito",
      options=list(cartoes_dict.keys()),
      index=(
          list(cartoes_dict.keys()).index(cartao_principal)
          if cartao_principal in cartoes_dict
          else 0
      ),
  )

  valor = st.number_input(
      "Valor da Despesa (R$)", min_value=0.01, format="%.2f", step=10.0
  )

  parcelado = st.checkbox("Parcelado")
  qtd_parcelas = 1
  if parcelado:
    qtd_parcelas = st.selectbox(
        "Número de vezes", options=list(range(2, 13)), format_func=lambda x: f"{x}x"
    )

  data_compra = st.date_input("Data da Compra", value=datetime.now().date())
  descricao = st.text_input("Descrição", placeholder="Ex: Supermercado, Uber...")

  cats_dict = carregar_categorias()
  cat_selecionada = st.selectbox(
      "Categoria", options=list(cats_dict.keys()) if cats_dict else []
  )

  id_cat = cats_dict.get(cat_selecionada) if cat_selecionada else None
  subs_dict = carregar_subcategorias(id_cat)
  sub_selecionada = st.selectbox(
      "Subcategoria", options=list(subs_dict.keys()) if subs_dict else []
  )
  id_sub = subs_dict.get(sub_selecionada) if sub_selecionada else None

  with st.form("form_envio_despesa"):
    enviar = st.form_submit_button(
        "Cadastrar Despesa", use_container_width=True
    )

    if enviar:
      if not descricao.strip():
        st.error("Por favor, preencha a descrição da despesa.")
      elif not cat_selecionada:
        st.error("Selecione uma categoria.")
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
            st.success("Despesa de cartão cadastrada com sucesso!")

          conn.commit()
          cursor.close()
          conn.close()
        except Exception as ex:
          st.error(f"Erro ao salvar no banco de dados: {ex}")