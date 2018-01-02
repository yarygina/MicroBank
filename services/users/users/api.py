import os
import sys

from flask import Flask, request, abort

from general import log, getEnvVar, isDocker, niceJson, allLinks
from db_controller import db_create, db_migrate, dbCtrl


# Use the name of the current directory as a service type
serviceType = os.path.basename(os.getcwd())
logger = log(serviceType).logger

# Setup MiSSFire
TOKEN_REQUIRED = getEnvVar('TOKEN', False)
try:
    if TOKEN_REQUIRED:
        from MiSSFire import jwt_conditional, Requests
        requests = Requests()
    else:
        import requests
        def jwt_conditional(reqs):
            def real_decorator(f):
                return f
            return real_decorator
except ImportError:
    logger.error("Module MiSSFire is required. Terminating.")
    exit()


# Setup Flask
# FLASK_DEBUG = getEnvVar('FLASK_DEBUG', False)
# FLASK_HOST = '0.0.0.0'
if isDocker():
    FLASK_PORT = 80
else:
    FLASK_PORT = 9081


app = Flask(__name__)



# Load DB controller
db = dbCtrl(logger)

def prepareDB():
    """Ensure presence of the required DB files."""
    res = False
    if db_create.isDBVolume():
        if not db_create.isDBfile():
            db_create.main()
            db_migrate.main()
        res = True
    return res

if not prepareDB():
    logger.error("Missing volume. Terminating.")
    sys.exit(1)




@app.route("/", methods=['GET'])
def hello():
    return niceJson({"subresource_uris": allLinks(app)}, 200)


@app.route("/users", methods=['GET'])
def usersIndex():
    res_code = 400
    username = request.args.get('username')
    if username:
        res = {'id': db.getByUsername(username, json=True)['id']}
    else:
        res = db.getAllUsers(json=True)
    if res:
        res_code = 200
    return niceJson(res, res_code)


@app.route("/users", methods=['POST'])
def addUser():
    if not request.json or not 'username' in request.json or \
                           not 'pwd' in request.json:
        abort(400)
    username = request.json['username']
    res = ""
    res_code = 400
    if not db.isUserName(username):
        pwd = request.json['pwd']
        userJson = db.createUser(username, pwd)
        if userJson != 1 and userJson != 2 and 'id' in userJson:
            res = {'id': userJson['id']}
            res_code = 200
    else:
        res = "User already exists"
    return niceJson(res, res_code)


@app.route("/users/userID", methods=['DELETE'])
@jwt_conditional(requests)
def removeUser(userID):
    if db.isUserID(userID):
        db.removeUserID(userID)
        res = "User (userID=%s) removed" % userID
    else:
        res = "User (userID=%s) non existent" % userID
    return niceJson({'Result': res}), 201


@app.route("/users/login", methods=['POST'])
def login():
    if not request.json or not 'username' in request.json or \
                           not 'pwd' in request.json:
        abort(400)
    res = {}
    res_code = 403

    username = request.json['username']
    pwd = request.json['pwd']

    isAllowedCode = db.isUserAllowed(username, pwd)
    if isAllowedCode == 0:
        if TOKEN_REQUIRED:
            accessToken = requests.securityToken.getToken(username)
            if accessToken:
                res = {'access_token': accessToken}
                res_code = 201
    return niceJson(res, res_code)



# def main():
#     logger.info("%s service starting now: MTLS=%s, Token=%s" \
#                 % (SERVICE_TYPE, MTLS, TOKEN))
#     # Start Flask web server
#     if MTLS and serviceCert:
#         # SSL configuration for Flask. Order matters!
#         cert = serviceCert.getServiceCertFileName()
#         key = serviceCert.getServiceKeyFileName()
#         if cert and key:
#             app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, \
#                     ssl_context=(cert,key))
#         else:
#             logger.error("Cannot serve API without SSL cert and key.")
#             exit()
#     else:
#         app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
        


# if __name__ == "__main__":
#     main()    



