from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import ClauseElement
from app import app
from sqlalchemy import event
from sqlalchemy.orm import Session

db = SQLAlchemy(app)

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

unit_topic_context = db.Table('unit_topic_context', db.Model.metadata,
    db.Column('unit_topic_id', db.Integer, db.ForeignKey('unit_topic.id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'))
)

class UnitTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    unit = db.relationship('Unit', backref='unit_topics')

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))

    alias = db.Column(db.Text)

    is_taught = db.Column(db.Boolean)
    is_assessed = db.Column(db.Boolean)
    is_applied = db.Column(db.Boolean)

    contexts = db.relationship("Topic", secondary=unit_topic_context)

    def __init__(self, unit_id, topic_id):
        self.unit_id = unit_id
        self.topic_id = topic_id

    def __str__(self):
        return self.__repr__() 

    def __repr__(self):
        return '<UnitTopic %r %r>' % (self.unit_id, self.topic_id)

# Adapted from http://stackoverflow.com/a/9264556
@event.listens_for(Session, 'after_flush')
def delete_topic_orphans(session, ctx):
    session.query(Topic).\
        filter(~Topic.unit_topics.any()).\
        delete(synchronize_session=False)

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.Text, unique=True)
    name = db.Column(db.Text)

    def __init__(self, code, name):
        self.code = code
        self.name = name

    def __repr__(self):
        return "<Unit %r %r>" % (self.code, self.name)

topic_category = db.Table('topic_category', db.Model.metadata,
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Text, unique=True)

    unit_topics = db.relationship(UnitTopic, backref=db.backref('topic'))

    categories = db.relationship("Category", secondary=topic_category)

    type = db.Column(db.String(20))

    __mapper_args__ = {
        'polymorphic_identity': 'topic',
        'polymorphic_on': type
    }

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Topic %r>' % self.name

custom_topic_keyword = db.Table('custom_topic_keyword', db.Model.metadata,
    db.Column('custom_topic_id', db.Integer, db.ForeignKey('custom_topic.id')),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id'))
)

class CustomTopic(Topic):
    id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)

    description = db.Column(db.Text)

    keywords = db.relationship("Keyword", secondary=custom_topic_keyword)

    __mapper_args__ = {
        'polymorphic_identity': 'custom_topic',
    }

    def __repr__(self):
        return '<CustomTopic %r>' % self.name

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)

    def __init__(self, name):
        self.name = name

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)
