import os

from flask import Flask, request, abort
from requests import codes
from requests.exceptions import ConnectionError
from werkzeug.exceptions import NotFound, ServiceUnavailable

from general import log, getEnvVar, isDocker, niceJson, allLinks


# Use the name of the current directory as a service type
serviceType = os.path.basename(os.getcwd())
logger = log(serviceType).logger

# Setup MiSSFire
try:
    PROT = 'http'
    if getEnvVar('MTLS', False) or getEnvVar('TOKEN', False):
        from MiSSFire import Requests
        requests = Requests()
        if getEnvVar('MTLS', False):
            PROT = 'https'

        if getEnvVar('TOKEN', False):
            from MiSSFire import jwt_conditional
        else:
            def jwt_conditional(reqs):
                def real_decorator(f):
                    return f
                return real_decorator
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
    USERS_SERVICE_URL        = '%s://%s:%s/' % (PROT, "users", 80)
    ACCOUNTS_SERVICE_URL     = '%s://%s:%s/' % (PROT, "accounts", 80)
    TRANSACTIONS_SERVICE_URL = '%s://%s:%s/' % (PROT, "transactions", 80)
else:
    FLASK_PORT = 9084
    USERS_SERVICE_URL        = '%s://%s:%s/' % (PROT, '0.0.0.0', 9081)
    ACCOUNTS_SERVICE_URL     = '%s://%s:%s/' % (PROT, '0.0.0.0', 9082)
    TRANSACTIONS_SERVICE_URL = '%s://%s:%s/' % (PROT, '0.0.0.0', 9083)

app = Flask(__name__)



@app.route("/", methods=['GET'])
def hello():
    return niceJson({"subresource_uris": allLinks(app)}, 200)


@app.route("/pay", methods=['POST'])
@jwt_conditional(requests)
def pay():
    if (not request.json or not 'fromAccNum' in request.json
                        or not 'toAccNum' in request.json
                        or not 'amount' in request.json):
        abort(400)
    fromAccNum = request.json['fromAccNum']
    toAccNum = request.json['toAccNum']
    amount = float(request.json['amount'])

    res = ""
    res_code = 400
    transNum = postTransaction(fromAccNum, toAccNum, amount)

    try:
        if transNum:
            if (not updateAccount(fromAccNum, -amount) or not updateAccount(toAccNum, amount)):
                cancelTransaction(transNum)
            else:
                res_code = 200
    except Exception as e:
        logger.error("Payment: %s" % e)

    return niceJson(res, res_code)


def postTransaction(fromAccNum, toAccNum, amount):
    try:
        url = TRANSACTIONS_SERVICE_URL + 'transactions'
        payload = {'fromAccNum':fromAccNum, 'toAccNum':toAccNum, 
                   'amount':amount}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable(
              "Transactions service connection error: %s." % e)

    if res.status_code != codes.ok:
        raise NotFound("Cannot post a transaction from " + \
              "%s to %s amount %s, resp %s, status code %s" \
              % (fromAccNum, toAccNum, amount, res.text, res.status_code))
    else:
        return res.json()['number']


def updateAccount(accNum, amount):
    try:
        url = ACCOUNTS_SERVICE_URL + 'accounts/%s' % accNum
        payload = {'amount':amount}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable("Accounts service connection error: %s."%e)

    if res.status_code != codes.ok:
        raise NotFound("Cannot update account %s, resp %s, status code %s" \
                       % (accNum, res.text, res.status_code))
    else:
        return res.json()['balance']


def cancelTransaction(transNum):
    try:
        url = TRANSACTIONS_SERVICE_URL + 'transactions/%s' % transNum
        res = requests.delete(url)
    except ConnectionError as e:
        raise ServiceUnavailable(
              "Transactions service connection error: %s." % e)

    if res.status_code != codes.ok:
        raise NotFound("Cannot cancel transaction %s, resp %s, status code %s" \
                       % (transNum, res.text, res.status_code))
    else:
        return res.json()['number']



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








