import os 
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    ) 

# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM schemes")
    all_schemes = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        schemes=all_schemes
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (name, email, password)
            )

            db.commit()

        except mysql.connector.IntegrityError:

            cursor.close()
            db.close()

            return "Email already registered."

        cursor.close()
        db.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM users
            WHERE email = %s AND password = %s
            """,
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:
            return redirect(url_for("profile"))

        return "Invalid email or password."

    return render_template("login.html")


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    return render_template("profile.html")


# =========================================================
# AI ELIGIBILITY ENGINE
# =========================================================

@app.route("/check-eligibility", methods=["POST"])
def check_eligibility():

    # -----------------------------------------------------
    # USER INPUT
    # -----------------------------------------------------

    try:
        age = int(request.form["age"])
        income = float(request.form["income"])
    except (ValueError, TypeError):

        return "Invalid age or income.", 400

    occupation = request.form["occupation"]
    category = request.form["category"]
    state = request.form["state"]


    # -----------------------------------------------------
    # GET SCHEMES
    # -----------------------------------------------------

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM schemes")

    schemes = cursor.fetchall()

    cursor.close()
    db.close()


    # -----------------------------------------------------
    # AI MATCHING
    # -----------------------------------------------------

    recommendations = []

    for scheme in schemes:

        score = 0

        matched_conditions = []
        reasons = []
        missing_conditions = []


        # =================================================
        # 1. AGE MATCH
        # =================================================

        min_age = scheme["min_age"]
        max_age = scheme["max_age"]

        if min_age <= age <= max_age:

            score += 20

            matched_conditions.append("Age requirement matched")

            reasons.append(
                f"Your age ({age}) matches the scheme age criteria."
            )

        else:

            missing_conditions.append("Age requirement not matched")


        # =================================================
        # 2. INCOME MATCH
        # =================================================

        try:
            max_income = float(scheme["max_income"])
        except (ValueError, TypeError):

            max_income = 999999999


        if income <= max_income:

            score += 20

            matched_conditions.append("Income requirement matched")

            reasons.append(
                "Your annual family income is within the scheme limit."
            )

        else:

            missing_conditions.append(
                "Income is above the scheme limit"
            )


        # =================================================
        # 3. OCCUPATION MATCH
        # =================================================

        scheme_occupation = scheme["occupation"]

        if (
            scheme_occupation == "All"
            or scheme_occupation == occupation
        ):

            score += 20

            matched_conditions.append(
                "Occupation requirement matched"
            )

            reasons.append(
                f"Your occupation ({occupation}) matches the scheme."
            )

        else:

            missing_conditions.append(
                "Occupation requirement not matched"
            )


        # =================================================
        # 4. CATEGORY MATCH
        # =================================================

        scheme_category = scheme["category_required"]

        if (
            scheme_category == "All"
            or scheme_category == category
        ):

            score += 20

            matched_conditions.append(
                "Social category requirement matched"
            )

            reasons.append(
                "Your social category matches the scheme requirement."
            )

        else:

            missing_conditions.append(
                "Social category requirement not matched"
            )


        # =================================================
        # 5. STATE MATCH
        # =================================================

        scheme_state = scheme["state"]

        if (
            scheme_state == "All"
            or scheme_state == state
        ):

            score += 20

            matched_conditions.append(
                "State requirement matched"
            )

            reasons.append(
                f"The scheme is available for {state}."
            )

        else:

            missing_conditions.append(
                "State requirement not matched"
            )


        # =================================================
        # RECOMMENDATION LEVEL
        # =================================================

        if score >= 80:

            recommendation = "Highly Recommended"

        elif score >= 60:

            recommendation = "Good Match"

        elif score >= 40:

            recommendation = "Possible Match"

        else:

            recommendation = "Low Match"


        # =================================================
        # WHY RECOMMENDED
        # =================================================

        if score >= 80:

            recommendation_reason = (
                "Most of your eligibility conditions match "
                "this scheme."
            )

        elif score >= 60:

            recommendation_reason = (
                "Several important eligibility conditions "
                "match your profile."
            )

        elif score >= 40:

            recommendation_reason = (
                "Some eligibility conditions match, but "
                "additional requirements may need verification."
            )

        else:

            recommendation_reason = (
                "Your current profile has limited matching "
                "conditions for this scheme."
            )


        # =================================================
        # DOCUMENT READINESS
        # =================================================

        documents = scheme.get("documents")

        if documents:

            document_readiness = "Documents information available"

        else:

            document_readiness = "Document information not available"


        # =================================================
        # BENEFITS
        # =================================================

        benefits = scheme.get("benefits")

        if benefits:

            benefit_preview = benefits

        else:

            benefit_preview = (
                "Benefit information will be available "
                "on the official government portal."
            )


        # =================================================
        # OFFICIAL PORTAL
        # =================================================

        official_link = scheme.get("apply_link")

        if not official_link:

            official_link = "https://www.myscheme.gov.in/"


        # =================================================
        # FINAL RESULT
        # =================================================

        scheme["match_score"] = score

        scheme["matched_conditions"] = matched_conditions

        scheme["reasons"] = reasons

        scheme["missing_conditions"] = missing_conditions

        scheme["recommendation"] = recommendation

        scheme["recommendation_reason"] = recommendation_reason

        scheme["document_readiness"] = document_readiness

        scheme["benefit_preview"] = benefit_preview

        scheme["official_link"] = official_link


        # =================================================
        # ONLY SHOW USEFUL MATCHES
        # =================================================

        if score >= 40:

            recommendations.append(scheme)


    # =====================================================
    # SORT BY AI MATCH SCORE
    # =====================================================

    recommendations.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )


    # =====================================================
    # USER PROFILE DATA
    # =====================================================

    user_profile = {
        "age": age,
        "income": income,
        "occupation": occupation,
        "category": category,
        "state": state
    }


    # =====================================================
    # RESULTS PAGE
    # =====================================================

    return render_template(
        "results.html",
        schemes=recommendations,
        user_profile=user_profile
    )


# =========================================================
# ALL SCHEMES
# =========================================================

@app.route("/schemes")
def schemes():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM schemes")

    all_schemes = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "scheme.html",
        schemes=all_schemes
    )


# =========================================================
# SCHEME DETAILS
# =========================================================

@app.route("/scheme/<int:scheme_id>")
def scheme_details(scheme_id):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM schemes WHERE id = %s",
        (scheme_id,)
    )

    scheme = cursor.fetchone()

    cursor.close()
    db.close()

    if not scheme:

        return "Scheme not found", 404


    # -----------------------------------------------------
    # OFFICIAL LINK
    # -----------------------------------------------------

    official_link = scheme["apply_link"]

    if not official_link:

        official_link = "https://www.myscheme.gov.in/"


    return render_template(
        "scheme_details.html",
        scheme=scheme,
        official_link=official_link
    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(debug=True) 