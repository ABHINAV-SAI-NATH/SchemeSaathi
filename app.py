from flask import Flask, render_template, request, session, redirect
import json

app = Flask(__name__)

app.secret_key = "hackathon-secret-key"

with open("data/schemes.json", "r", encoding="utf-8") as file:
    schemes = json.load(file)


@app.route("/")
def home():

    profile = session.get("profile")

    return render_template(
        "index.html",
        profile=profile
    )


@app.route("/eligibility", methods=["GET", "POST"])
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