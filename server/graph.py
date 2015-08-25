import pygraphviz as pgv
from lxml import etree
import textwrap
from flask import url_for

class SyllabusGraph(pgv.AGraph):

    UNIT_STYLE = {
        'fixedsize': True,
        'style': 'filled', 
        'width': 1.8, 
        'height': 1.8, 
        'fontname': 'Helvetica',
        'fontcolor': 'white',
        'color': 'black', 
        'shape': 'doublecircle'
    }

    CENTRAL_UNIT_STYLE = dict(UNIT_STYLE, color='red')

    TOPIC_STYLE = {
        'style': 'filled, rounded',
        'fontname': 'Helvetica',
        'fontcolor': 'white',
        'color': '#105060FF',
        'shape' : 'box'
    }

    CENTRAL_TOPIC_STYLE = dict(TOPIC_STYLE, color='red')

    EDGE_STYLE = {
        'color': '#00000030',
        'headclip': 'false',
        'tailclip': 'false'
    }

    CATEGORY_EDGE_STYLE = dict(EDGE_STYLE, style='invis', len=0.4)

    CATEGORY_STYLE = {
        'fontname': 'Helvetica',
        'fontcolor': 'black',
        'fillcolor: '#FFEEFF', 
        'color': '#500050',
        'style': 'filled',
        'fixedsize': True,
        'shape': 'circle',
    }

    def __init__(self, is_embedded=False):
        super(SyllabusGraph,self).__init__(overlap='false', outputorder='edgesfirst')

        self.is_embedded = is_embedded

    def add_unit_node(self, unit, is_central=False):
        wrapped_name = textwrap.fill(unit.name, width = 15)

        style = self.CENTRAL_UNIT_STYLE if is_central else self.UNIT_STYLE

        node_name = "unit_{}".format(unit.id)

        self.add_node(node_name,
            id=node_name,
            label=wrapped_name, 
            URL='#/graph/unit/{}'.format(unit.code),
            **style)

        return node_name

    def add_category_node(self, name, weight):
        label = name.split(":",1)[1]
        label = '\n'.join(textwrap.wrap("%s" % label,  width = 15))

        self.add_node(name, 
            id="category_" + self._hashed(name), 
            label=label,
            width=1.7+((weight-1)*0.5), 
            fontsize=14+(weight-1),
            # URL=url_for('category_page', category=name),
            **self.CATEGORY_STYLE)

    def add_topic_node(self, topic, is_central=False):
        label = None

        if self.is_embedded:
            label = topic.name
        else:
            label = (u'<<table border="0" cellpadding="5" cellspacing="0" cellborder="0">' +
                u'<tr><td href="#/graph/topic/{0}" title="Topic page" valign="middle">{1}</td>' +
                u'<td valign="middle" href="//en.wikipedia.org/wiki/{1}" title="Wikipedia article" target="_blank_"><font face="Glyphicons Halflings" point-size="12" color="#666666">\ue164</font></td></tr>' +
                u'</table>>')

            label = label.format(
                topic.id,
                topic.name)

        style = self.CENTRAL_TOPIC_STYLE if is_central else self.TOPIC_STYLE

        node_name = self.topic_node_name(topic)

        self.add_node(node_name, 
            id=node_name,
            label=label,
            **style)

        return node_name

    def add_edge(self, source, target):
        super(SyllabusGraph, self).add_edge(source, target, **self.EDGE_STYLE)

    def add_invisible_edge(self, source, target):
        super(SyllabusGraph, self).add_edge(source, target, **self.CATEGORY_EDGE_STYLE)

    def render_svg(self):
        self.layout(prog='neato')
        svg = self.draw(format='svg').decode('utf-8')

        svgparser = etree.XMLParser(encoding='utf-8')
        svgobj = etree.fromstring(svg.encode('utf-8'), parser=svgparser)

        svgobj.attrib['width'] = "100%"
        svgobj.attrib['height'] = "100%"

        for n in svgobj.xpath('//n:text', namespaces={'n': "http://www.w3.org/2000/svg"}):
            n.attrib['text-rendering'] = 'geometricPrecision'

        return etree.tostring(svgobj, pretty_print=True)

    @staticmethod
    def topic_node_name(topic):
        return 'topic_{}'.format(topic.id)


