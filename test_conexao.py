import psycopg2

# String de conexão configurada com os seus dados do Supabase
DATABASE_URL = "postgresql://postgres:gPAc6c9P+_ZV2u$@db.vihsucqqzeaestnynffz.supabase.co:5432/postgres"

def testar_conexao_e_dados():
    print("Tentando conectar ao banco de dados do Supabase...")
    try:
        # Estabelece a conexão
        conexao = psycopg2.connect(DATABASE_URL)
        cursor = conexao.cursor()
        
        # 1. Testa a versão para garantir a conexão
        cursor.execute("SELECT version();")
        versao = cursor.fetchone()
        print("\n✅ Conexão realizada com sucesso!")
        print(f"Versão do PostgreSQL: {versao[0]}\n")
        
        # 2. Busca dados da tabela lancamentos
        print("Consultando os últimos lançamentos na tabela 'lancamentos'...")
        # Usamos try/except caso a tabela tenha algum nome diferente ou ainda esteja vazia
        cursor.execute("SELECT * FROM lancamentos ORDER BY 1 DESC LIMIT 10;")
        
        # Pega os nomes das colunas
        colunas = [desc[0] for desc in cursor.description]
        registros = cursor.fetchall()
        
        print(f"\n📊 Colunas encontradas: {colunas}")
        print(f"📁 Total de registros retornados nesta amostra: {len(registros)}\n")
        
        if registros:
            print("--- ÚLTIMOS LANÇAMENTOS ---")
            for i, reg in enumerate(registros, 1):
                print(f"Registro {i}: {reg}")
        else:
            print("⚠️ A tabela 'lancamentos' foi encontrada, mas está vazia.")
            
        # Fecha cursor e conexão
        cursor.close()
        conexao.close()
        print("\nConexão fechada com segurança.")
        
    except Exception as e:
        print("\n❌ Erro ao conectar ou consultar o banco de dados:")
        print(e)

if __name__ == "__main__":
    testar_conexao_e_dados()