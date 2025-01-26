from flask import Flask, jsonify, render_template, request, redirect, flash, session, send_file, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps
from fpdf import FPDF
import os

app = Flask(__name__)
app.secret_key = "dev ander"

# Função para conectar ao banco de dados de transações
def conectar_financas_db():
    return sqlite3.connect("finanças.db")

# Função para conectar ao banco de dados de usuários
def conectar_usuarios_db():
    return sqlite3.connect("usuarios.db")

# Função para conectar ao banco de dados de planejamento
def conectar_planejamento_db():
    return sqlite3.connect("planejamento.db")

# Decorador para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Por favor, faça login para acessar esta página.")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

@app.route("/admin")
@login_required
def admin():
    if not session.get("is_admin"):
        flash("Você não tem permissão para acessar esta página.")
        return redirect("/")  # Redireciona para a página inicial se não for admin
    return render_template("admin.html")


# Criar tabela de notificações
def criar_tabela_notificacoes():
    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mensagem TEXT,
            lida BOOLEAN DEFAULT 0,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios(id)
        )
    """)
    conn.commit()
    conn.close()

# Função para criar notificações
def criar_notificacao(user_id, mensagem):
    try:
        conn = conectar_financas_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notificacoes (user_id, mensagem) VALUES (?, ?)", (user_id, mensagem))
        conn.commit()
        return cursor.lastrowid  # Retorna o ID da notificação criada
    except Exception as e:
        print(f"Erro ao criar notificação: {e}")
        return None
    finally:
        conn.close()

# Página inicial
def obter_transacoes(user_id, tipo_filtro="", categoria_filtro="", page=1, per_page=5):
    conn = conectar_financas_db()
    cursor = conn.cursor()

    query = "SELECT * FROM transacoes WHERE user_id = ?"
    params = [user_id]

    if tipo_filtro:
        query += " AND tipo = ?"
        params.append(tipo_filtro)

    if categoria_filtro:
        query += " AND categoria = ?"
        params.append(categoria_filtro)

    query += " ORDER BY data DESC LIMIT ? OFFSET ?"
    params.append(per_page)
    params.append((page - 1) * per_page)

    cursor.execute(query, params)
    transacoes = cursor.fetchall()

    # Obter o total de transações
    cursor.execute("SELECT COUNT(*) FROM transacoes WHERE user_id = ?", (user_id,))
    total_transacoes = cursor.fetchone()[0]
    conn.close()

    total_pages = (total_transacoes + per_page - 1) // per_page
    return transacoes, total_transacoes, total_pages

@app.route("/")
@login_required
def index():
    tipo_filtro = request.args.get("tipo", "")
    categoria_filtro = request.args.get("categoria", "")
    page = request.args.get("page", 1, type=int)

    transacoes, total_transacoes, total_pages = obter_transacoes(
        session["user_id"], tipo_filtro, categoria_filtro, page
    )

    # Obter o nome do usuário logado
    conn = conectar_usuarios_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM usuarios WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    conn.close()

    username = user[0] if user else "Usuário"

    return render_template(
        "index.html",
        transacoes=transacoes,
        tipo_filtro=tipo_filtro,
        categoria_filtro=categoria_filtro,
        username=username,
        page=page,
        total_pages=total_pages,
    )

# Registrar transação
@app.route("/registrar", methods=["POST"])
@login_required
def registrar():
    descricao = request.form["descricao"]
    valor = float(request.form["valor"])
    tipo = request.form["tipo"]
    categoria = request.form["categoria"]
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO transacoes (descricao, valor, tipo, categoria, data, user_id) VALUES (?, ?, ?, ?, ?, ?)""",
        (descricao, valor, tipo, categoria, data, session["user_id"]),
    )
    
    conn.commit()
    conn.close()

    # Criar notificação
    criar_notificacao(session["user_id"], f"Transação registrada: {descricao} - R$ {valor:.2f}")
    
    flash("Transação registrada com sucesso!")
    return redirect("/")

