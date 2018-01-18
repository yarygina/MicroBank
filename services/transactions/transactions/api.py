import os
import sys
import datetime

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
    from general import Requests
    requests = Requests()
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
    FLASK_PORT = 9083

app = Flask(__name__)


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


@app.route("/transactions", methods=['GET'])
@jwt_conditional(requests)
def transactionsIndex():
    accNum = request.args.get('accNum')
    if accNum:
        res = db.getAllTransactionsForAcc(accNum, json=True)
    else:
        res = db.getAllTransactions()
    return niceJson(res, 200)


@app.route("/transactions", methods=['POST'])
@jwt_conditional(requests)
def postTransaction():
    if (not request.json or not 'fromAccNum' in request.json
                        or not 'toAccNum' in request.json
                        or not 'amount' in request.json):
        abort(400)
    fromAccNum = request.json['fromAccNum']
    toAccNum = request.json['toAccNum']
    amount = int(request.json['amount'])
    res = ""
    res_code = 400
    transNum = db.addTransactionBetweenAccs(fromAccNum, toAccNum, amount)
    if transNum != 0:
        res = {'number': transNum}
        res_code = 200
    return niceJson(res, res_code)


@app.route("/transactions/<number>", methods=['GET'])
@jwt_conditional(requests)
def getTransaction(number):
    return niceJson(db.getTransactionByNum(number, json=True)), 200


@app.route("/transactions/<number>", methods=['DELETE'])
@jwt_conditional(requests)
def cancelTransaction(number):
    res = ""
    res_code = 400
    if db.cancelTransaction(number) == 0:
        res = {'number': number}
        res_code = 200
    return niceJson(res, res_code)


# All APIs provided by this application, automatically generated
LOCAL_APIS = allLinks(app)
# All external APIs that this application relies on, manually created
KNOWN_REMOTE_APIS = []


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



