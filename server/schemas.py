from __future__ import print_function
from marshmallow import fields
from flask_marshmallow import Marshmallow

from app import app
from models import *

ma = Marshmallow(app)

class CategorySchema(ma.ModelSchema):
    class Meta:
        model = Category
        exclude = ('topics',)

class TopicSchema(ma.ModelSchema):
    class Meta:
        model = Topic
        exclude = ('unit_topics',)
    categories = ma.Nested(CategorySchema, many=True)

class UnitSchema(ma.ModelSchema):
    class Meta:
        model = Unit
        exclude = ('unit_topics',)

class UnitSchemaWithCount(ma.ModelSchema):
    num_topics = fields.Function(lambda x: len(x.unit_topics))
    class Meta:
        model = Unit
        exclude = ('unit_topics',)

class TopicSchemaWithCount(ma.ModelSchema):
    num_units = fields.Function(lambda x: len(x.unit_topics))
    class Meta:
        model = Topic
        exclude = ('categories', 'contexts', 'custom_topics')

class InstitutionSchema(ma.ModelSchema):
    class Meta:
        model = Institution
        exclude = ('departments',)

class DepartmentSchema(ma.ModelSchema):
    class Meta:
        model = Department
        exclude = ('units','users')
        sqla_session = get_db().session
    sqla_session = get_db().session

class DepartmentGroupedSchema(ma.ModelSchema):
    class Meta:
        model = Institution
    departments = ma.Nested(DepartmentSchema, many=True, exclude=('institution',))

class UnitTopicSchema(ma.ModelSchema):
    class Meta:
        model = UnitTopic
    unit = ma.Nested(UnitSchema, only=["code", "department"])

class TopicSchema2(ma.ModelSchema):
    class Meta:
        model = Topic
        exclude = ('categories','contexts')
    unit_topics = ma.Nested(UnitTopicSchema, many=True, only=["unit"])

def SchemaFactory(model, fields):
    dict = fields.copy()
    dict['Meta'] = type('Meta', (), {'model': model})

    return type(model.__name__ + 'Schema', (ma.ModelSchema,), dict)