# Exibir saldo atual
@app.route("/saldo")
@login_required
def saldo():
    conn = conectar_financas_db()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE -valor END) AS saldo 
            FROM transacoes WHERE user_id = ?""",
        (session["user_id"],)
    )
    saldo_atual = cursor.fetchone()[0]
    saldo_atual = saldo_atual if saldo_atual else 0.0

    cursor.execute(
        """SELECT * FROM transacoes WHERE user_id = ? 
            ORDER BY data DESC LIMIT 5""",
        (session["user_id"],)
    )
    transacoes = cursor.fetchall()

    cursor.execute(
        """SELECT categoria, SUM(valor) AS valor FROM transacoes 
            WHERE user_id = ? GROUP BY categoria""",
        (session["user_id"],)
    )
    despesas_por_categoria = cursor.fetchall()

    cursor.execute(
        """SELECT strftime('%Y-%m', data) AS mes, SUM(valor) AS total 
            FROM transacoes WHERE user_id = ? GROUP BY mes""",
        (session["user_id"],)
    )
    gastos_mensais = cursor.fetchall()

    cursor.execute(
        """SELECT strftime('%Y-%m', data) AS mes, SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE -valor END) 
            FROM transacoes WHERE user_id = ? GROUP BY mes""",
        (session["user_id"],)
    )
    saldo_mensal = cursor.fetchall()

    conn.close()

    return render_template("saldo.html", 
                            saldo=saldo_atual, 
                            transacoes=transacoes, 
                            despesas_por_categoria=despesas_por_categoria, 
                            gastos_mensais=gastos_mensais, 
                            saldo_mensal=saldo_mensal)

@app.route("/resumo")
@login_required
def resumo():
    mes_atual = datetime.now().strftime("%Y-%m")
    conn = conectar_financas_db()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT tipo, SUM(valor) FROM transacoes WHERE data LIKE ? GROUP BY tipo""",
        (f"{mes_atual}%",),
    )
    resumo = cursor.fetchall()

    cursor.execute(
        """SELECT descricao, valor, tipo, categoria, data FROM transacoes WHERE data LIKE ? ORDER BY data DESC""",
        (f"{mes_atual}%",),
    )
    transacoes = cursor.fetchall()
    conn.close()

    entradas = sum(r[1] for r in resumo if r[0] == "entrada")
    saidas = sum(r[1] for r in resumo if r[0] == "saida")
    total = entradas - saidas
    saldo = entradas - saidas

    return render_template(
        "resumo.html", 
        entradas=entradas, 
        saídas=saidas, 
        saldo=saldo,  
        total=total, 
        transacoes=transacoes
    )

