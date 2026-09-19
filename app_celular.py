from datetime import datetime
from dateutil.relativedelta import relativedelta
import psycopg2
import streamlit as st

# Configuração da página para dispositivos móveis
st.set_page_config(
    page_title="Lançamento de Cartão", page_icon="💳", layout="centered"
)


# Função de conexão inteligente (funciona localmente e na nuvem via Pooler)
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
    # Conexão de fallback para testes locais no VS Code
    return psycopg2.connect(
        host="aws-0-us-east-1.pooler.supabase.com",
        database="postgres",
        user="postgres.vihsucqqzeaestnynffz",
        password=r"gPAc6c9P+_ZV2u$",
        port=6543,
    )


# Funções para buscar dados do banco
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


# --- Interface do Aplicativo no Celular ---
st.title("💳 Lançamento de Cartão")
st.write("Adicione suas despesas de cartão rapidamente pelo celular.")

cartoes_dict, cartao_principal = carregar_cartoes()
if not cartoes_dict:
  st.warning(
      "Nenhum cartão encontrado. Verifique sua conexão ou tabela de cartões."
  )
  st.stop()

# Formulário de Lançamento
with st.form("form_despesa_celular"):
  # 1. Cartão
  cartao_selecionado = st.selectbox(
      "Cartão de Crédito",
      options=list(cartoes_dict.keys()),
      index=(
          list(cartoes_dict.keys()).index(cartao_principal)
          if cartao_principal in cartoes_dict
          else 0
      ),
  )

  # 2. Valor
  valor = st.number_input(
      "Valor da Despesa (R$)", min_value=0.01, format="%.2f", step=10.0
  )

  # 3. Parcelamento
  parcelado = st.checkbox("Parcelado")
  qtd_parcelas = 1
  if parcelado:
    qtd_parcelas = st.selectbox(
        "Número de vezes", options=list(range(2, 13)), format_func=lambda x: f"{x}x"
    )

  # 4. Data da Compra
  data_compra = st.date_input("Data da Compra", value=datetime.now().date())

  # 5. Descrição
  descricao = st.text_input("Descrição", placeholder="Ex: Supermercado, Uber...")

  # 6. Categoria e Subcategoria
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

  # Botão de Envio
  enviar = st.form_submit_button("Cadastrar Despesa", use_container_width=True)

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