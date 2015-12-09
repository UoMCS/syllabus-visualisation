from flask import *

# NB: Order is important
from models import *
from schemas import *

from graph import SyllabusGraph

import json
import urllib
from collections import Counter

def svg_response(svg):
    return Response(svg, mimetype='image/svg+xml')

def addCategoryNodes(g, topics):
    category_topics = {}

    for topic in topics:
        for category in topic.categories:
            category_topics.setdefault(category, set()).add(topic)

    for category in category_topics:
        if len(category_topics[category]) > 1:
            category_node = g.add_category_node(category, len(category_topics[category]))

            for topic in category_topics[category]:
                g.add_category_edge(category_node, SyllabusGraph.topic_node_name(topic))

api = Blueprint('syl_vis_api', __name__)

@api.route("/units")
def units():
    """ Main page """
    units = Unit.query.all()

    unit_schema = UnitSchemaWithCount(many=True)

    return jsonify({'units': unit_schema.dump(units).data})


@api.route("/unit/<string:unit_code>", methods=['GET'])
def unit(unit_code):
    """ Unit page """
    unit = Unit.query.filter_by(code=unit_code).one()

    unit_schema = UnitSchema()

    return jsonify({'unit': unit_schema.dump(unit).data})

@api.route("/unit_topics", methods=['GET'])
def unit_topics():
    """ Unit page """
    query = db.session.query(UnitTopic).join(Unit).join(Topic)

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
    """ Topic page """

    topic = db.session.query(Topic).get(topic_id)

    topic_schema = TopicSchema()

    return jsonify({'topic': topic_schema.dump(topic).data})

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
        map(db.session.add, new_categories)

        return existing_categories + new_categories
    else:
        return []

@api.route("/unit_topics/add", methods=['POST'])
def add_unit_topic():
    """ Add syllabus item """

    args = request.get_json()

    topic_name = args["topic_name"]

    topic = Topic.query.filter_by(name=topic_name).first()
    is_new = False

    # If topic doesn't exist, need to add it
    if not topic:
        is_new = True

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
    unit = db.session.query(Unit).filter_by(code=unit_code).one()

    unit_topic = UnitTopic(unit.id, topic.id)
    unit.unit_topics.append(unit_topic)
    db.session.add(unit)

    db.session.commit()

    return ''

@api.route("/unit_topics/update", methods=['POST'])
def update_unit_topic():
    """ Update unit topic """
    args = request.get_json()

    unit_topic = db.session.query(UnitTopic).get(args['id'])

    unit_topic.alias = args['alias']
    unit_topic.is_assessed = args['is_assessed']
    unit_topic.is_taught = args['is_taught']
    unit_topic.is_applied = args['is_applied']

    topic_ids = map(lambda x: x['id'], args['contexts'])
    unit_topic.contexts = Topic.query.filter(Topic.id.in_(topic_ids)).all()

    db.session.commit()

    return ''

@api.route("/unit_topics/remove", methods=['POST'])
def remove_syllabus_item():
    """ Removes syllabus item """

    # Find the topic needs removed
    unit_topic_id = (request.get_json())['unit_topic_id']
    unit_topic = db.session.query(UnitTopic).get(unit_topic_id)

    # Remove it
    db.session.delete(unit_topic)
    db.session.commit()

    return ''

# @api.route("/category/<string:category>")
# @auto.doc()
# def category_page(category):
#     """ Category page """
#     db = connectToDB()

#     query = """
#         SELECT topic_id, unit_code, unit_name
#         FROM syllabus
#         JOIN units USING (unit_code)
#         WHERE topic_id IN
#             (SELECT topic_id
#              FROM topic_categories
#              WHERE category=?);
#     """

#     items = db.execute(query, (category,)).fetchall()


#     raw_svg = request.args.has_key('svg')
#     g = SyllabusGraph(raw_svg)
#     g.add_category_node(category, len(items))
#     for item in items:
#         g.add_unit_node(item["unit_code"], item["unit_name"])
#         g.add_topic_node(item["topic_id"])
#         g.add_edge(item["unit_code"], item["topic_id"])
#         g.add_edge(item["topic_id"], category)
#     svg = g.render_svg()

#     if raw_svg:
#         return svg_responce(svg)
#     else:
#         return render_template('category_graph.html', category=category, graph=svg)

@api.route("/graph")
def units_graph():
    """ Main graph """
    topics = db.session.query(Topic).all()

    raw_svg = request.args.has_key('svg')

    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], raw_svg)
    for topic in topics:
        topic_node = g.add_topic_node(topic)

        for unit_topic in topic.unit_topics:
            unit_node = g.add_unit_node(unit_topic.unit)
            g.add_edge(unit_node, topic_node)

    return svg_response(g.render_svg())

@api.route("/graph/unit/<string:unit_code>")
def unit_graph(unit_code):
    """ Unit graph """
    unit = db.session.query(Unit).filter_by(code=unit_code).one()

    raw_svg = request.args.has_key('svg')

    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], raw_svg)
    unit_node = g.add_unit_node(unit, unit.code == unit_code)
    for unit_topic in unit.unit_topics:
        topic_node = g.add_topic_node(unit_topic.topic)
        g.add_edge(unit_node, topic_node)

        # Add related units
        for related_unit_topic in unit_topic.topic.unit_topics:
            related_unit_node = g.add_unit_node(related_unit_topic.unit)
            g.add_edge(related_unit_node, topic_node)

    addCategoryNodes(g, [ut.topic for ut in unit.unit_topics])

    return svg_response(g.render_svg())


@api.route("/graph/topic/<string:topic_id>")
def topic_graph(topic_id):
    """ Topic page """

    topic = db.session.query(Topic).get(topic_id)

    raw_svg = request.args.has_key('svg')
    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], raw_svg)
    topic_node = g.add_topic_node(topic, True)
    addCategoryNodes(g, [topic])

    for unit_topic in topic.unit_topics:
        unit_node = g.add_unit_node(unit_topic.unit)
        g.add_edge(unit_node, topic_node)

        for related_unit_topic in unit_topic.unit.unit_topics:
            related_topic_node = g.add_topic_node(related_unit_topic.topic)
            g.add_edge(unit_node, related_topic_node)

        addCategoryNodes(g, [ut.topic for ut in unit_topic.unit.unit_topics])

    return svg_response(g.render_svg())
