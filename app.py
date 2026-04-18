import json
import os
import re
import unicodedata
import functools
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
with open(DATA_FILE, encoding="utf-8") as f:
    ALL_DATA = json.load(f)

APP_PASSWORD = os.environ.get("APP_PASSWORD", "oml2026")


def normalize(text):
    # 全角→半角、大文字→小文字
    text = unicodedata.normalize("NFKC", text).lower()
    # カタカナ→ひらがな
    result = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(ch)
    return "".join(result)


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            session.permanent = True
            return redirect(request.args.get("next") or url_for("index"))
        error = "パスワードが違います"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "all")
    keywords = [normalize(k) for k in q.split() if k]

    results = []
    for item in ALL_DATA:
        if category != "all" and item.get("category", "") != category:
            continue
        if keywords:
            haystack = normalize(" ".join([
                item.get("date", ""),
                item.get("no", ""),
                item.get("title", ""),
                item.get("summary", ""),
                item.get("keywords", ""),
                item.get("category", ""),
            ]))
            if not all(k in haystack for k in keywords):
                continue
        results.append(item)

    return jsonify({"total": len(results), "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
