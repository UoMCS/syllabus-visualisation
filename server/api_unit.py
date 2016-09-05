from flask import request,jsonify,abort
from flask_login import login_required

from models import Unit,Department,Institution,get_db
from schemas import UnitSchemaWithCount,UnitSchema
from auth import DepartmentPermission

from api import api,get_institution_id,get_department_id


@api.route("/units")
def units():
    units = Unit.query.all()

    unit_schema = UnitSchemaWithCount(many=True)

    return jsonify({'units': unit_schema.dump(units).data})


@api.route("/<string:institution_uri>/<string:department_uri>/units")
def dep_units(institution_uri, department_uri):
    units = Unit.query.join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    all()

    unit_schema = UnitSchemaWithCount(many=True)

    return jsonify({'units': unit_schema.dump(units).data})


@api.route("/<string:institution_uri>/<string:department_uri>/units/<int:limit>/<int:offset>")
def dep_units_limit(institution_uri, department_uri, limit, offset):
    units = Unit.query.join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    limit(limit).offset(offset).all()

    count = Unit.query.join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    count()

    unit_schema = UnitSchemaWithCount(many=True)

    return jsonify({'units': unit_schema.dump(units).data, 'total': count})


@api.route("/<string:institution_uri>/<string:department_uri>/unit/<string:unit_code>", methods=['GET'])
def dep_unit(institution_uri, department_uri, unit_code):
    unit = Unit.query.join(Department).join(Institution).\
    filter(Institution.uri == institution_uri).\
    filter(Department.uri == department_uri).\
    filter(Unit.code == unit_code).one()

    unit_schema = UnitSchema()

    return jsonify({'unit': unit_schema.dump(unit).data})


@api.route("/<string:institution_uri>/<string:department_uri>/unit/add", methods=["POST"])
@login_required
def add_unit(institution_uri, department_uri):
    args = request.get_json()
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst).can():
        unit_code = args["code"]
        unit_name = args["name"]
        unit_level = args["level"]

        department = Department.query.join(Institution).\
        filter(Institution.uri == institution_uri).\
        filter(Department.uri == department_uri).\
        one().id

        unit = Unit.query.filter(Unit.code==unit_code).\
        filter(Unit.department_id==department).first()

        db = get_db()

        if not unit:
            unit = Unit(code=unit_code, name=unit_name, level=unit_level, department_id=department)
            db.session.add(unit)
            db.session.commit()
            return '1'

        return '0'
    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/unit/update", methods=['POST'])
@login_required
def update_unit(institution_uri, department_uri):
    args = request.get_json()
    db = get_db()
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst).can():
        unit = db.session.query(Unit).get(args['id'])

        unit.level = args['level']
        unit.code = args['code']
        unit.name = args['name']

        db.session.commit()

        return ''
    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/unit/remove", methods=['POST'])
@login_required
def remove_unit(institution_uri, department_uri):
    db = get_db()
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst).can():
        unit_id = (request.get_json())['id']
        unit = db.session.query(Unit).get(unit_id)

        db.session.delete(unit)

        db.session.commit()

        return ''
    abort(403)

