from collections import defaultdict

from flask import Response,request,current_app

from models import Topic,UnitTopic,Institution,Department,Unit,get_db,Category
from graph import SyllabusGraph

from api import api


def taught_toint(unit_topic):
    return sum(1<<i for i, b in enumerate([
        unit_topic.is_assessed,
        unit_topic.is_taught,
        unit_topic.is_applied
    ]) if b)

def get_label(taught):
    label = []
    if taught & 1:
        label.append('assessed')
    if taught & 2:
        label.append('taught')
    if taught & 4:
        label.append('applied')

    if not label:
        return "no data"
    return ', '.join(label)


def svg_response(svg):
    return Response(svg, mimetype='image/svg+xml')


def addCategoryNodes(g, topics):
    category_topics = {}

    for topic in topics:
        for category in topic.categories:
            category_topics.setdefault(category, set()).add(topic)

    for category in category_topics:
        if len(category_topics[category]) > 1:
            category_node = g.add_category_node(category,
                                                len(category_topics[category]))

            for topic in category_topics[category]:
                g.add_category_edge(category_node,
                                    SyllabusGraph.topic_node_name(topic))


@api.route("/<string:institution_uri>/<string:department_uri>/graph")
def units_graph(institution_uri, department_uri):
    unit_topics = get_db().session.query(UnitTopic).\
    join(Unit).join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).all()

    raw_svg = request.args.has_key('svg')
    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], institution_uri + '/' + department_uri, raw_svg)

    for unit_topic in unit_topics:
        unit_node = g.add_unit_node(unit_topic.unit)
        topic_node = g.add_topic_node(unit_topic.topic)
        g.add_edge(unit_node, topic_node)

    return svg_response(g.render_svg())


@api.route("/<string:institution_uri>/<string:department_uri>/graph/unit/<string:unit_code>")
def unit_graph(institution_uri, department_uri, unit_code):
    unit = get_db().session.query(Unit).join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    filter(Unit.code == unit_code).one_or_none()

    if not unit:
        return ''

    raw_svg = request.args.has_key('svg')

    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], institution_uri + '/' + department_uri, raw_svg)
    unit_node = g.add_unit_node(unit, unit.code == unit_code)

    for unit_topic in unit.unit_topics:
        topic_node = g.add_topic_node(unit_topic.topic)
        g.add_edge(unit_node, topic_node)

        # Add related units
        for related_unit_topic in unit_topic.topic.unit_topics:
            if (related_unit_topic.unit.department.uri == department_uri):
                if (related_unit_topic.unit.department.institution.uri == institution_uri):
                    related_unit_node = g.add_unit_node(related_unit_topic.unit)
                    g.add_edge(related_unit_node, topic_node)

    addCategoryNodes(g, [ut.topic for ut in unit.unit_topics])

    return svg_response(g.render_svg())


@api.route("/<string:institution_uri>/<string:department_uri>/graph/topic/<string:topic_id>")
def topic_graph(institution_uri, department_uri, topic_id):
    topic = get_db().session.query(Topic).get(topic_id)

    raw_svg = request.args.has_key('svg')
    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], institution_uri + '/' + department_uri, raw_svg)
    topic_node = g.add_topic_node(topic, True)
    addCategoryNodes(g, [topic])

    for unit_topic in topic.unit_topics:
        if (unit_topic.unit.department.uri == department_uri):
            if (unit_topic.unit.department.institution.uri == institution_uri):
                unit_node = g.add_unit_node(unit_topic.unit)
                g.add_edge(unit_node, topic_node)

                for related_unit_topic in unit_topic.unit.unit_topics:
                    related_topic_node = g.add_topic_node(related_unit_topic.topic)
                    g.add_edge(unit_node, related_topic_node)

                addCategoryNodes(g, [ut.topic for ut in unit_topic.unit.unit_topics])

    return svg_response(g.render_svg())


@api.route("/<string:institution_uri>/<string:department_uri>/graph/topic_route/<string:topic_id>")
def topic_graph_route(institution_uri, department_uri, topic_id):
    topic = get_db().session.query(Topic).get(topic_id)

    raw_svg = request.args.has_key('svg')
    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'],
                      institution_uri + '/' + department_uri, raw_svg, True)

    # store the units by level so we can process them later
    units = defaultdict(list)
    clusters = defaultdict(list)

    for unit_topic in topic.unit_topics:
        if unit_topic.unit.department.uri != department_uri or\
                unit_topic.unit.department.institution.uri != institution_uri:
            continue

        node = g.add_unit_node(unit_topic.unit,
                               False,
                               unit_topic.unit.level)
        units[unit_topic.unit.level].append(node)
        taught = taught_toint(unit_topic)
        if not clusters[taught]:
            clusters[taught] = g.add_subgraph([node],name='cluster_'+str(taught),label=get_label(taught))
        else:
            clusters[taught].add_node(node)

    # add edges from all units of the previous level to
    # all units of the next, skipping over missing levels
    last_level_units = min(units.items())[1]
    for level in range(min(units.keys())+1, max(units.keys())+1):
        if units[level]:
            for unit in units[level]:
                for prev in last_level_units:
                    g.add_edge(prev, unit)

            last_level_units = units[level]

    return svg_response(g.render_svg(True))


@api.route("/<string:institution_uri>/<string:department_uri>/graph/category/<string:category_id>")
def category_graph(institution_uri, department_uri, category_id):

    category = get_db().session.query(Category).get(category_id);

    # category = get_db().session.query(Category).join((Topic, Category.topics)).\
        # join(UnitTopic).join(Department).join(Institution).\
        # filter(Institution.uri == institution_uri).\
        # filter(Department.uri == department_uri).get(category_id)

    raw_svg = request.args.has_key('svg')
    g = SyllabusGraph(current_app.config['GRAPH_STYLE_PATH'], institution_uri + '/' + department_uri, raw_svg)

    category_node = g.add_category_node(category, len(category.topics))

    for topic in category.topics:
        topic_node = g.add_topic_node(topic)
        g.add_category_edge(category_node, topic_node)

        for unit_topic in topic.unit_topics:
            unit_node = g.add_unit_node(unit_topic.unit)
            g.add_edge(unit_node, topic_node)

    return svg_response(g.render_svg())

