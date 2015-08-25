from logging import FileHandler

from app import app
from api import api

app.config.from_pyfile('../server.cfg')

api_prefix = None

if app.debug:
    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    api_prefix = '/api'
else: # Production
    file_handler = FileHandler(app.config['LOG_FILE'])
    app.logger.addHandler(file_handler)

app.register_blueprint(api, url_prefix=api_prefix)
