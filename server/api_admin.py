from flask import request,jsonify,abort
from flask_login import login_required

from auth import bcrypt,DepartmentPermission,InstitutionPermission,AdminPermission

from models import get_db,User,Institution,Unit,Department
from schemas import InstitutionSchema,DepartmentSchema

from api import api,get_department_id,get_institution_id


@api.route("/admin")
@login_required
def admin():
    modules = {}
    if AdminPermission().can():
        modules['Add user'] = "add_user_global"
        modules['Add department'] = "add_department_global"
        modules['Add institution'] = "add_institution_global"
        modules['Add units'] = "add_units_global"
    else:
        modules['Add user'] = "add_user"
        modules['Add units'] = "add_units"
    return jsonify(modules)


@api.route("/<string:institution_uri>/<string:department_uri>/admin/bulkaddunits", methods=['POST'])
@login_required
def bulk_add_units(institution_uri, department_uri):
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst).can():
        args = request.get_json()
        newunits = []
        for unit in args['units']:
            newunits.append(Unit(code=unit['code'], name=unit['name'], level=unit['level'], department_id=dep))

        db = get_db()
        db.session.bulk_save_objects(newunits)
        db.session.commit()

        return str(len(newunits))
    abort(403)


@api.route("/<string:institution_uri>/<string:department_uri>/admin/adduser", methods=['POST'])
@login_required
def add_user(institution_uri, department_uri):
    dep  = get_department_id(institution_uri, department_uri)
    inst = get_institution_id(institution_uri)

    if DepartmentPermission(dep, inst).can():
        db = get_db()
        args = request.get_json()

        user = User(username=args['username'], password=bcrypt.generate_password_hash(args['password']), department=dep)
        db.session.add(user)
        db.session.commit()

        return ''
    abort(403)


@api.route("/admin/institutions", methods=['GET'])
@login_required
def institutions():
    institutions = Institution.query.all()

    inst_schema = InstitutionSchema(many=True)

    return jsonify({'institutions': inst_schema.dump(institutions).data})


@api.route("/<string:institution_uri>/admin/departments", methods=['GET'])
@login_required
def departments(institution_uri):
    inst = get_institution_id(institution_uri)

    if InstitutionPermission(inst).can():
        departments = Department.query.join(Institution).\
            filter(Institution.uri == institution_uri).all()

        dept_schema = DepartmentSchema(many=True)

        return jsonify({'departments': dept_schema.dump(departments).data})
    abort(403)


@api.route("/<string:institution_uri>/admin/adddepartment", methods=['POST'])
@login_required
def add_department(institution_uri):
    inst = get_institution_id(institution_uri)

    if InstitutionPermission(inst).can():
        db = get_db()
        args = request.get_json()

        department = Department(name=args['name'], uri=args['uri'], institution=inst)
        db.session.add(department)
        db.session.commit()

        return '1'
    abort(403)

@api.route("/admin/addinstitution", methods=['POST'])
@login_required
def add_institution():
    if AdminPermission().can():
        db = get_db()
        args = request.get_json()

        institution = Institution(name=args['name'], uri=args['uri'])
        db.session.add(institution)
        db.session.commit()

        department = Department(name="admin", uri="admin", institution=institution.id)
        db.session.add(department)
        db.session.commit()

        admin = User(username=args['username'], password=bcrypt.generate_password_hash(args['password']), department=department.id)
        db.session.add(admin)
        db.session.commit()

        return '1'
    abort(403)

@api.route("/<string:institution_uri>/admin/removedepartment", methods=['POST'])
@login_required
def remove_department(institution_uri):
    inst = get_institution_id(institution_uri)

    if InstitutionPermission(inst).can():
        db = get_db()
        dept_id = (request.get_json())['id']
        department = db.session.query(Department).get(dept_id)

        db.session.delete(department)
        db.session.commit()

        return ''
    abort(403)


@api.route("/admin/removeinstitution", methods=['POST'])
@login_required
def remove_institution():
    if AdminPermission().can():
        db = get_db()
        inst_id = (request.get_json())['id']
        institution = db.session.query(Institution).get(inst_id)

        db.session.delete(institution)
        db.session.commit()

        return ''
    abort(403)


@api.route("/<string:institution_uri>/admin/updatedepartment", methods=['POST'])
@login_required
def update_department(institution_uri):
    inst = get_institution_id(institution_uri)
    args = request.get_json()

    if InstitutionPermission(inst).can():
        db = get_db()
        department = db.session.query(Department).get(args['id'])

        department.name = args['name']
        department.uri = args['uri']

        db.session.commit()

        return ''
    abort(403)


@api.route("/admin/updateinstitution", methods=['POST'])
@login_required
def update_institution():
    args = request.get_json()

    if AdminPermission().can():
        db = get_db()
        institution = db.session.query(Institution).get(args['id'])

        institution.name = args['name']
        institution.uri = args['uri']

        db.session.commit()

        return ''
    abort(403)
