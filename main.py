import flask

app=flask.Flask(__name__)

@app.route('/',methods=['GET'])
def hello():
    return "HELLO WORLD"
if __name__=='__main__':
    app.run(debug=True)