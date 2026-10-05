from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import psycopg2
import flet as ft

# Conexão direta com o Supabase
DATABASE_URL = "postgresql://postgres:gPAc6c9P+_ZV2u$@db.vihsucqqzeaestnynffz.supabase.co:5432/postgres"

def conectar_banco():
    return psycopg2.connect(DATABASE_URL)

def carregar_cartoes():
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, dia_fechamento, principal FROM cartoes ORDER BY nome;")
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        cartoes = {}
        principal = None
        if res:
            for row in res:
                cid, cnome, fechamento, is_principal = str(row[0]), row[1], row[2] or 24, row[3] or False
                cartoes[cnome] = {"id": cid, "fechamento": fechamento}
                if is_principal:
                    principal = cnome
        if not principal and cartoes:
            principal = list(cartoes.keys())[0]
        return cartoes, principal
    except Exception:
        return {}, None

def carregar_categorias():
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT id_categoria, descricao FROM categorias ORDER BY descricao;")
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return {row[1]: str(row[0]) for row in res} if res else {}
    except Exception:
        return {}

def carregar_subcategorias(id_categoria):
    if not id_categoria:
        return {}
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT id_subcategoria, descricao FROM subcategorias WHERE id_categoria = %s ORDER BY descricao;", (id_categoria,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return {row[1]: str(row[0]) for row in res} if res else {}
    except Exception:
        return {}

def main(page: ft.Page):
    page.title = "Controle Financeiro"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Carrega dados do banco
    cartoes_dict, cartao_principal = carregar_cartoes()
    cats_dict = carregar_categorias()

    # Componentes da Tela
    txt_titulo = ft.Text("💳 Nova Despesa Cartão", size=20, weight=ft.FontWeight.BOLD)
    
    txt_valor = ft.TextField(
        label="Valor da despesa (R$)",
        value="R$ 0,00",
        text_size=20,
        text_align=ft.TextAlign.RIGHT,
        keyboard_type=ft.KeyboardType.NUMBER
    )

    def formatar_moeda(digitos):
        if not digitos:
            return "R$ 0,00"
        valor_int = int(digitos)
        num = valor_int / 100.0
        return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def on_valor_change(e):
        digitos = "".join(filter(str.isdigit, e.control.value))
        txt_valor.data = digitos
        txt_valor.value = formatar_moeda(digitos)
        txt_valor.update()

    txt_valor.data = ""
    txt_valor.on_change = on_valor_change

    # Data atual padrão
    data_atual_str = datetime.now().strftime("%d/%m/%Y")
    txt_data = ft.TextField(label="Data da Compra (DD/MM/AAAA)", value=data_atual_str)

    def set_data_hoje(e):
        txt_data.value = datetime.now().strftime("%d/%m/%Y")
        txt_data.update()

    def set_data_ontem(e):
        ontem = datetime.now().date() - timedelta(days=1)
        txt_data.value = ontem.strftime("%d/%m/%Y")
        txt_data.update()

    btn_hoje = ft.ElevatedButton("📅 Hoje", on_click=set_data_hoje)
    btn_ontem = ft.ElevatedButton("↩️ Ontem", on_click=set_data_ontem)

    txt_descricao = ft.TextField(label="📝 Descrição", hint_text="Ex: Supermercado, Uber...")

    # Dropdowns
    dd_cartao = ft.Dropdown(
        label="💳 Cartão de Crédito",
        options=[ft.dropdown.Option(k) for k in cartoes_dict.keys()],
        value=cartao_principal if cartao_principal in cartoes_dict else (list(cartoes_dict.keys())[0] if cartoes_dict else None)
    )

    dd_categoria = ft.Dropdown(
        label="📂 Categoria",
        options=[ft.dropdown.Option(k) for k in cats_dict.keys()]
    )

    dd_subcategoria = ft.Dropdown(
        label="📂 Subcategoria",
        options=[]
    )

    def on_categoria_change(e):
        cat_nome = dd_categoria.value
        id_cat = cats_dict.get(cat_nome)
        subs = carregar_subcategorias(id_cat)
        dd_subcategoria.options = [ft.dropdown.Option(k) for k in subs.keys()]
        dd_subcategoria.value = None
        dd_subcategoria.update()  # Atualiza o componente na tela

    dd_categoria.on_change = on_categoria_change

    # Status / Mensagens
    lbl_status = ft.Text("", color="red")

    def cadastrar_despesa(e):
        digitos_salvos = txt_valor.data
        try:
            valor_final = int(digitos_salvos) / 100.0 if digitos_salvos else 0.0
        except ValueError:
            valor_final = 0.0

        if valor_final <= 0:
            lbl_status.value = "O valor da despesa deve ser maior que zero."
            lbl_status.update()
            return
        if not txt_descricao.value.strip():
            lbl_status.value = "Por favor, preencha a descrição da despesa."
            lbl_status.update()
            return
        if not dd_categoria.value:
            lbl_status.value = "Selecione uma categoria."
            lbl_status.update()
            return

        try:
            data_compra = datetime.strptime(txt_data.value, "%d/%m/%Y").date()
        except ValueError:
            lbl_status.value = "Formato de data inválido! Use DD/MM/AAAA."
            lbl_status.update()
            return

        try:
            id_cartao = cartoes_dict[dd_cartao.value]["id"]
            id_cat = cats_dict[dd_categoria.value]
            id_sub = carregar_subcategorias(id_cat).get(dd_subcategoria.value) if dd_subcategoria.value else None
            
            conn = conectar_banco()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO lancamentos (tipo, valor, recebido, data_lancamento, descricao, id_categoria, id_subcategoria, id_cartao, repeticoes)
                VALUES ('Despesa', %s, FALSE, %s, %s, %s, %s, %s, 1);
                """,
                (valor_final, data_compra.strftime("%Y-%m-%d"), txt_descricao.value.strip(), id_cat, id_sub, id_cartao)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Limpa os campos para o próximo lançamento
            txt_valor.data = ""
            txt_valor.value = "R$ 0,00"
            txt_descricao.value = ""
            lbl_status.color = "green"
            lbl_status.value = "✔ Despesa cadastrada com sucesso!"
            page.update()

            lbl_status.color = "red"
        except Exception as ex:
            lbl_status.value = f"Erro ao salvar: {ex}"
            lbl_status.update()

    btn_cadastrar = ft.ElevatedButton(
        "✔ Cadastrar Despesa", 
        on_click=cadastrar_despesa, 
        bgcolor="blue", 
        color="white",
        width=400
    )

    # Monta a tela na página
    page.add(
        txt_titulo,
        ft.Divider(),
        txt_valor,
        ft.Row([btn_hoje, btn_ontem], alignment=ft.MainAxisAlignment.CENTER),
        txt_data,
        txt_descricao,
        dd_cartao,
        dd_categoria,
        dd_subcategoria,
        ft.Divider(),
        lbl_status,
        btn_cadastrar
    )

    txt_valor.focus()

ft.app(target=main)