# Gerar PDF com o resumo e transações
@app.route("/exportar_pdf")
@login_required
def exportar_pdf():
    mes_atual = datetime.now().strftime("%Y-%m")
    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT tipo, SUM(valor) FROM transacoes WHERE data LIKE ? GROUP BY tipo""",
        (f"{mes_atual}%",),
    )
    resumo = cursor.fetchall()

    cursor.execute(
        """SELECT descricao, valor, tipo, categoria, data FROM transacoes WHERE data LIKE ? ORDER BY data DESC""",
        (f"{mes_atual}%",),
    )
    transacoes = cursor.fetchall()
    conn.close()

    entradas = sum(r[1] for r in resumo if r[0] == "entrada")
    saidas = sum(r[1] for r in resumo if r[0] == "saida")
    total = entradas - saidas

    pdf = FPDF()
    pdf.add_page()
    
    # Definindo fundo preto
    pdf.set_fill_color(0, 0, 0)
    pdf.rect(0, 0, 210, 297, 'F')  # Fundo preto

    pdf.set_font("Arial", size=12)
    pdf.set_text_color(0, 255, 255)  # Azul neon

    pdf.cell(200, 10, txt="Resumo Mensal", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Mês: {mes_atual}", ln=True)
    pdf.cell(200, 10, txt=f"Entradas: R$ {entradas:.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Saídas: R$ {saidas:.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Total: R$ {total:.2f}", ln=True)

    pdf.cell(200, 10, txt="Transações Detalhadas:", ln=True)
    pdf.cell(200, 10, txt="Descrição | Valor | Tipo | Categoria | Data", ln=True)

    for transacao in transacoes:
        descricao, valor, tipo, categoria, data = transacao
        pdf.cell(200, 10, txt=f"{descricao} | R$ {valor:.2f} | {tipo} | {categoria} | {data}", ln=True)

    pdf_file = f'resumo_{mes_atual}.pdf'
    pdf.output(pdf_file)

    if os.path.exists(pdf_file):
        return send_file(pdf_file, as_attachment=True)
    else:
        flash("Erro ao gerar o PDF.")
        return redirect("/resumo")

# Confirmar exclusão
@app.route("/excluir/<int:transacao_id>", methods=["POST"])
@login_required
def excluir_transacao(transacao_id):
    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute("SELECT descricao, valor FROM transacoes WHERE id = ?", (transacao_id,))
    transacao = cursor.fetchone()
    
    cursor.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))
    conn.commit()
    conn.close()

    # Criar notificação
    criar_notificacao(session["user_id"], f"Transação excluída: {transacao[0]} - R$ {transacao[1]:.2f}")

    flash("Transação excluída com sucesso!")
    return redirect("/")

# Editar transação
@app.route("/editar/<int:transacao_id>", methods=["GET", "POST"])
@login_required
def editar_transacao(transacao_id):
    conn = conectar_financas_db()
    cursor = conn.cursor()

    if request.method == "POST":
        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        tipo = request.form["tipo"]
        categoria = request.form["categoria"]

        cursor.execute(
            """UPDATE transacoes SET descricao = ?, valor = ?, tipo = ?, categoria = ? WHERE id = ?""",
            (descricao, valor, tipo, categoria, transacao_id),
        )
        conn.commit()
        conn.close()
        
        # Criar notificação
        criar_notificacao(session["user_id"], f"Transação editada: {descricao} - R$ {valor:.2f}")

        flash("Transação atualizada com sucesso!")
        return redirect("/")

    cursor.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,))
    transacao = cursor.fetchone()
    conn.close()
    return render_template("editar.html", transacao=transacao)

# Página de registro
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        try:
            conn = conectar_usuarios_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, password) VALUES (?, ?)",
                (username, hashed_password),
            )
            conn.commit()
            conn.close()
            flash("Usuário registrado com sucesso!")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Nome de usuário já existe. Tente outro.")
            return redirect("/registro")

    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = conectar_usuarios_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password, is_admin FROM usuarios WHERE username = ?", (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            if check_password_hash(user[1], password):
                session["user_id"] = user[0]
                session["is_admin"] = user[2]  # Armazena se o usuário é admin
                flash("Login realizado com sucesso!")

                # Verifica se o usuário é admin
                if user[2]:  # user[2] é o valor de is_admin
                    return redirect("/admin")  # Redireciona para a página de admin
                else:
                    return redirect("/")  # Redireciona para a página normal

            else:
                flash("Senha incorreta.")
        else:
            flash("Usuário não encontrado.")

        return redirect("/login")  # Redireciona se falhar

    return render_template("login.html")  # Retorna o template para o método GET

# Rota para logout
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Você saiu com sucesso.")
    return redirect("/login")

@app.route("/planejamento")
@login_required
def listar_planejamentos():
    conn = conectar_planejamento_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM planejamento WHERE user_id = ?", (session["user_id"],)
    )
    planejamentos = cursor.fetchall()
    conn.close()
    return render_template("listar.html", planejamentos=planejamentos)

@app.route("/planejamento/novo", methods=["GET", "POST"])
@login_required
def criar_planejamento():
    if request.method == "POST":
        descricao = request.form["descricao"]
        valor_meta = float(request.form["valor_meta"])
        prazo = request.form["prazo"]
        
        conn = conectar_planejamento_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO planejamento (user_id, descricao, valor_meta, prazo)
            VALUES (?, ?, ?, ?)
            """,
            (session["user_id"], descricao, valor_meta, prazo),
        )
        conn.commit()
        conn.close()

        # Criar notificação
        criar_notificacao(session["user_id"], f"Novo planejamento criado: {descricao} - Meta: R$ {valor_meta:.2f}")

        flash("Planejamento criado com sucesso!")
        return redirect("/planejamento")

    return render_template("novo.html")

