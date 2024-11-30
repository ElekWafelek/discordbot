from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Discord bot ok"

def run():
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
