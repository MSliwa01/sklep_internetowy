from __future__ import annotations

import os
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    image_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="nowe", nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User", backref=db.backref("orders", lazy=True))


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    order = db.relationship("Order", backref=db.backref("items", lazy=True))
    product = db.relationship("Product")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


def build_database_uri(app: Flask) -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    db_path = os.path.join(app.instance_path, "shop.db")
    return f"sqlite:///{db_path}"


def is_production() -> bool:
    return bool(
        os.environ.get("RENDER") == "true"
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("RENDER_SERVICE_ID")
        or os.environ.get("FLASK_ENV") == "production"
    )


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if is_production():
            raise RuntimeError("SECRET_KEY is required in production.")
        secret_key = "dev-secret-change-me"
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=build_database_uri(app),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        seed_data()

    register_routes(app)
    return app


def seed_data() -> None:
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sklep.local")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    force_reset = os.environ.get("ADMIN_FORCE_RESET") == "1"

    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        admin = User.query.filter_by(email=admin_email).first()

    if not admin:
        if not admin_password:
            if is_production():
                raise RuntimeError("ADMIN_PASSWORD is required in production.")
            admin_password = "admin123"
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            is_admin=True,
        )
        db.session.add(admin)
    else:
        admin.is_admin = True
        if force_reset:
            if not admin_password:
                raise RuntimeError(
                    "ADMIN_PASSWORD is required when ADMIN_FORCE_RESET=1."
                )
            admin.username = admin_username
            admin.email = admin_email
            admin.password_hash = generate_password_hash(admin_password)

    if Product.query.count() == 0:
        sample_products = [
            Product(
                name="Procesor Ryzen 5 7600",
                description="6 rdzeni / 12 watkow, taktowanie do 5.1 GHz.",
                price_cents=109900,
                stock=15,
                image_url="https://placehold.co/600x400?text=CPU",
            ),
            Product(
                name="Karta graficzna RTX 4070",
                description="12 GB GDDR6X, swietna do 1440p.",
                price_cents=289900,
                stock=7,
                image_url="https://placehold.co/600x400?text=GPU",
            ),
            Product(
                name="Pamiec RAM 32 GB DDR5",
                description="2x16 GB, 6000 MHz, CL36.",
                price_cents=54900,
                stock=20,
                image_url="https://placehold.co/600x400?text=RAM",
            ),
            Product(
                name="Dysk SSD NVMe 1 TB",
                description="PCIe 4.0, odczyt do 7000 MB/s.",
                price_cents=35900,
                stock=30,
                image_url="https://placehold.co/600x400?text=SSD",
            ),
            Product(
                name="Plyta glowna B650",
                description="Socket AM5, Wi-Fi 6, 2x M.2.",
                price_cents=79900,
                stock=12,
                image_url="https://placehold.co/600x400?text=MOBO",
            ),
            Product(
                name="Zasilacz 750W Gold",
                description="Certyfikat 80+ Gold, modularny.",
                price_cents=42900,
                stock=18,
                image_url="https://placehold.co/600x400?text=PSU",
            ),
        ]
        db.session.add_all(sample_products)

    db.session.commit()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def format_price(cents: int) -> str:
    return f"{cents / 100:.2f} zl"


def parse_price_to_cents(value: str) -> int | None:
    cleaned = value.strip().replace(",", ".")
    try:
        price = float(cleaned)
    except ValueError:
        return None
    if price <= 0:
        return None
    return int(round(price * 100))


def get_cart() -> dict[str, int]:
    cart = session.get("cart")
    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart
    return cart


def cart_count() -> int:
    return sum(get_cart().values())


def build_cart_items() -> tuple[list[dict], int]:
    cart = get_cart()
    items = []
    total = 0
    for product_id_str, quantity in cart.items():
        product = db.session.get(Product, int(product_id_str))
        if not product:
            continue
        line_total = product.price_cents * quantity
        total += line_total
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )
    return items, total


