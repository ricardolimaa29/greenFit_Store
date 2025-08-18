from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
produtos = [
    {
        "id": 1,
        "nome": "Whey Protein",
        "descricao": "Suplemento proteico de alta qualidade.",
        "preco": 99.90,
        "categoria": "suplementos",
        "imagem": "whey.jpg"
    },
    {
        "id": 2,
        "nome": "Biquíni de Crochê",
        "descricao": "Feito à mão com fios resistentes.",
        "preco": 149.90,
        "categoria": "moda praia",
        "imagem": "croche.jpg"
    },
    {
        "id": 3,
        "nome": "Kit Cosméticos Naturais",
        "descricao": "Produtos de beleza livres de químicos agressivos.",
        "preco": 79.90,
        "categoria": "cosmeticos",
        "imagem": "image/cosmeticos.jpg"
    }
]
app = Flask(__name__)
app.secret_key = "chave_super_secreta_troque_isto"

# SQLite na raiz do projeto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "loja.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELOS
# =========================
class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), index=True)
    imagem = db.Column(db.String(200))  # opcional

class Pedido(db.Model):
    __tablename__ = "pedidos"
    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(120), nullable=False)
    cliente_email = db.Column(db.String(120), nullable=False)
    cliente_telefone = db.Column(db.String(30), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)

    itens = db.relationship("ItemPedido", backref="pedido", cascade="all, delete-orphan")

class ItemPedido(db.Model):
    __tablename__ = "itens_pedido"
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produtos.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    preco_unit = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)

# =========================
# SEED INICIAL
# =========================
def seed():
    if not Produto.query.first():
        itens = [
            Produto(nome="Whey Protein", descricao="Suplemento proteico 900g.",
                preco=120.00, categoria="suplementos", imagem="whey.jpg"),
            Produto(nome="Camiseta Fitness", descricao="Camiseta confortável para treino.",
                preco=59.90, categoria="roupas", imagem="camiseta fitness.jpg"),
            Produto(nome="Biquíni de Crochê", descricao="Feito à mão, tamanhos P/M/G.",
                preco=149.90, categoria="moda praia", imagem="croche.jpg"),
            Produto(nome="Kit de Cosméticos", descricao="Skin care: sabonete, tônico, hidratante.",
                preco=199.90, categoria="cosmeticos", imagem="cosmeticos.jpg"),
        ]
        db.session.add_all(itens)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed()

# =========================
# HELPERS DO CARRINHO (na sessão)
# carrinho = { str(produto_id): quantidade }
# =========================
def get_carrinho():
    if "carrinho" not in session:
        session["carrinho"] = {}
    return session["carrinho"]

def salvar_carrinho(c):
    session["carrinho"] = c
    session.modified = True

def carrinho_itens_e_total():
    c = get_carrinho()
    ids = [int(pid) for pid in c.keys()]
    produtos = Produto.query.filter(Produto.id.in_(ids)).all() if ids else []
    itens = []
    total = 0.0
    for p in produtos:
        qty = int(c.get(str(p.id), 0))
        subtotal = p.preco * qty
        total += subtotal
        itens.append({"produto": p, "qty": qty, "subtotal": subtotal})
    return itens, total

# =========================
# ROTAS
# =========================
@app.route("/")
def index():
    categoria = request.args.get("categoria", "")
    busca = request.args.get("q", "").strip()

    query = Produto.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    if busca:
        like = f"%{busca}%"
        query = query.filter(Produto.nome.ilike(like) | Produto.descricao.ilike(like))

    produtos = query.order_by(Produto.nome.asc()).all()
    categorias = [c[0] for c in db.session.query(Produto.categoria).distinct().all()]
    return render_template("index.html", produtos=produtos, categorias=categorias,
                           categoria_sel=categoria, q=busca)

@app.route("/adicionar/<int:pid>")
def adicionar(pid):
    produto = Produto.query.get_or_404(pid)
    c = get_carrinho()
    c[str(produto.id)] = c.get(str(produto.id), 0) + 1
    salvar_carrinho(c)
    flash(f"Adicionado: {produto.nome}", "ok")
    return redirect(url_for("index"))

@app.route("/carrinho")
def ver_carrinho():
    itens, total = carrinho_itens_e_total()
    return render_template("carrinho.html", itens=itens, total=total)

@app.route("/mais/<int:pid>")
def mais(pid):
    c = get_carrinho()
    c[str(pid)] = c.get(str(pid), 0) + 1
    salvar_carrinho(c)
    return redirect(url_for("ver_carrinho"))

@app.route("/menos/<int:pid>")
def menos(pid):
    c = get_carrinho()
    key = str(pid)
    if key in c:
        c[key] -= 1
        if c[key] <= 0:
            del c[key]
        salvar_carrinho(c)
    return redirect(url_for("ver_carrinho"))

@app.route("/remover/<int:pid>")
def remover(pid):
    c = get_carrinho()
    c.pop(str(pid), None)
    salvar_carrinho(c)
    return redirect(url_for("ver_carrinho"))

@app.route("/limpar")
def limpar():
    salvar_carrinho({})
    return redirect(url_for("ver_carrinho"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    itens, total = carrinho_itens_e_total()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if not (nome and email and telefone and itens):
            flash("Preencha todos os campos e verifique o carrinho.", "erro")
            return redirect(url_for("checkout"))

        # cria pedido
        pedido = Pedido(cliente_nome=nome, cliente_email=email,
                        cliente_telefone=telefone, total=total)
        db.session.add(pedido)
        db.session.flush()  # obtém pedido.id antes de commit

        # cria itens do pedido
        for item in itens:
            p = item["produto"]
            qty = item["qty"]
            subtotal = item["subtotal"]
            db.session.add(ItemPedido(
                pedido_id=pedido.id,
                produto_id=p.id,
                nome=p.nome,
                preco_unit=p.preco,
                quantidade=qty,
                subtotal=subtotal
            ))
        db.session.commit()

        # limpa carrinho
        salvar_carrinho({})
        return redirect(url_for("pedido", pedido_id=pedido.id))

    return render_template("checkout.html", itens=itens, total=total)

@app.route("/pedido/<int:pedido_id>")
def pedido(pedido_id):
    ped = Pedido.query.get_or_404(pedido_id)
    return render_template("pedido.html", ped=ped)

@app.route("/contato")
def contato():
    return render_template("contato.html")


@app.route("/finalizar")
def finalizar():
    return render_template("finalizar.html")

@app.route("/pedido_finalizado", methods=["POST"])
def pedido_finalizado():
    nome = request.form["nome"]
    endereco = request.form["endereco"]
    pagamento = request.form["pagamento"]
    return f"Pedido de {nome} para {endereco} com pagamento via {pagamento} foi finalizado!"


if __name__ == "__main__":
    app.run(debug=True)
