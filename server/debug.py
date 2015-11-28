#! /usr/bin/env python
from server import app

with app.app_context():
    app.run(debug=True)
