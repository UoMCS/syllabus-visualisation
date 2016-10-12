from flask import request,jsonify,abort
from flask_login import login_required
from sqlalchemy import or_

from models import get_db,Unit,Institution,Department,Topic,UnitTopic,Category,CustomTopic
from schemas import fields,SchemaFactory,TopicSchema,UnitSchema,TopicSchemaWithCount,TopicSchema2
from auth import DepartmentPermission

import json
import urllib

from api import api,get_institution_id,get_department_id


def fetch_categories(topic_name):
    params = urllib.urlencode({
        'action': 'query',
        'prop': 'categories',
        'format': 'json',
        'clshow': '!hidden',
        'cllimit': 'max',
        'titles': unicode(topic_name).encode('utf-8'),
        'indexpageids': True})
    f = urllib.urlopen("http://en.wikipedia.org/w/api.php?{}".format(params))
    responce = json.load(f)

    pageid = responce['query']['pageids'][0]

    if pageid != '-1':
        page = responce['query']['pages'][pageid]

        if 'categories' in page:
            return page['categories']

    return []


def get_categories(topic):
    fetched_categories = fetch_categories(topic.name)
    category_names = map(lambda x: x['title'], fetched_categories)

    if category_names:
        existing_categories = Category.query.filter(Category.name.in_(category_names)).all()
        existing_names = map(lambda x: x.name, existing_categories)

        new_categories = [Category(name) for name in category_names if name not in existing_names]
        map(get_db().session.add, new_categories)

        return existing_categories + new_categories
    else:
        return []


@api.route("/<string:institution_uri>/<string:department_uri>/unit_topics", methods=['GET'])
def unit_topics(institution_uri, department_uri):
    query = get_db().session.query(UnitTopic).\
    join(Unit).join(Topic).join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri)

    # TODO: find by unit_id, topic_id

    if 'unit_code' in request.args:
        unit_code = request.args['unit_code'].split('|')
        query = query.filter(Unit.code.in_(unit_code)).order_by(Topic.name)

    if 'topic_name' in request.args:
        topic_name = request.args['topic_name'].split('|')
        query = query.filter(Topic.name.in_(topic_name)).order_by(Unit.name)

    unit_topics = query.all()

    schema_fields = {}

    if 'embed' in request.args:
        embed = request.args['embed'].split(',')

        if 'topic' in embed:
            schema_fields['topic'] = fields.Nested(TopicSchema)

        if 'unit' in embed:
            schema_fields['unit'] = fields.Nested(UnitSchema)

        if 'contexts' in embed:
            schema_fields['contexts'] = fields.Nested(TopicSchema, many=True)

    Schema = SchemaFactory(UnitTopic, schema_fields)
    schema = Schema(many=True)

    return jsonify({'unit_topics': schema.dump(unit_topics).data})


@api.route("/topic/<string:topic_id>")
def topic(topic_id):
    topic = get_db().session.query(Topic).get(topic_id)

    topic_schema = TopicSchema()

    return jsonify({'topic': topic_schema.dump(topic).data})


@api.route("/<string:institution_uri>/<string:department_uri>/topic/<string:topic_id>")
def dep_topic(institution_uri, department_uri, topic_id):
    topic = get_db().session.query(Topic).get(topic_id)

    topic_schema = TopicSchema()

    return jsonify({'topic': topic_schema.dump(topic).data})


@api.route("/<string:institution_uri>/<string:department_uri>/unit_topics/add", methods=['POST'])
@login_required
def add_unit_topic(institution_uri, department_uri):

    args = request.get_json()

    topic_name = args["topic_name"]

    topic = Topic.query.filter_by(name=topic_name).one_or_none()

    db = get_db()

    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst):

        # If topic doesn't exist, need to add it
        if not topic:
            if args.has_key("topic_description"): # Custom topic
                topic = CustomTopic(name=topic_name)
                topic.description = args["topic_description"]
                # TODO: topic.keywords = request.form["keywords"].split(',')
            else: # WP topic
                topic = Topic(name=topic_name)
                topic.categories = get_categories(topic)

            db.session.add(topic)
            db.session.flush() # So that we have access to id

        unit_code = args["unit_code"]
        unit = db.session.query(Unit).join(Department).join(Institution).\
        filter(Institution.uri == institution_uri).\
        filter(Department.uri == department_uri).\
        filter(Unit.code == unit_code).one()

        unit_topic = UnitTopic(unit.id, topic.id)
        unit.unit_topics.append(unit_topic)
        db.session.add(unit)

        db.session.commit()
        return ''

    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/unit_topics/update", methods=['POST'])