@app.route("/planejamento/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_planejamento(id):
    conn = conectar_planejamento_db()
    cursor = conn.cursor()

    if request.method == "POST":
        descricao = request.form["descricao"]
        valor_meta = float(request.form["valor_meta"])
        valor_atual = float(request.form["valor_atual"])
        prazo = request.form["prazo"]

        cursor.execute(
            """
            UPDATE planejamento
            SET descricao = ?, valor_meta = ?, valor_atual = ?, prazo = ?
            WHERE id = ? AND user_id = ?
            """,
            (descricao, valor_meta, valor_atual, prazo, id, session["user_id"]),
        )
        conn.commit()
        conn.close()

        # Criar notificação
        criar_notificacao(session["user_id"], f"Planejamento atualizado: {descricao} - Meta: R$ {valor_meta:.2f}")

        flash("Planejamento atualizado com sucesso!")
        return redirect("/planejamento")

    cursor.execute(
        "SELECT * FROM planejamento WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    planejamento = cursor.fetchone()
    conn.close()
    return render_template("editar2.html", planejamento=planejamento)

@app.route("/planejamento/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_planejamento(id):
    conn = conectar_planejamento_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT descricao, valor_meta FROM planejamento WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    planejamento = cursor.fetchone()
    
    cursor.execute(
        "DELETE FROM planejamento WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    # Criar notificação
    criar_notificacao(session["user_id"], f"Planejamento excluído: {planejamento[0]} - Meta: R$ {planejamento[1]:.2f}")

    flash("Planejamento excluído com sucesso!")
    return redirect("/planejamento")

@app.route("/notificacoes")
@app.route("/notificacoes/<int:pagina>")
@login_required
def notificacoes(pagina=1):
    conn = conectar_financas_db()
    cursor = conn.cursor()
    
    user_id = session["user_id"]  # Certifique-se de que isso está correto
    limite = 10  # Número de notificações por página
    offset = (pagina - 1) * limite

    # Consulta para pegar as notificações com limite e offset
    cursor.execute("SELECT * FROM notificacoes WHERE user_id = ? ORDER BY data_criacao DESC LIMIT ? OFFSET ?", (user_id, limite, offset))
    notificacoes = cursor.fetchall()

    # Consulta para contar o total de notificações
    cursor.execute("SELECT COUNT(*) FROM notificacoes WHERE user_id = ?", (user_id,))
    total_notificacoes = cursor.fetchone()[0]
    total_paginas = (total_notificacoes + limite - 1) // limite  # Cálculo do total de páginas

    print(f"Notificações: {notificacoes}")
    print(f"User ID na sessão: {session['user_id']}")

    conn.close()
    
    return render_template("notificacoes.html", notificacoes=notificacoes, pagina=pagina, total_paginas=total_paginas)

@app.route("/marcar_lida/<int:notificacao_id>")
@login_required
def marcar_lida(notificacao_id):
    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificacoes SET lida = 1 WHERE id = ?", (notificacao_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("notificacoes"))

@app.route("/notificacoes/<int:pagina>")
@login_required
def notificacoes_paginas(pagina=1):
    conn = conectar_financas_db()
    cursor = conn.cursor()
    
    limite = 10  # Número de notificações por página
    offset = (pagina - 1) * limite

    cursor.execute("SELECT * FROM notificacoes WHERE user_id = ? ORDER BY data_criacao DESC LIMIT ? OFFSET ?", (session["user_id"], limite, offset))
    notificacoes = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM notificacoes WHERE user_id = ?", (session["user_id"],))
    total_notificacoes = cursor.fetchone()[0]
    total_paginas = (total_notificacoes + limite - 1) // limite

    conn.close()
    
    return render_template("notificacoes.html", notificacoes=notificacoes, pagina=pagina, total_paginas=total_paginas)

@app.route("/notificacoes/excluir/<int:notificacao_id>", methods=["POST"])
@login_required
def excluir_notificacao(notificacao_id):
    conn = conectar_financas_db()
    cursor = conn.cursor()
    
    # Excluir a notificação pelo ID
    cursor.execute("DELETE FROM notificacoes WHERE id = ? AND user_id = ?", (notificacao_id, session["user_id"]))
    conn.commit()
    conn.close()
    
    return redirect(url_for("notificacoes"))

@app.route("/usuario")
@login_required
def usuario():
    conn = conectar_usuarios_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM usuarios WHERE id = ?", (session["user_id"],))
    usuario = cursor.fetchone()
    conn.close()

    return render_template("usuario.html", usuario=usuario)

from werkzeug.security import generate_password_hash

@app.route("/editar_usuario", methods=["GET", "POST"])
@login_required
def editar_usuario():
    conn = conectar_usuarios_db()
    cursor = conn.cursor()

    if request.method == "POST":
        novo_username = request.form["username"]
        nova_senha = request.form["password"]

        # Hash da nova senha
        hashed_password = generate_password_hash(nova_senha)

        cursor.execute(
            """UPDATE usuarios SET username = ?, password = ? WHERE id = ?""",
            (novo_username, hashed_password, session["user_id"])
        )
        conn.commit()
        conn.close()

        flash("Dados atualizados com sucesso!")
        return redirect("/usuario")

    cursor.execute("SELECT username FROM usuarios WHERE id = ?", (session["user_id"],))
    usuario = cursor.fetchone()
    conn.close()
 
    return render_template("editar_usuario.html", usuario=usuario)

@app.route("/verificar_senha", methods=["POST"])
@login_required
def verificar_senha():
    senha_inserida = request.json.get("senha")
    
    conn = conectar_usuarios_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM usuarios WHERE id = ?", (session["user_id"],))
    usuario = cursor.fetchone()

    if usuario and check_password_hash(usuario[0], senha_inserida):
        # Aqui você deve retornar a senha real, mas **não é recomendado**
        return jsonify({"success": True, "senha": senha_inserida})  # Retorna a senha inserida
    else:
        return jsonify({"success": False, "message": "Senha incorreta."})
    

@app.route("/admin/usuarios")
@login_required
def listar_usuarios():
    if not session.get("is_admin"):
        flash("Você não tem permissão para acessar esta página.")
        return redirect("/")
    
    conn = conectar_usuarios_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, is_admin FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    
    return render_template("listar_usuarios.html", usuarios=usuarios)


@app.route("/admin/usuario/nova", methods=["GET", "POST"])
@login_required
def criar_usuario():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        is_admin = request.form.get("is_admin", False)

        hashed_password = generate_password_hash(password)
        conn = conectar_usuarios_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (username, password, is_admin) VALUES (?, ?, ?)",
            (username, hashed_password, is_admin)
        )
        conn.commit()
        conn.close()
        flash("Usuário criado com sucesso!")
        return redirect(url_for('listar_usuarios'))

    return render_template("criar_usuario.html")

@app.route("/admin/usuario/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_usuario_admin(id):
    conn = conectar_usuarios_db()
    cursor = conn.cursor()

    if request.method == "POST":
        username = request.form["username"]
        is_admin = request.form.get("is_admin", False)

        cursor.execute(
            "UPDATE usuarios SET username = ?, is_admin = ? WHERE id = ?",
            (username, is_admin, id)
        )
        conn.commit()
        conn.close()
        flash("Usuário atualizado com sucesso!")
        return redirect(url_for('listar_usuarios'))

    cursor.execute("SELECT username, is_admin FROM usuarios WHERE id = ?", (id,))
    usuario = cursor.fetchone()
    conn.close()
    
    return render_template("editar_usuario.html", usuario=usuario)

# Verifique se não há outra função com o mesmo nome

@app.route("/admin/usuario/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_usuario(id):
    conn = conectar_usuarios_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!")
    return redirect(url_for('listar_usuarios'))

# Executar o servidor
if __name__ == "__main__":
    criar_tabela_notificacoes()
    PORT = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT, debug=True)