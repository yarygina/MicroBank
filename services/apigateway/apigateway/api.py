import os

from flask import Flask, request, abort
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
    PAYMENT_SERVICE_URL      = '%s://%s:%s/' % (PROT, "payment", 80)
else:
    FLASK_PORT = 80
    USERS_SERVICE_URL        = '%s://%s:%s/' % (PROT, '0.0.0.0', 9081)
    ACCOUNTS_SERVICE_URL     = '%s://%s:%s/' % (PROT, '0.0.0.0', 9082)
    TRANSACTIONS_SERVICE_URL = '%s://%s:%s/' % (PROT, '0.0.0.0', 9083)
    PAYMENT_SERVICE_URL      = '%s://%s:%s/' % (PROT, '0.0.0.0', 9084)

app = Flask(__name__)



@app.route("/", methods=['GET'])
def hello():
    return niceJson({"subresource_uris": allLinks(app)}, 200)


@app.route("/users", methods=['GET'])
def userInfo():
    username = request.args.get('username')
    try:
        url = USERS_SERVICE_URL + 'users'
        if username:
            url += '?username=%s' % username
        res = requests.get(url)
    except ConnectionError as e:
        raise ServiceUnavailable("Users service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("Cannot get user information, status %s" \
                       % (res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/users", methods=['POST'])
def userEnroll():
    if not request.json or not 'username' in request.json or \
                           not 'pwd' in request.json:
        abort(400)
    username = request.json['username']
    pwd = request.json['pwd']
    try:
        url = USERS_SERVICE_URL + 'users'
        payload = {'username':username, 'pwd':pwd}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable("Users service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("Cannot register user %s, resp %s, status code %s" \
                       % (username, res.text, res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/users/<userID>/accounts", methods=['GET'])
@jwt_conditional(requests)
def accountsInfo(userID):
    try:
        url = ACCOUNTS_SERVICE_URL + 'accounts' + '?userID=%s' % userID
        res = requests.get(url)
    except ConnectionError as e:
        raise ServiceUnavailable("Accounts service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("No accounts found for userID %s, status %s" \
                       % (userID, res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/users/<userID>/accounts", methods=['POST'])
@jwt_conditional(requests)
def openAccount(userID):
    try:
        url = ACCOUNTS_SERVICE_URL + 'accounts'
        payload = {'userID':userID}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable("Accounts service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("Cannot open account for userID %s, status code %s" \
                       % (userID, res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/users/<userID>/accounts/<accNum>/transactions", methods=['GET'])
@jwt_conditional(requests)
def transactionsInfo(accNum):
    try:
        url = TRANSACTIONS_SERVICE_URL + 'transactions' + '?accNum=%s'%accNum
        res = requests.get(url)
    except ConnectionError as e:
        raise ServiceUnavailable(
              "Transactions service connection error: %s." % e)

    if int(res.status_code) >= 400:
        logger.warning("No transactions found for accNum %s, status %s" \
                       % (accNum, res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/users/<userID>/pay", methods=['POST'])
@jwt_conditional(requests)
def pay(userID):
    if (not request.json or not 'fromAccNum' in request.json
                        or not 'toAccNum' in request.json
                        or not 'amount' in request.json):
        abort(400)
    fromAccNum = request.json['fromAccNum']
    toAccNum = request.json['toAccNum']
    amount = request.json['amount']
    try:
        url = PAYMENT_SERVICE_URL + 'pay'
        payload = {'fromAccNum':fromAccNum, 'toAccNum':toAccNum, 
                   'amount':amount}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable("Payment service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("Cannot execute payment from " + \
                       "%s to %s amount %s, resp %s, status code %s" \
                       % (fromAccNum, toAccNum, amount, res.text, 
                          res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/login", methods=['POST'])
def login():
    if not request.json or not 'username' in request.json or \
                           not 'pwd' in request.json:
        abort(400)
    username = request.json['username']
    pwd = request.json['pwd']
    try:
        url = USERS_SERVICE_URL + 'users/login'
        payload = {'username':username, 'pwd':pwd}
        res = requests.post(url, json=payload)
    except ConnectionError as e:
        raise ServiceUnavailable("Users service connection error: %s."%e)

    if int(res.status_code) >= 400:
        logger.warning("Cannot login user %s, resp %s, status code %s" \
                       % (username, res.text, res.status_code))
        resp = res.text
    else:
        resp = res.json()
    return niceJson(resp, res.status_code)


@app.route("/logout", methods=['POST'])
@jwt_conditional(requests)
def logout():
    raise NotImplementedError()


# All APIs provided by this application, automatically generated
LOCAL_APIS = allLinks(app)
# All external APIs that this application relies on, manually created
KNOWN_REMOTE_APIS = [USERS_SERVICE_URL + "users",
                    ACCOUNTS_SERVICE_URL + "accounts",
                    TRANSACTIONS_SERVICE_URL + "transactions",
                    PAYMENT_SERVICE_URL + "pay",
                    USERS_SERVICE_URL + "users/login"]


# def main():
#     logger.info("%s service starting now: MTLS=%s, Token=%s" \
#                 % (serviceType, MTLS, TOKEN))
#     # Start Flask web server
#     if MTLS and serviceCert:
#         # SSL configuration for Flask. Order matters!
#         cert = serviceCert.getServiceCertFileName()
#         key = serviceCert.getServiceKeyFileName()
#         if cert and key:
#             app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)#, 
#             #        ssl_context=(cert,key))
#         else:
#             logger.error("Cannot serve API without SSL cert and key.")
#             exit()
#     else:
#         app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)



# if __name__ == "__main__":
#     main()









