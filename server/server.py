from logging import FileHandler

from app import app
from api import api
from models import db
import os
from flask import request 

app.config.from_pyfile('../server.cfg')

@app.route("/edit_graph_style", methods=['GET','POST'])
def edit_graph_style():
    filename = os.path.dirname(os.path.abspath(__file__)) + "/graph_style.json"

    if request.method == 'POST':
        with open(filename, 'w') as f:
            f.write(request.form['text'])

    with open(filename) as f:
        return """
               <form method="POST">
               <textarea name="text" style="width: 800; height: 600">{0}</textarea>
               <br/>
               <input type="submit" value="Save"/>
               </form>
               """.format(f.read())

api_prefix = None

if app.debug:
    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    api_prefix = '/api'
else: # Production
    file_handler = FileHandler(app.config['LOG_FILE'])
    app.logger.addHandler(file_handler)

app.register_blueprint(api, url_prefix=api_prefix)

