from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Koyeb!"

@app.route("/")
def welcome():
    greetings = """
    <html>
    <body>
    <h1>gretings!</h1>
    <p>hello word</P>
    </body>
    </html>
    """
    return greetings

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
