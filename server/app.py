from flask import Flask

app = Flask(__name__, static_folder='../client', static_url_path='')