@login_required
def update_unit_topic(institution_uri, department_uri):
    args = request.get_json()
    db = get_db()
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst):
        unit_topic = db.session.query(UnitTopic).get(args['id'])

        unit_topic.alias = args['alias']
        unit_topic.is_assessed = args['is_assessed']
        unit_topic.is_taught = args['is_taught']
        unit_topic.is_applied = args['is_applied']

        topic_ids = map(lambda x: x['id'], args['contexts'])
        unit_topic.contexts = Topic.query.filter(Topic.id.in_(topic_ids)).all()

        db.session.commit()

        return ''
    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/unit_topics/remove", methods=['POST'])
@login_required
def remove_syllabus_item(institution_uri, department_uri):
    db = get_db()
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst):
        unit_topic_id = (request.get_json())['unit_topic_id']
        unit_topic = db.session.query(UnitTopic).get(unit_topic_id)

        db.session.delete(unit_topic)

        db.session.commit()

        return ''
    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/topics")
def dep_topics(institution_uri, department_uri):
    topics = Topic.query.join(UnitTopic).join(Unit).\
    join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    all()

    topic_schema = TopicSchemaWithCount(many=True)

    return jsonify({'topics': topic_schema.dump(topics).data})


@api.route("/<string:institution_uri>/<string:department_uri>/topics/<int:limit>/<int:offset>")
def dep_topics_limit(institution_uri, department_uri, limit, offset):
    topics = Topic.query.join(UnitTopic).join(Unit).\
    join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri)

    topic_schema = TopicSchema2(many=True)
    department = get_department_id(institution_uri, department_uri)

    count = topics.count()
    tosend = topic_schema.dump(topics.limit(limit).offset(offset).all()).data
    for topic in tosend:
        topic['unit_topics'][:] = [unit for unit in topic['unit_topics'] if unit['unit']['department'] == department]

    return jsonify({'topics': tosend, 'total': count})


@api.route("/<string:institution_uri>/<string:department_uri>/topics/filter/<int:limit>/<int:offset>", methods=['POST'])
def topic_filter_limit(institution_uri, department_uri, limit, offset):
    args = request.get_json()
    db = get_db()

    # here be dragons, sorry to any DBAs

    starter = db.session.query(Topic.id).join(UnitTopic).join(Unit).\
    join(Department).join(Institution).\
    filter(Institution.uri == institution_uri, Department.uri == department_uri)

    include = {}
    exclude = {}

    # create a subquery for each filter
    for i,f in enumerate(args['include']):
        filter_group = []
        if 'taught' in f['taught']:
            filter_group.append(UnitTopic.is_taught == 1)
        if 'assessed' in f['taught']:
            filter_group.append(UnitTopic.is_assessed == 1)
        if 'applied' in f['taught']:
            filter_group.append(UnitTopic.is_applied == 1)

        include[i] = starter.filter(or_(*filter_group))

        if f.has_key('levels') and f['levels']:
            include[i] = include[i].filter(Unit.level.in_(f['levels']))

    for i,f in enumerate(args['exclude']):
        filter_group = []
        if 'taught' in f['taught']:
            filter_group.append(UnitTopic.is_taught == 1)
        if 'assessed' in f['taught']:
            filter_group.append(UnitTopic.is_assessed == 1)
        if 'applied' in f['taught']:
            filter_group.append(UnitTopic.is_applied == 1)

        exclude[i] = starter.filter(or_(*filter_group))

        if f.has_key('levels') and f['levels']:
            exclude[i] = exclude[i].filter(Unit.level.in_(f['levels']))


    topics = Topic.query.join(UnitTopic).join(Unit).\
    join(Department).join(Institution).\
    filter(Institution.uri == institution_uri, Department.uri == department_uri)

    for f in include:
        topics = topics.filter(Topic.id.in_(include[f]))
    for f in exclude:
        topics = topics.filter(Topic.id.notin_(exclude[f]))

    topic_schema = TopicSchema2(many=True)
    department = get_department_id(institution_uri, department_uri)

    count = topics.count()
    tosend = topic_schema.dump(topics.limit(limit).offset(offset).all()).data
    for topic in tosend:
        topic['unit_topics'][:] = [unit for unit in topic['unit_topics'] if unit['unit']['department'] == department]


    return jsonify({ 'topics': tosend, 'total': count })
