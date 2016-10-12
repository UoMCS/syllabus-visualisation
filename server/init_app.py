from api import api

def init_app(app, config):
    app.config.from_pyfile(config)
    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    app.register_blueprint(api, url_prefix='/api')
    app.secret_key = "super secret"
