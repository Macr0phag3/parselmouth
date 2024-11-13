from flask import Flask, request, Response
import random
import re

app = Flask(__name__)


@app.route("/")
def index():
    evalme = request.args.get("evalme")

    if (not evalme) or re.search(r"[A-Zd-z\\. /*$#@!+^]", evalme):
        return "hacker?"

    with open(eval(evalme), "rb") as f:
        return Response(f.read())


if __name__ == "__main__":
    app.run(port=8080)
