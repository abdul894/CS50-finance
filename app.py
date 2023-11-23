import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # query database to fetch logedin user data.
    stocks = db.execute(
        "SELECT stock_symbol,SUM(no_of_stocks) AS totalshares,price FROM buyers WHERE user_id = ? GROUP BY stock_symbol",
        session["user_id"],
    )

    value = 0
    for stock in stocks:
        value += stock["totalshares"] * stock["price"]

    avail_cash_dict = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"]
    )
    avail_cash = avail_cash_dict[0]["cash"]

    net_worth = value + avail_cash

    return render_template(
        "index.html", stocks=stocks, avail_cash=avail_cash, net_worth=net_worth, usd=usd
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # Check if the request method is POST, indicating a form submission
    if request.method == "POST":
        # Check if the submitted symbol is valid and exists
        if not request.form.get("symbol") or not lookup(request.form.get("symbol")):
            return apology("Invalid symbol")

        # Check if the number of shares is valid
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Invalid no of shares!")

        if shares <= 0:
            return apology("Invalid no of shares!")

        # Get stock details and current price from the API
        dets_stock = lookup(request.form.get("symbol"))
        curt_price = dets_stock.get("price")

        # Get the user's available cash from the database
        row = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        avail_cash = row[0]["cash"]

        # Calculate the total value of the purchase
        value = curt_price * shares

        # Check if the user has enough cash for the purchase
        if value > avail_cash:
            return apology("Not enough cash for this purchase!")

        # If the user has enough cash, proceed with the purchase
        elif value <= avail_cash:
            pur_cost = shares * curt_price
            bal = avail_cash - pur_cost
            db.execute(
                "INSERT INTO buyers(user_id,stock_symbol, price, no_of_stocks, amount, type) VALUES(?, ?, ?, ?, ?, ?)",
                session["user_id"],
                request.form.get("symbol"),
                curt_price,
                shares,
                pur_cost,
                "Buy",
            )
            db.execute(
                "UPDATE users SET cash = ? WHERE id = ?", bal, session["user_id"]
            )

        # Redirect the user back to the homepage
        return redirect("/")
    else:
        # If the request method is GET, simply render the buy.html template
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute(
        "SELECT stock_symbol, no_of_stocks, type, price, time FROM buyers WHERE user_id = ?",
        session["user_id"],
    )
    return render_template("history.html", transactions=transactions, usd=usd)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quoted = lookup(symbol)

        # If user input wrong symbol, return apology message
        if quoted == None:
            return apology("Incorrect symbol!")

        # Returning share details!
        return render_template("quoted.html", quoted=quoted)

    # If user visited via GET method
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # checking the user's request
    if request.method == "POST":
        # checking the username field is not empty
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # checking the password field is not empty
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # checking the re-typed password is correct
        password = request.form.get("password")
        conf_password = request.form.get("confirmation")
        if not conf_password == password:
            return apology("confirmed password should be same as password")

        # hashing the users password
        hashed = generate_password_hash(password)

        # Inserting the users info into the database
        try:
            user_info = request.form.get("username")
            db.execute(
                "INSERT INTO users(username,hash) VALUEs(?,?)", user_info, hashed
            )
        except:
            return apology("User name already exists!")

        # Remember the usrs credentials
        session["user_id"] = db.execute(
            "SELECT id FROM users WHERE username = ?", user_info
        )

        # redirecting the user to main page
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("shares") or not int(request.form.get("shares")) > 0:
            return apology("Invalid no of Shares!")

        symbol = request.form.get("symbol")
        shares_owned = db.execute(
            "SELECT no_of_stocks FROM buyers WHERE user_id = ? AND stock_symbol = ? GROUP BY stock_symbol",
            session["user_id"],
            symbol,
        )[0]["no_of_stocks"]
        shares = int(request.form.get("shares"))

        if shares_owned < shares:
            return apology("Invalid share quantity!")

        price = lookup(symbol)["price"]
        sell_value = price * shares

        current_cash = db.execute(
            "SELECT cash FROM users WHERE id = ?", session["user_id"]
        )[0]["cash"]
        cash_bal = current_cash + sell_value
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?", cash_bal, session["user_id"]
        )
        db.execute(
            "INSERT INTO buyers(user_id, stock_symbol, price, no_of_stocks, amount, type) VALUES(?, ?, ?, ?, ?, ?)",
            session["user_id"],
            symbol,
            price,
            -shares,
            sell_value,
            "Sell",
        )
        return redirect("/")
    else:
        stocks_owned = db.execute(
            "SELECT stock_symbol FROM buyers WHERE user_id = ? GROUP BY stock_symbol",
            session["user_id"],
        )
        return render_template("sell.html", stocks_owned=stocks_owned)
