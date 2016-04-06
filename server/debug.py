#! /usr/bin/env python
import sys
from app import app
from init_app import init_app

init_app(app, sys.argv[1])

with app.app_context():
    app.run(debug=True)
