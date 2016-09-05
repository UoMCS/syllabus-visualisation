from flask import jsonify,Blueprint

from models import Institution,Department
from schemas import DepartmentGroupedSchema,DepartmentSchema,InstitutionSchema


api = Blueprint('syl_vis_api', __name__)


def get_department_id(institution_uri, department_uri):
    department = Department.query.join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).one()

    return department.id


def get_institution_id(institution_uri):
    institution = Institution.query.\
    filter(Institution.uri == institution_uri).one()

    return institution.id


import api_graph
import api_admin
import api_unit
import api_topic


@api.route("/departments_group", methods=['GET'])
def departments_group():
    departments = Institution.query.all()
    dept_schema = DepartmentGroupedSchema(many=True)

    data = dept_schema.dump(departments).data
    # filter out the admin institution/departments
    data = [ins for ins in data if ins['uri'] != 'admin']
    for i in data:
        i['departments'][:] = [dep for dep in i['departments'] if dep['uri'] != 'admin']

    return jsonify({'institutions': data})


@api.route("/<string:institution_url>/departments", methods=['GET'])
def get_departments(institution_url):
    departments = Department.query.join(Institution).\
    filter(Institution.uri == institution_url).\
    filter(Department.uri != "admin").all()

    dept_schema = DepartmentSchema(many=True)

    return jsonify({'departments': dept_schema.dump(departments).data})


@api.route("/institutions/", methods=['GET'])
def get_institutions():
    institutions = Institution.query.\
    filter(Institution.uri != "admin").all()

    inst_schema = InstitutionSchema(many=True)

    return jsonify({'institutions': inst_schema.dump(institutions).data})


@api.route("/<string:institution_url>", methods=['GET'])
def institution_info(institution_url):
    institution = Institution.query.filter(Institution.uri == institution_url).one()
    inst_schema = InstitutionSchema()

    return jsonify(inst_schema.dump(institution).data)

