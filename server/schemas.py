from __future__ import print_function
from marshmallow import fields
from flask_marshmallow import Marshmallow

from app import app
from models import *

ma = Marshmallow(app)

class TopicSchema(ma.ModelSchema):
    class Meta:
        model = Topic
        exclude = ('unit_topics','categories')

class UnitSchema(ma.ModelSchema):
    class Meta:
        model = Unit
        exclude = ('unit_topics',)

class UnitSchemaWithCount(ma.ModelSchema):
    num_topics = fields.Function(lambda x: len(x.unit_topics))
    class Meta:
        model = Unit
        exclude = ('unit_topics',)

def SchemaFactory(model, fields):
    dict = fields.copy()
    dict['Meta'] = type('Meta', (), {'model': model})

    return type(model.__name__ + 'Schema', (ma.ModelSchema,), dict)
