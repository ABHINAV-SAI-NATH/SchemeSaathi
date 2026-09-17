from flask import Flask, render_template, request
import json

app = Flask(__name__)

with open("data/schemes.json", "r", encoding="utf-8") as file:
    schemes = json.load(file)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/eligibility", methods=["GET", "POST"])
def eligibility():

    if request.method == "POST":

        age = int(request.form["age"])
        gender = request.form["gender"]
        state = request.form["state"]
        income = request.form["income"]
        occupation = request.form["occupation"]
        category = request.form["category"]

        # Convert income selection into an approximate upper limit
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

            # Age check
            if age < scheme["min_age"] or age > scheme["max_age"]:
                continue

            # State check
            if "all" not in scheme["states"] and state not in scheme["states"]:
                continue

            # Income check
            if user_income > scheme["max_income"]:
                continue

            # Occupation check
            if occupation not in scheme["occupations"]:
                continue

            # Social category check
            if category not in scheme["social_categories"]:
                continue

            matched_schemes.append(scheme)

        return render_template(
            "results.html",
            schemes=matched_schemes
        )

    return render_template("eligibility.html")

if __name__ == "__main__":
    app.run(debug=True)