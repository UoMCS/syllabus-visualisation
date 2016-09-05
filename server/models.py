from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import ClauseElement
from app import app


def get_db():
    db = getattr(app, '_database', None)
    if db is None:
        db = app._database = SQLAlchemy(app)
    return db

# to use with many-many association tables
db = get_db()

# Checks if the model with given parameters exists. Returns an existing one if
# it does, creates one and returns it if it doesn't
#
# Original: http://stackoverflow.com/a/2587041
def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        return instance, True

class Unit(get_db().Model):
    db = get_db()
    __tablename__ = "unit"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20))
    name = db.Column(db.Text)
    level = db.Column(db.Integer)

    department_id = db.Column('department', db.Integer, db.ForeignKey('department.id'))

    unit_topics = db.relationship("UnitTopic", backref="unit", cascade="all, delete-orphan")

    def __init__(self, code, name, level, department_id):
        self.code = code
        self.name = name
        self.level = level
        self.department_id = department_id

    def __repr__(self):
        return "<Unit %r %r %r>" % (self.code, self.name, self.level)


unit_topic_context = db.Table('unit_topic_context', db.Model.metadata,
    db.Column('unit_topic_id', db.Integer, db.ForeignKey('unit_topic.id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
)

class UnitTopic(get_db().Model):
    db = get_db()
    __tablename__ = "unit_topic"

    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))

    alias = db.Column(db.Text)
    is_taught = db.Column(db.Boolean)
    is_assessed = db.Column(db.Boolean)
    is_applied = db.Column(db.Boolean)

    contexts = db.relationship("Topic", secondary=unit_topic_context, back_populates="contexts")

    def __init__(self, unit_id, topic_id):
        self.unit_id = unit_id
        self.topic_id = topic_id

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<UnitTopic %r %r>' % (self.unit_id, self.topic_id)


# topic - category association table
topic_category = db.Table('topic_category', db.Model.metadata,
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

class Topic(get_db().Model):
    db = get_db()
    __tablename__ = 'topic'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    type = db.Column(db.String(20))

    unit_topics = db.relationship("UnitTopic", backref="topic", cascade="all, delete-orphan")
    custom_topics = db.relationship("CustomTopic", backref="topic", lazy="dynamic", cascade="all, delete-orphan")

    categories = db.relationship("Category", secondary=topic_category, back_populates="topics")
    contexts = db.relationship("UnitTopic", secondary=unit_topic_context, back_populates="contexts")

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Topic %r>' % self.name


class Category(get_db().Model):
    db = get_db()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)

    topics = db.relationship("Topic", secondary="topic_category", back_populates="categories")

    def __init__(self, name):
        self.name = name



# custom_topic - Keyword association table
custom_topic_keyword = db.Table('custom_topic_keyword', db.Model.metadata,
    db.Column('custom_topic_id', db.Integer, db.ForeignKey('custom_topic.id')),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id'))
)

class CustomTopic(Topic):
    db = get_db()
    __tablename__ = 'custom_topic'

    id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)
    description = db.Column(db.Text)

    keywords = db.relationship("Keyword", secondary=custom_topic_keyword, back_populates="custom_topics")

    def __repr__(self):
        return '<CustomTopic %r>' % self.name

class Keyword(get_db().Model):
    db = get_db()
    __tablename__ = 'keyword'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)

    custom_topics = db.relationship("CustomTopic", secondary="custom_topic_keyword", back_populates="keywords")


class User(get_db().Model):
    db = get_db()
    __tablename__ = "users"

    id = db.Column('id', db.Integer, primary_key=True)
    username = db.Column('username', db.String(45), unique=True)
    password = db.Column('password', db.String(60))
    department_id = db.Column('Department', db.Integer, db.ForeignKey('department.id'))

    def __init__(self, username, password, department):
        self.username = username
        self.password = password
        self.department_id = department

    def is_active(self):
        return True

    def get_id(self):
        return unicode(self.id)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False


class Department(get_db().Model):
    db = get_db()
    __tablename__ = "department"

    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.Text)
    uri = db.Column('uri', db.String(45))
    institution_id = db.Column('institution', db.Integer, db.ForeignKey('institution.id'))

    users = db.relationship(User, backref="department", lazy='dynamic', cascade="all, delete-orphan")
    units = db.relationship(Unit, backref="department", lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, name, uri, institution):
        self.name = name
        self.uri = uri
        self.institution_id = institution



class Institution(get_db().Model):
    db = get_db()
    __tablename__ = "institution"

    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.Text)
    uri = db.Column('uri', db.String(45), unique=True)

    departments = db.relationship(Department, backref="institution", lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, name, uri):
        self.name = name
        self.uri = uri
