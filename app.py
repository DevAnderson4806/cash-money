from flask import Flask, render_template, request, redirect, flash, session, send_file
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

# Decorador para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Por favor, faça login para acessar esta página.")
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

# Página inicial
@app.route("/")
@login_required
def index():
    tipo_filtro = request.args.get("tipo", "")
    categoria_filtro = request.args.get("categoria", "")

    conn = conectar_financas_db()
    cursor = conn.cursor()

    query = "SELECT * FROM transacoes WHERE 1=1"
    params = []

    if tipo_filtro:
        query += " AND tipo = ?"
        params.append(tipo_filtro)

    if categoria_filtro:
        query += " AND categoria = ?"
        params.append(categoria_filtro)

    query += " ORDER BY data DESC"

    cursor.execute(query, params)
    transacoes = cursor.fetchall()
    conn.close()

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
        """INSERT INTO transacoes (descricao, valor, tipo, categoria, data) VALUES (?, ?, ?, ?, ?)""",
        (descricao, valor, tipo, categoria, data),
    )
    conn.commit()
    conn.close()
    flash("Transação registrada com sucesso!")
    return redirect("/")

# Exibir saldo atual
@app.route("/saldo")
@login_required
def saldo():
    conn = conectar_financas_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE -valor END) AS saldo FROM transacoes"""
    )
    saldo_atual = cursor.fetchone()[0]
    conn.close()
    saldo_atual = saldo_atual if saldo_atual else 0.0
    return render_template("saldo.html", saldo=saldo_atual)

# Exibir resumo mensal
from datetime import datetime
from flask import render_template

from datetime import datetime
from flask import render_template

@app.route("/resumo")
@login_required
def resumo():
    mes_atual = datetime.now().strftime("%Y-%m")
    conn = conectar_financas_db()
    cursor = conn.cursor()
    
    # Obter resumo das transações
    cursor.execute(
        """SELECT tipo, SUM(valor) FROM transacoes WHERE data LIKE ? GROUP BY tipo""",
        (f"{mes_atual}%",),
    )
    resumo = cursor.fetchall()

    # Obter transações detalhadas
    cursor.execute(
        """SELECT descricao, valor, tipo, categoria, data FROM transacoes WHERE data LIKE ? ORDER BY data DESC""",
        (f"{mes_atual}%",),
    )
    transacoes = cursor.fetchall()
    conn.close()

    # Calcular entradas, saídas e total
    entradas = sum(r[1] for r in resumo if r[0] == "entrada")
    saidas = sum(r[1] for r in resumo if r[0] == "saida")
    total = entradas - saidas
    saldo = entradas - saidas  # Saldo total para o gráfico de pizza

    return render_template(
        "resumo.html", 
        entradas=entradas, 
        saídas=saidas, 
        saldo=saldo,  # Passando o saldo para o template
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

    # Obter transações detalhadas
    cursor.execute(
        """SELECT descricao, valor, tipo, categoria, data FROM transacoes WHERE data LIKE ? ORDER BY data DESC""",
        (f"{mes_atual}%",),
    )
    transacoes = cursor.fetchall()
    conn.close()

    # Calcular entradas, saídas e total
    entradas = sum(r[1] for r in resumo if r[0] == "entrada")
    saidas = sum(r[1] for r in resumo if r[0] == "saida")
    total = entradas - saidas

    # Criar o PDF
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

    # Adicionar transações detalhadas
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
    cursor.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))
    conn.commit()
    conn.close()
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
            "SELECT id, password FROM usuarios WHERE username = ?", (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            flash("Login realizado com sucesso!")
            return redirect("/")
        else:
            flash("Usuário ou senha inválidos.")
            return redirect("/login")

    return render_template("login.html")

# Rota para logout
@app.route("/logout")
@login_required
def logout():
    session.clear()  # Remove todos os dados da sessão
    flash("Você saiu com sucesso.")
    return redirect("/login")

def conectar_planejamento_db():
    return sqlite3.connect("planejamento.db")

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
        "DELETE FROM planejamento WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Planejamento excluído com sucesso!")
    return redirect("/planejamento")

# Executar o servidor
if __name__ == "__main__":
    # Obtém a porta a partir da variável de ambiente PORT, padrão 5000
    PORT = int(os.getenv("PORT", 5000))

    # Executa o app na interface 0.0.0.0 para ser acessível publicamente
    app.run(host="0.0.0.0", port=PORT, debug=True)