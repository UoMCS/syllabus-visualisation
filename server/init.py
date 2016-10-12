#!/bin/python2
from getpass import getpass

from flask_bcrypt import Bcrypt

from app import app

from init_app import init_app

import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists, create_database

def get_database_info(driver):
        print "Database address (empty for localhost):",
        address = raw_input()
        if address == "":
            address = "localhost"

        print "Database username (empty for root):",
        username = raw_input()
        if username == "":
            username = "root"

        password = getpass("Database password: ")
        while password == "":
            password = getpass("Please enter a password: ")

        print "Database name (empty for syllabus):",
        name = raw_input()
        if name == "":
            name = "syllabus"

        return driver + "://" + username + ":" + password + "@" + address + "/" + name


print "Choose database engine:"
print "1 - MySQL"
print "2 - Oracle"
print "3 - Postgresql"
print "4 - SQLite"
print "5 - Custom"

while True:
    ans = raw_input("> ")
    if ans == "1":
        database = get_database_info("mysql")
        break
    elif ans == "2":
        database = get_database_info("oracle")
        break
    elif ans == "2":
        database = get_database_info("postgresql")
        break
    elif ans == "4":
        print "Database path (empty for syllabus):",
        path = raw_input()
        if path == "":
            path = "syllabus"
        database = "sqlite:///" + path + ".db"
        break
    elif ans == "5":
        print "Enter database connection string",
        database = raw_input()
        break
    else:
        print "invalid selection"

engine = sqlalchemy.create_engine(database)

if not database_exists(engine.url):
    confirm = raw_input("Database does not exist, okay to create [Y/n] ")
    if confirm != "" and (confirm[0] == 'n' or confirm[0] == 'N'):
        print "Exiting, no changes have been made."
        exit()
    create_database(engine.url)

try:
    connection = engine.connect()
except sqlalchemy.exc.OperationalError, e:
    print e
    exit()
connection.close()

config = open("server/server.cfg", "w")
config.write("SQLALCHEMY_DATABASE_URI = \"" + database + "\"\n")
config.write("GRAPH_STYLE_PATH = \"./graph_style.json\"\n")
config.close()

print "Config file written to server.cfg"

init_app(app, "example.cfg")
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# important, import after getting the db
from models import *

print "Creating database..."
db.create_all()
db.session.commit()


print "Admin username (empty for admin):",
username = raw_input()
if username == "":
    username = "admin"

password = getpass("Admin password: ")
while password == "":
    password = getpass("Please enter a password: ")


inst = Institution(name="admin",uri="admin")
db.session.add(inst)
# need to commit now for relationships to work
db.session.commit()

dept = Department(name="admin",uri="admin",institution=inst.id)
db.session.add(dept)
db.session.commit()

user = User(username=username, password=bcrypt.generate_password_hash(password), department=dept.id)
db.session.add(user)
db.session.commit()

print "All done."
