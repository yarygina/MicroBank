import os
import sys
from functools import wraps

from flask import Flask, request, abort

from general import log, getEnvVar, isDocker, niceJson, allLinks
from db_controller import db_create, db_migrate, dbCtrl


# Use the name of the current directory as a service type
serviceType = os.path.basename(os.getcwd())
logger = log(serviceType).logger

# Setup MiSSFire
if getEnvVar('TOKEN', False):
    try:
        from MiSSFire import jwt_conditional, Requests
        requests = Requests()
    except ImportError:
        logger.error("Module MiSSFire is required. Terminating.")
        exit()
else:
    import requests
    def jwt_conditional(reqs):
        def real_decorator(f):
            return f
        return real_decorator


# Setup Flask
# FLASK_DEBUG = getEnvVar('FLASK_DEBUG', False)
# FLASK_HOST = '0.0.0.0'
if isDocker():
    FLASK_PORT = 80
else:
    FLASK_PORT = 9082

app = Flask(__name__)




DEFAULT_BALANCE = 1000

# Load DB controller
db = dbCtrl(logger)

def prepareDB():
    """Insure presence of the required DB files."""
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


@app.route("/accounts", methods=['GET'])
@jwt_conditional(requests)
def accountsGet():
    userID = request.args.get('userID')
    if userID:
        res = db.getAccountsByUserId(userID, json=True)
    else:
        res = db.getAllAccounts()    
    if res:
        res_code = 200
    else:
        res = {}
        res_code = 400
    return niceJson(res, res_code)


@app.route("/accounts", methods=['POST'])
@jwt_conditional(requests)
def accountsPost():
    if not request.json or not 'userID' in request.json:
        abort(400)
    res = {}
    res_code = 400
    try:
        userID = int(request.json['userID'])
        accNum = db.createAccountForUserId(userID, DEFAULT_BALANCE)
        if accNum != 1:
            res = {'accNum': accNum}
            res_code = 200
    except ValueError:
        msg="UserID expected integer, received: %s"%request.json['userID']
        logger.warning(msg)
        res = {'msg': msg}
    logger.info("niceJson(res): %s, %s" % (niceJson(res,res_code), res))
    return niceJson(res, res_code)


@app.route("/accounts/<accNum>", methods=['GET'])
@jwt_conditional(requests)
def accountsAccNumGet(accNum):
    res = {}
    res_code = 400
    try:
        accNum = int(accNum)
        res = db.getAccountByNum(accNum, json=True)
        if res:
            res_code = 200
    except ValueError:
        msg="accNum expected integer, received: %s"%request.json['accNum']
        logger.warning(msg)
        res = {'msg': msg}
    return niceJson(res, res_code)


@app.route("/accounts/<accNum>", methods=['DELETE'])
@jwt_conditional(requests)
def accountsAccNumDel(accNum):
    res = {}
    res_code = 400
    try:
        accNum = int(accNum)
        if db.closeAccount(accNum) == 0:
            res = request.json
            res_code = 200
    except ValueError:
        msg="accNum expected integer, received: %s"%request.json['accNum']
        logger.warning(msg)
        res = {'msg': msg}
    return niceJson(res, res_code)


@app.route("/accounts/<accNum>", methods=['POST'])
@jwt_conditional(requests)
def accountsAccNumPost(accNum):
    if not request.json or not 'amount' in request.json:
        abort(400)
    res = {}
    res_code = 400
    try:
        accNum = int(accNum)
        amount = int(request.json['amount'])
        new_balance = db.updateAccount(accNum, amount)
        if new_balance:
            res = {'balance':new_balance}
            res_code = 200
    except ValueError:
        msg = "Expected integers: accNum=%s, amount=%s" \
              % (request.json['accNum'], request.json['amount'])
        logger.warning(msg)
        res = {'msg': msg}
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


