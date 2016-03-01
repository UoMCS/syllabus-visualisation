#! /usr/bin/env python
import sys
from server import init_app

app = init_app(sys.argv[1])

with app.app_context():
    app.run(debug=True)
