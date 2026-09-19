import json
import os
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token

app = Flask(__name__)

# In production set a long random value in the SECRET_KEY environment variable.
# Anyone who knows this key can forge a login session, so never rely on the
# fallback once the site is public.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7 days

# Must match the projectId in your Firebase web config.
FIREBASE_PROJECT_ID = "sceamsatthi"
_http_request = g_requests.Request()

with open("data/schemes.json", "r", encoding="utf-8") as file:
    schemes = json.load(file)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def safe_next(target, default="/eligibility"):
    """Only allow same-site relative paths, so /login?next= can't redirect
    people to another website."""
    if (
        not target
        or not target.startswith("/")
        or target.startswith("//")
        or "\\" in target
    ):
        return default
    return target


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login")
def login():
    next_url = safe_next(request.args.get("next"))
    if "user" in session:
        return redirect(next_url)
    return render_template("login.html", next=next_url)


@app.route("/session-login", methods=["POST"])
def session_login():
    """The browser signs in with Firebase, then sends us the ID token.
    We verify it here before trusting it."""
    data = request.get_json(silent=True) or {}
    token = data.get("idToken")
    if not token:
        return jsonify(error="Missing sign-in token. Please try again."), 400

    try:
        claims = id_token.verify_firebase_token(
            token,
            _http_request,
            audience=FIREBASE_PROJECT_ID,
            clock_skew_in_seconds=10,
        )
    except Exception as exc:  # invalid, expired, wrong project, certs unreachable
        app.logger.warning("Firebase token verification failed: %s", exc)
        claims = None

    expected_issuer = f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
    if not claims or claims.get("iss") != expected_issuer:
        return jsonify(error="We couldn't verify your sign-in. Please try again."), 401

    uid = claims.get("user_id") or claims.get("sub")

    # A different person signing in on this browser shouldn't inherit the
    # previous person's saved eligibility answers.
    previous = session.get("user")
    if previous and previous.get("uid") != uid:
        session.pop("profile", None)

    session["user"] = {"uid": uid, "email": claims.get("email")}
    session.permanent = True

    return jsonify(ok=True, next=safe_next(data.get("next")))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------------------------------------------------------------------
# App routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    profile = session.get("profile")

    return render_template(
        "index.html",
        profile=profile
    )


@app.route("/eligibility", methods=["GET", "POST"])
@login_required
def eligibility():
    if request.method == "POST":
        profile = {
            "age": int(request.form["age"]),
            "gender": request.form["gender"],
            "state": request.form["state"],
            "income": request.form["income"],
            "occupation": request.form["occupation"],
            "category": request.form["category"]
        }

        session["profile"] = profile

        return redirect("/my-schemes")

    return render_template("eligibility.html")


@app.route("/my-schemes")
@login_required
def my_schemes():
    if "profile" not in session:
        return redirect("/eligibility")

    profile = session["profile"]

    age = profile["age"]
    state = profile["state"]
    income = profile["income"]
    occupation = profile["occupation"]
    category = profile["category"]

    income_limits = {
        "1": 100000,
        "2": 300000,
        "3": 500000,
        "4": 1000000,
        "5": float("inf")
    }

    user_income = income_limits[income]

    matched_schemes = []

    for scheme in schemes:
        if age < scheme["min_age"] or age > scheme["max_age"]:
            continue

        if "all" not in scheme["states"] and state not in scheme["states"]:
            continue

        if user_income > scheme["max_income"]:
            continue

        if occupation not in scheme["occupations"]:
            continue

        if category not in scheme["social_categories"]:
            continue

        reasons = []

        reasons.append(
            f"Age {age} is within the required range "
            f"({scheme['min_age']}-{scheme['max_age']})"
        )

        if "all" in scheme["states"]:
            reasons.append("Available across all states")
        else:
            reasons.append(f"State requirement: {state.title()}")

        reasons.append("Income is within the scheme's limit")

        reasons.append(
            f"Current status: {occupation.replace('_', ' ').title()}"
        )

        reasons.append(f"Category: {category.upper()}")

        matched_schemes.append({
            "name": scheme["name"],
            "category": scheme["category"],
            "description": scheme["description"],
            "documents": scheme["documents"],
            "official_link": scheme["official_link"],
            "reasons": reasons
        })

    return render_template(
        "results.html",
        schemes=matched_schemes
    )


if __name__ == "__main__":
    app.run(debug=True)