def register_routes(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        return {
            "cart_count": cart_count(),
            "format_price": format_price,
        }

    @app.route("/")
    def index():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template("index.html", products=products)

    @app.route("/product/<int:product_id>")
    def product_detail(product_id: int):
        product = db.session.get(Product, product_id)
        if not product:
            abort(404)
        return render_template("product.html", product=product)

    @app.route("/cart")
    def cart():
        items, total = build_cart_items()
        return render_template("cart.html", items=items, total=total)

    @app.post("/cart/add/<int:product_id>")
    def cart_add(product_id: int):
        product = db.session.get(Product, product_id)
        if not product:
            abort(404)
        try:
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            quantity = 1
        if quantity < 1:
            flash("Nieprawidlowa ilosc.", "danger")
            return redirect(url_for("product_detail", product_id=product_id))
        cart = get_cart()
        current_qty = cart.get(str(product_id), 0)
        if product.stock < current_qty + quantity:
            flash("Brak wystarczajacej ilosci w magazynie.", "warning")
            return redirect(url_for("product_detail", product_id=product_id))
        cart[str(product_id)] = current_qty + quantity
        session.modified = True
        flash("Dodano do koszyka.", "success")
        return redirect(url_for("cart"))

    @app.post("/cart/update")
    def cart_update():
        cart = get_cart()
        for key in list(cart.keys()):
            field = f"qty_{key}"
            if field not in request.form:
                continue
            try:
                qty = int(request.form.get(field, 0))
            except ValueError:
                qty = 0
            if qty <= 0:
                cart.pop(key, None)
                continue
            product = db.session.get(Product, int(key))
            if not product:
                cart.pop(key, None)
                continue
            if qty > product.stock:
                qty = product.stock
                flash(
                    f"Ilosc dla {product.name} zostala zmniejszona do {qty}.",
                    "warning",
                )
            if qty <= 0:
                cart.pop(key, None)
                continue
            cart[key] = qty
        session.modified = True
        return redirect(url_for("cart"))

    @app.post("/cart/remove/<int:product_id>")
    def cart_remove(product_id: int):
        cart = get_cart()
        cart.pop(str(product_id), None)
        session.modified = True
        return redirect(url_for("cart"))

    @app.route("/checkout", methods=["GET", "POST"])
    @login_required
    def checkout():
        items, total = build_cart_items()
        if not items:
            flash("Koszyk jest pusty.", "info")
            return redirect(url_for("index"))
        if request.method == "POST":
            for item in items:
                if item["quantity"] > item["product"].stock:
                    flash("Brak wystarczajacej ilosci w magazynie.", "danger")
                    return redirect(url_for("cart"))
            order = Order(user_id=current_user.id, total_cents=total)
            db.session.add(order)
            for item in items:
                product = item["product"]
                quantity = item["quantity"]
                product.stock -= quantity
                db.session.add(
                    OrderItem(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price_cents=product.price_cents,
                    )
                )
            db.session.commit()
            session["cart"] = {}
            flash("Zamowienie zostalo przyjete.", "success")
            return redirect(url_for("orders"))
        return render_template("checkout.html", items=items, total=total)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not username or not email or not password:
                flash("Wypelnij wszystkie pola.", "danger")
                return render_template("register.html")
            if User.query.filter(
                (User.username == username) | (User.email == email)
            ).first():
                flash("Uzytkownik o takich danych juz istnieje.", "warning")
                return render_template("register.html")
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            flash("Konto zostalo utworzone. Zaloguj sie.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                flash("Nieprawidlowy email lub haslo.", "danger")
                return render_template("login.html")
            login_user(user)
            flash("Zalogowano pomyslnie.", "success")
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Wylogowano.", "info")
        return redirect(url_for("index"))

    @app.route("/orders")
    @login_required
    def orders():
        orders_list = (
            Order.query.filter_by(user_id=current_user.id)
            .order_by(Order.created_at.desc())
            .all()
        )
        return render_template("orders.html", orders=orders_list)

    @app.route("/orders/<int:order_id>")
    @login_required
    def order_detail(order_id: int):
        order = db.session.get(Order, order_id)
        if not order:
            abort(404)
        if order.user_id != current_user.id and not current_user.is_admin:
            abort(403)
        return render_template("order_detail.html", order=order)

    @app.route("/admin")
    @admin_required
    def admin_index():
        product_count = Product.query.count()
        order_count = Order.query.count()
        return render_template(
            "admin/index.html",
            product_count=product_count,
            order_count=order_count,
        )

    @app.route("/admin/password", methods=["GET", "POST"])
    @admin_required
    def admin_change_password():
        if request.method == "POST":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_password or not new_password or not confirm_password:
                flash("Wypelnij wszystkie pola.", "danger")
                return render_template("admin/password.html")
            if not check_password_hash(
                current_user.password_hash, current_password
            ):
                flash("Aktualne haslo jest nieprawidlowe.", "danger")
                return render_template("admin/password.html")
            if new_password != confirm_password:
                flash("Nowe hasla nie sa takie same.", "warning")
                return render_template("admin/password.html")
            if len(new_password) < 8:
                flash("Haslo musi miec co najmniej 8 znakow.", "warning")
                return render_template("admin/password.html")

            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Haslo admina zostalo zmienione.", "success")
            return redirect(url_for("admin_index"))

        return render_template("admin/password.html")

    @app.route("/admin/products")
    @admin_required
    def admin_products():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template("admin/products.html", products=products)

    @app.route("/admin/products/new", methods=["GET", "POST"])
    @admin_required
    def admin_product_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            price_cents = parse_price_to_cents(request.form.get("price", "0"))
            try:
                stock = int(request.form.get("stock", 0))
            except ValueError:
                stock = 0
            image_url = request.form.get("image_url", "").strip() or None
            if not name or not description or not price_cents:
                flash("Wypelnij wymagane pola.", "danger")
                return render_template("admin/product_form.html", product=None)
            product = Product(
                name=name,
                description=description,
                price_cents=price_cents,
                stock=stock,
                image_url=image_url,
            )
            db.session.add(product)
            db.session.commit()
            flash("Produkt dodany.", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", product=None)

    @app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_product_edit(product_id: int):
        product = db.session.get(Product, product_id)
        if not product:
            abort(404)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            price_cents = parse_price_to_cents(request.form.get("price", "0"))
            try:
                stock = int(request.form.get("stock", 0))
            except ValueError:
                stock = 0
            image_url = request.form.get("image_url", "").strip() or None
            if not name or not description or not price_cents:
                flash("Wypelnij wymagane pola.", "danger")
                return render_template("admin/product_form.html", product=product)
            product.name = name
            product.description = description
            product.price_cents = price_cents
            product.stock = stock
            product.image_url = image_url
            db.session.commit()
            flash("Produkt zaktualizowany.", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", product=product)

    @app.post("/admin/products/<int:product_id>/delete")
    @admin_required
    def admin_product_delete(product_id: int):
        product = db.session.get(Product, product_id)
        if not product:
            abort(404)
        db.session.delete(product)
        db.session.commit()
        flash("Produkt usuniety.", "info")
        return redirect(url_for("admin_products"))

    @app.route("/admin/orders")
    @admin_required
    def admin_orders():
        orders_list = Order.query.order_by(Order.created_at.desc()).all()
        return render_template("admin/orders.html", orders=orders_list)


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug)
