import pygraphviz as pgv
from lxml import etree
import textwrap
import json
import copy

class SyllabusGraph(pgv.AGraph):

    def __init__(self, style_path='', urlpart='', is_embedded=False, directed=False, *args, **kwargs):
        super(SyllabusGraph,self).__init__(overlap='false', outputorder='edgesfirst', directed=directed, *args, **kwargs)

        # support creating plain AGraphs
        if style_path=='':
            return

        self.is_embedded = is_embedded
        self.urlpart = urlpart

        with open(style_path) as f:
            self.style = json.loads(f.read())
            for key in self.style:
                if 'inherit' in self.style[key]:
                    parent = self.style[key]['inherit']
                    overwrites = self.style[key]
                    overwrites.pop('inherit', None)
                    self.style[key] = copy.deepcopy(self.style[parent])
                    self.style[key].update(overwrites)

    def add_unit_node(self, unit, is_central=False, groupa=None):
        wrapped_name = textwrap.fill(unit.name, width = 15)

        style = None

        key = 'unit_' + str(unit.level)
        if key in self.style:
            style = self.style[key]
        else:
            style = self.style['unit_default']

        node_name = "unit_{}".format(unit.id)

        self.add_node(node_name,
            id=node_name,
            label=wrapped_name,
            URL='#/'+self.urlpart+'/graph/unit/{}'.format(unit.code),
            group=str(groupa),
            **style)

        return node_name

    def add_category_node(self, category, weight):
        label = category.name.split(":",1)[1]
        label = '\n'.join(textwrap.wrap("%s" % label,  width = 15))

        node_name = "category_{}".format(category.id)

        self.add_node(node_name,
            id=node_name,
            label=label,
            width=1.7+((weight-1)*0.5),
            fontsize=14+(weight-1),
            URL='#/'+self.urlpart+'/graph/category/{}'.format(category.id),
            **self.style['category'])

        return node_name

    def add_topic_node(self, topic, is_central=False):
        label = None

        if self.is_embedded:
            label = topic.name
        else:
            label = (u'<<table border="0" cellpadding="5" cellspacing="0" cellborder="0">' +
                u'<tr><td href="#/'+self.urlpart+'/topic/{0}" title="Topic page" valign="middle">{1}</td>' +
                u'<td valign="middle" href="//en.wikipedia.org/wiki/{1}" title="Wikipedia article" target="_blank_"><font face="Glyphicons Halflings" point-size="12" color="#666666">\ue164</font></td></tr>' +
                u'</table>>')

            label = label.format(
                topic.id,
                topic.name)

        style = self.style['central_topic'] if is_central else self.style['topic']

        node_name = self.topic_node_name(topic)

        self.add_node(node_name,
            id=node_name,
            label=label,
            **style)

        return node_name

    def add_edge(self, source, target):
        super(SyllabusGraph, self).add_edge(source, target, **self.style['edge'])

    def add_category_edge(self, source, target):
        super(SyllabusGraph, self).add_edge(source, target, **self.style['category_edge'])

    def render_svg(self, fixed=False):
        if fixed or self.is_directed():
            # directed graphs
            self.layout(prog='dot')
        else:
            # fastest for large graphs
            self.layout(prog='sfdp')

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


