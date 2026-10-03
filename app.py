import os
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-secret"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'foodlink.db'}"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
db = SQLAlchemy(app)
CSRFProtect(app)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ROLES = {"donor", "ngo", "consumer", "admin"}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(24), nullable=False, default="servings")
    servings = db.Column(db.Integer, nullable=False)
    food_type = db.Column(db.String(24), nullable=False, default="Vegetarian")
    prepared_at = db.Column(db.DateTime, nullable=False)
    available_until = db.Column(db.DateTime, nullable=False)
    storage = db.Column(db.String(80), nullable=False)
    donation_type = db.Column(db.String(24), nullable=False, default="Free")
    price = db.Column(db.Float, default=0, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255))
    status = db.Column(db.String(24), default="Available", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    donor = db.relationship("User", backref="foods")

    @property
    def priority(self):
        hours = (self.available_until - datetime.utcnow()).total_seconds() / 3600
        age_hours = (datetime.utcnow() - self.prepared_at).total_seconds() / 3600
        if hours <= 6 or (self.storage.lower() == "room temperature" and age_hours >= 4):
            return "High Priority"
        if hours <= 18 or age_hours >= 8:
            return "Medium Priority"
        return "Low Priority"


class FoodRequest(db.Model):
    __tablename__ = "food_requests"

    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food.id"), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_quantity = db.Column(db.Float, nullable=False)
    approved_quantity = db.Column(db.Float)
    pickup_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(24), default="Requested", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    food = db.relationship("Food", backref="requests")
    requester = db.relationship("User", foreign_keys=[requester_id])


class Pickup(db.Model):
    __tablename__ = "pickup"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("food_requests.id"), unique=True, nullable=False)
    status = db.Column(db.String(24), default="Approved", nullable=False)
    pickup_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    food_request = db.relationship("FoodRequest", backref=db.backref("pickup", uselist=False, cascade="all, delete-orphan"))


