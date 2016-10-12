from flask import request,session
from flask_login import LoginManager,current_user,login_user,logout_user,login_required
from models import User,get_db,Department,Institution
from app import app
from flask_bcrypt import Bcrypt
from sqlalchemy import or_

from collections import namedtuple
from functools import partial

from flask_principal import Principal,identity_loaded,Permission,RoleNeed,identity_changed,Identity,AnonymousIdentity

from api import api

login_manager = LoginManager()
login_manager.init_app(app)
bcrypt = Bcrypt(app)

Principal(app)

@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(int(user_id))


NormalNeed = namedtuple('normal', ['method', 'value'])
DepartmentNeed = partial(NormalNeed, 'edit')
InstitutionNeed = partial(NormalNeed, 'mod')
AdminNeed = RoleNeed('admin')


# permission to edit a given department
class DepartmentPermission(Permission):
    def __init__(self, department_id, institution_id=None):
        dept = DepartmentNeed(department_id)
        inst = InstitutionNeed(institution_id)
        admn = AdminNeed
        super(DepartmentPermission, self).__init__(dept, inst, admn)


# permission to edit a given institution
class InstitutionPermission(Permission):
    def __init__(self, institution_id):
        inst = InstitutionNeed(institution_id)
        admn = AdminNeed
        super(InstitutionPermission, self).__init__(inst, admn)


# global permissions
class AdminPermission(Permission):
    def __init__(self):
        super(AdminPermission, self).__init__(AdminNeed)


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # add the needs to the identity
    if hasattr(current_user, 'department_id'):
        identity.provides.add(DepartmentNeed(current_user.department_id))
        if current_user.department.name == 'admin':
            identity.provides.add(InstitutionNeed(current_user.department.institution.id))
            if current_user.department.institution.name == 'admin':
                identity.provides.add(AdminNeed)



@api.route("/login", methods=["POST"])
def login():
    args = request.get_json()

    user = get_db().session.query(User).join(Department).join(Institution).\
    filter(or_(Institution.uri == i for i in (args["institution"], 'admin'))).\
    filter(or_(Department.uri == d for d in (args["department"], 'admin'))).\
    filter(User.username == args["user"]).one_or_none()

    if user:
        if bcrypt.check_password_hash(user.password, args["pass"]):
            login_user(user)
            identity_changed.send(app, identity=Identity(user.id))
            return '1'
    return '0'


@api.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(app, identity=AnonymousIdentity())
    return '1'