class FoodAnalytics(db.Model):
    __tablename__ = "food_analytics"

    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food.id"), nullable=False)
    event_type = db.Column(db.String(24), nullable=False)
    servings = db.Column(db.Integer, default=0, nullable=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    food = db.relationship("Food", backref="analytics_events")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(40), default="update", nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User", backref="notifications")


class EmergencyRequest(db.Model):
    __tablename__ = "emergency_requests"

    id = db.Column(db.Integer, primary_key=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    food_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    required_at = db.Column(db.DateTime, nullable=False)
    urgency = db.Column(db.String(20), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(24), default="Open", nullable=False)
    ngo = db.relationship("User", backref="emergencies")


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user().role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def notify(user_id, message, kind="update"):
    db.session.add(Notification(user_id=user_id, message=message, kind=kind))


def parse_datetime(value, fallback=None):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


@app.context_processor
def inject_globals():
    user = current_user()
    unread = Notification.query.filter_by(user_id=user.id, read=False).count() if user else 0
    return {"current_user": user, "unread_count": unread}


@app.route("/")
def home():
    foods = Food.query.filter_by(status="Available").order_by(Food.available_until.asc()).limit(3).all()
    return render_template("home.html", foods=foods)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
        password, role = request.form.get("password", ""), request.form.get("role", "")
        mobile, address = request.form.get("mobile", "").strip(), request.form.get("address", "").strip()
        if not all((name, email, password, mobile, address)) or role not in ROLES - {"admin"}:
            flash("Complete every field and choose a valid account type.", "error")
        elif len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(name=name, email=email, mobile=mobile, address=address, role=role,
                        verified=(role != "ngo"), password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            flash("Welcome to FoodLink. Your account is ready.", "success")
            return redirect(url_for("dashboard"))
    preferred_role = request.form.get("role", "") if request.method == "POST" else request.args.get("role", "")
    return render_template("auth.html", mode="register", preferred_role=preferred_role)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("admin" if user.role == "admin" else "dashboard"))
        flash("Email or password did not match.", "error")
    return render_template("auth.html", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("home"))


@app.get("/donate-food")
def donate_food():
    user = current_user()
    if user and user.role == "donor":
        return redirect(url_for("add_food"))
    if user:
        flash("Food donations are posted by restaurant and food-business accounts. NGOs and community members can find and request food.", "info")
        return redirect(url_for("dashboard"))
    return redirect(url_for("register", role="donor"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user.role == "admin":
        return redirect(url_for("admin"))
    if user.role == "donor":
        foods = Food.query.filter_by(donor_id=user.id).all()
        requests = FoodRequest.query.join(Food).filter(Food.donor_id == user.id).order_by(FoodRequest.created_at.desc()).limit(6).all()
    else:
        foods = Food.query.filter_by(status="Available").order_by(Food.available_until.asc()).limit(6).all()
        requests = FoodRequest.query.filter_by(requester_id=user.id).order_by(FoodRequest.created_at.desc()).limit(6).all()
    user_requests = FoodRequest.query.filter_by(requester_id=user.id)
    return render_template("dashboard.html", foods=foods, requests=requests,
                           stats={"listings": Food.query.filter_by(donor_id=user.id).count(),
                                  "collected": user_requests.filter_by(status="Completed").count(),
                                  "pending": user_requests.filter_by(status="Requested").count(),
                                  "saved": sum(f.servings for f in foods)})


@app.route("/add-food", methods=["GET", "POST"])
@roles_required("donor")
def add_food():
    if request.method == "POST":
        try:
            quantity, servings, price = float(request.form["quantity"]), int(request.form["servings"]), float(request.form.get("price") or 0)
            prepared = parse_datetime(request.form.get("prepared_at"), datetime.utcnow())
            until = parse_datetime(request.form.get("available_until"))
            if quantity <= 0 or servings <= 0 or price < 0 or not until or until <= datetime.utcnow():
                raise ValueError
        except (ValueError, KeyError):
            flash("Check the quantity, servings, price, and future availability time.", "error")
            return render_template("food_form.html")
        image = None
        upload = request.files.get("image")
        if upload and upload.filename:
            filename = secure_filename(upload.filename)
            if "." not in filename or filename.rsplit(".", 1)[1].lower() not in ALLOWED_EXTENSIONS:
                flash("Use a JPG, PNG, or WebP image under 5 MB.", "error")
                return render_template("food_form.html")
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            image = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            upload.save(os.path.join(app.config["UPLOAD_FOLDER"], image))
        food = Food(donor_id=current_user().id, name=request.form["name"].strip(),
                    category=request.form["category"], quantity=quantity, unit=request.form.get("unit", "servings"),
                    servings=servings, food_type=request.form.get("food_type", "Vegetarian"), prepared_at=prepared,
                    available_until=until, storage=request.form["storage"], donation_type=request.form["donation_type"],
                    price=price, location=request.form["location"].strip(), image=image)
        db.session.add(food)
        db.session.add(FoodAnalytics(food=food, event_type="listed", servings=servings))
        db.session.commit()
        flash("Your food listing is live.", "success")
        return redirect(url_for("food_detail", food_id=food.id))
    return render_template("food_form.html")


@app.route("/food")
def food_list():
    query = Food.query.filter_by(status="Available")
    term = request.args.get("q", "").strip()
    category, location = request.args.get("category", ""), request.args.get("location", "").strip()
    food_type, donation = request.args.get("food_type", ""), request.args.get("donation_type", "")
    if term:
        query = query.filter(Food.name.ilike(f"%{term}%"))
    if category:
        query = query.filter_by(category=category)
    if location:
        query = query.filter(Food.location.ilike(f"%{location}%"))
    if food_type:
        query = query.filter_by(food_type=food_type)
    if donation:
        query = query.filter_by(donation_type=donation)
    foods = query.order_by(Food.available_until.asc()).all()
    priority = request.args.get("priority", "")
    if priority:
        foods = [food for food in foods if food.priority == priority]
    return render_template("food_list.html", foods=foods)


@app.route("/food/<int:food_id>")
def food_detail(food_id):
    food = db.get_or_404(Food, food_id)
    return render_template("food_detail.html", food=food)


@app.route("/request-food/<int:food_id>", methods=["POST"])
@roles_required("ngo", "consumer")
def request_food(food_id):
    food = db.get_or_404(Food, food_id)
    try:
        quantity = float(request.form.get("quantity", ""))
        pickup_at = parse_datetime(request.form.get("pickup_at"))
        if quantity <= 0 or quantity > food.quantity or not pickup_at or pickup_at > food.available_until:
            raise ValueError
    except ValueError:
        flash("Enter a valid quantity and pickup time before the listing expires.", "error")
        return redirect(url_for("food_detail", food_id=food.id))
    if food.donor_id == current_user().id:
        abort(403)
    item = FoodRequest(food_id=food.id, requester_id=current_user().id, requested_quantity=quantity, pickup_at=pickup_at)
    db.session.add(item)
    db.session.add(FoodAnalytics(food=food, event_type="requested", servings=int(quantity)))
    notify(food.donor_id, f"{current_user().name} requested {food.name}.", "request")
    db.session.commit()
    flash("Request sent to the donor.", "success")
    return redirect(url_for("requests"))


@app.route("/requests")
@login_required
def requests():
    user = current_user()
    query = FoodRequest.query.join(Food)
    if user.role == "donor":
        query = query.filter(Food.donor_id == user.id)
    elif user.role != "admin":
        query = query.filter(FoodRequest.requester_id == user.id)
    return render_template("requests.html", requests=query.order_by(FoodRequest.created_at.desc()).all())


def update_request_status(request_id, status):
    item = db.get_or_404(FoodRequest, request_id)
    user = current_user()
    if user.role != "admin" and item.food.donor_id != user.id:
        abort(403)
    if item.status != "Requested":
        flash("This request has already been updated.", "error")
        return redirect(url_for("requests"))
    if status == "Approved":
        try:
            approved = float(request.form.get("approved_quantity") or item.requested_quantity)
            pickup_at = parse_datetime(request.form.get("pickup_at"), item.pickup_at)
            if approved <= 0 or approved > item.food.quantity or pickup_at > item.food.available_until:
                raise ValueError
        except ValueError:
            flash("Approved quantity or pickup time is invalid.", "error")
            return redirect(url_for("requests"))
        item.approved_quantity, item.pickup_at, item.status = approved, pickup_at, "Approved"
        if item.pickup:
            item.pickup.pickup_at = pickup_at
            item.pickup.status = "Approved"
        else:
            db.session.add(Pickup(food_request=item, pickup_at=pickup_at))
        notify(item.requester_id, f"Your request for {item.food.name} was approved.", "approval")
    else:
        item.status = "Rejected"
        notify(item.requester_id, f"Your request for {item.food.name} was declined.", "rejection")
    db.session.commit()
    flash(f"Request {status.lower()}.", "success")
    return redirect(url_for("requests"))


@app.post("/approve-request/<int:request_id>")
@roles_required("donor", "admin")
def approve_request(request_id):
    return update_request_status(request_id, "Approved")


@app.post("/reject-request/<int:request_id>")
@roles_required("donor", "admin")
def reject_request(request_id):
    return update_request_status(request_id, "Rejected")


@app.route("/pickup/<int:request_id>", methods=["GET", "POST"])
@login_required
def pickup(request_id):
    item = db.get_or_404(FoodRequest, request_id)
    user = current_user()
    if user.role != "admin" and user.id not in (item.food.donor_id, item.requester_id):
        abort(403)
    if request.method == "POST":
        status = request.form.get("status")
        allowed = {"Approved": "Ready for Pickup", "Ready for Pickup": "Collected", "Collected": "Completed"}
        if status == "Cancelled" and item.status in {"Requested", "Approved"}:
            item.status = "Cancelled"
        elif allowed.get(item.status) == status and (user.role == "admin" or user.id == item.food.donor_id or status == "Cancelled"):
            item.status = status
            if item.pickup:
                item.pickup.status = status
            if status == "Completed":
                item.food.status = "Collected"
                db.session.add(FoodAnalytics(food_id=item.food_id, event_type="completed", servings=int(item.approved_quantity or item.requested_quantity)))
            elif status == "Collected":
                db.session.add(FoodAnalytics(food_id=item.food_id, event_type="collected", servings=int(item.approved_quantity or item.requested_quantity)))
            notify(item.requester_id, f"Pickup update for {item.food.name}: {status}.", "pickup")
        else:
            flash("That pickup status change is not allowed.", "error")
        db.session.commit()
        return redirect(url_for("pickup", request_id=item.id))
    return render_template("pickup.html", item=item)


@app.route("/emergency-request", methods=["GET", "POST"])
@roles_required("ngo")
def emergency_request():
    if not current_user().verified:
        flash("Only verified NGOs can publish emergency requests. Contact an administrator for verification.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        required_at = parse_datetime(request.form.get("required_at"))
        if not all(request.form.get(key, "").strip() for key in ("food_type", "quantity", "location", "urgency", "contact")) or not required_at:
            flash("Complete all emergency request fields.", "error")
        else:
            item = EmergencyRequest(ngo_id=current_user().id, food_type=request.form["food_type"].strip(),
                                    quantity=request.form["quantity"].strip(), location=request.form["location"].strip(),
                                    required_at=required_at, urgency=request.form["urgency"], contact=request.form["contact"].strip())
            db.session.add(item)
            for donor in User.query.filter_by(role="donor").all():
                notify(donor.id, f"Urgent food request near {item.location}.", "emergency")
            db.session.commit()
            flash("Emergency request shared with FoodLink donors.", "success")
            return redirect(url_for("emergency_request"))
    emergencies = EmergencyRequest.query.filter_by(status="Open").order_by(EmergencyRequest.required_at.asc()).all()
    return render_template("emergency.html", emergencies=emergencies)


@app.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()
    for item in items:
        item.read = True
    db.session.commit()
    return render_template("notifications.html", notifications=items)


@app.route("/analytics")
@login_required
def analytics():
    foods = Food.query.all()
    categories = [
        [category, count]
        for category, count in db.session.query(
            Food.category, db.func.count(Food.id)
        ).group_by(Food.category).all()
    ]
    month_values = [0] * 12
    monthly = db.session.query(
        db.extract("month", Food.created_at), db.func.sum(Food.servings)
    ).filter(
        db.extract("year", Food.created_at) == datetime.utcnow().year
    ).group_by(db.extract("month", Food.created_at)).all()
    for month, servings in monthly:
        month_values[int(month) - 1] = int(servings or 0)
    return render_template("analytics.html", total=len(foods), listed=sum(f.servings for f in foods),
                           collected=sum(f.servings for f in foods if f.status == "Collected"),
                           categories=categories, monthly=month_values,
                           completed=FoodRequest.query.filter_by(status="Completed").count())


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name, mobile, address = (request.form.get(key, "").strip() for key in ("name", "mobile", "address"))
        if name and mobile and address:
            user.name, user.mobile, user.address = name, mobile, address
            db.session.commit()
            flash("Profile updated.", "success")
        else:
            flash("Name, mobile number, and address are required.", "error")
    return render_template("profile.html", user=user)


@app.route("/admin")
@roles_required("admin")
def admin():
    return render_template("admin.html", users=User.query.order_by(User.created_at.desc()).limit(10).all(),
                           counts={"users": User.query.count(), "donors": User.query.filter_by(role="donor").count(),
                                   "ngos": User.query.filter_by(role="ngo").count(), "consumers": User.query.filter_by(role="consumer").count(),
                                   "foods": Food.query.count(), "pending": FoodRequest.query.filter_by(status="Requested").count(),
                                   "completed": FoodRequest.query.filter_by(status="Completed").count(),
                                   "emergencies": EmergencyRequest.query.filter_by(status="Open").count(),
                                   "saved": sum(f.servings for f in Food.query.all() if f.status == "Collected")})


@app.post("/admin/verify-ngo/<int:user_id>")
@roles_required("admin")
def verify_ngo(user_id):
    user = db.get_or_404(User, user_id)
    if user.role == "ngo":
        user.verified = True
        notify(user.id, "Your NGO account has been verified.", "account")
        db.session.commit()
        flash(f"{user.name} is now verified.", "success")
    return redirect(url_for("admin"))


@app.get("/api/food")
def api_food():
    items = Food.query.filter_by(status="Available").order_by(Food.available_until.asc()).all()
    return jsonify([{"id": f.id, "name": f.name, "category": f.category, "quantity": f.quantity,
                    "servings": f.servings, "location": f.location, "priority": f.priority,
                    "available_until": f.available_until.isoformat(), "donation_type": f.donation_type,
                    "price": f.price} for f in items])


def seed_demo():
    if User.query.first():
        return
    donor = User(name="Green Table Kitchen", email="donor@foodlink.demo", mobile="+1 415 555 0134",
                 password_hash=generate_password_hash("FoodLink123!"), address="18 Market Street, San Francisco", role="donor")
    ngo = User(name="Community Pantry", email="ngo@foodlink.demo", mobile="+1 415 555 0198",
               password_hash=generate_password_hash("FoodLink123!"), address="42 Mission Street, San Francisco", role="ngo", verified=True)
    consumer = User(name="Alex Morgan", email="consumer@foodlink.demo", mobile="+1 415 555 0120",
                    password_hash=generate_password_hash("FoodLink123!"), address="San Francisco", role="consumer")
    admin_user = User(name="FoodLink Admin", email="admin@foodlink.demo", mobile="+1 415 555 0100",
                      password_hash=generate_password_hash("FoodLink123!"), address="FoodLink HQ", role="admin", verified=True)
    db.session.add_all([donor, ngo, consumer, admin_user])
    db.session.flush()
    now = datetime.utcnow()
    samples = [
        Food(donor_id=donor.id, name="Harvest grain bowls", category="Prepared meals", quantity=18, unit="meals", servings=18,
             food_type="Vegetarian", prepared_at=now - timedelta(hours=2), available_until=now + timedelta(hours=5),
             storage="Refrigerated", donation_type="Free", price=0, location="18 Market Street, San Francisco"),
        Food(donor_id=donor.id, name="Seasonal produce boxes", category="Produce", quantity=12, unit="boxes", servings=36,
             food_type="Vegan", prepared_at=now - timedelta(hours=1), available_until=now + timedelta(hours=20),
             storage="Cool storage", donation_type="Free", price=0, location="18 Market Street, San Francisco"),
        Food(donor_id=donor.id, name="Fresh sourdough loaves", category="Bakery", quantity=10, unit="loaves", servings=20,
             food_type="Vegetarian", prepared_at=now - timedelta(hours=3), available_until=now + timedelta(hours=10),
             storage="Room temperature", donation_type="Discounted", price=2.5, location="18 Market Street, San Francisco"),
    ]
    db.session.add_all(samples)
    db.session.commit()


with app.app_context():
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db.create_all()
    if os.getenv("SEED_DEMO", "true").lower() == "true":
        seed_demo()


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You don't have permission to view this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="We couldn't find that FoodLink page."), 404


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")
