import json
import time
import datetime
from multiprocessing import Process, Queue

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
# Set the default logger to DEBUG to see the Requests library logging info.
#logging.basicConfig(level=logging.DEBUG)

import requests

HOST = '0.0.0.0'
APIGATEWAY_PORT = 80

IS_MISSFIRE = False
IS_MISSFIRE_TOKEN = False

if IS_MISSFIRE:
    PROT = 'https'
else:
    PROT = 'http'


NUM_PAYMENTS_PER_CLIENT = 100

class Simulation():
    def __init__(self, procNum):
        self.client = BankClient()
        self.customers = [{'username':str(procNum), 'pwd':'1234'},
                          {'username':str(procNum+1), 'pwd':'5678'}]
        
        if len(self.customers) == 0:
            print ("No customers to add!")
            exit()

        print("Adding %s bank customers." % (len(self.customers)))
        for customer in self.customers:
            userID = self.client.createUser(customer['username'],
                                             customer['pwd'])
            if userID:
                customer['userID'] = userID
            else:
                exit()

            if IS_MISSFIRE_TOKEN:
                token = self.client.login(customer['username'], customer['pwd'])
                if token:
                    customer['access_token'] = token
                else:
                    exit()
            else:
                customer['access_token'] = "notoken"

            accNum = self.client.openAccount(customer['userID'],
                                             customer['access_token'])
            if accNum:
                customer['accNum'] = accNum
            else:
                exit()


    def printPerformance(self):
        endTime = datetime.datetime.now()
        secondsPassed = float((endTime - self.startTime).total_seconds())
        return secondsPassed
        

    def runPaymentTest(self, queue):
        self.queue = queue
        print ("Start payment.")
        self.startTime = datetime.datetime.now()
        x = 0
        y = 1
        for i in xrange(0,NUM_PAYMENTS_PER_CLIENT+1):
            res = self.client.pay(self.customers[x]['accNum'], 
                                  self.customers[y]['accNum'], 
                                  20, 
                                  self.customers[x]['userID'],
                                  self.customers[x]['access_token'])
            if res:
                x, y = y, x
            else:
                print ("Fail")
        self.queue.put(self.printPerformance())
        return



class BankClient:
    def __init__(self):
        self.BASE_URL = "%s://%s:%s" % (PROT, HOST, APIGATEWAY_PORT)
        self.s = requests.Session()

    def createUser(self, username, pwd):
        userID = None
        try:
            url = self.BASE_URL + '/users'
            payload = {'username':username, 
                       'pwd':pwd}
            resp = self.s.post(url, json=payload, verify=False, allow_redirects=False, stream=False)

            # If the user already exist, request his id
            if 'User already exists' in resp.text:
                url += '?username=%s' % username
                resp = self.s.get(url, json=payload, verify=False, allow_redirects=False, stream=False)
            # Proceed with the id extraction
            if int(resp.status_code) >= 400:
                print("Fail to create user: %s; reason: %s; status: %s" \
                      % (username, resp.text, resp.status_code))
            elif 'id' not in resp.json():
                print("'id' not in response msg: %s" % resp.json())
            else:
                userID = resp.json()['id']
                return userID
        except requests.exceptions.ConnectionError as e:
            print("Connection error create user: %s" % e)
        

    def login(self, username, pwd):
        userID = None
        try:
            url = self.BASE_URL + '/login'
            payload = {'username':username, 
                       'pwd':pwd}
            resp = self.s.post(url, json=payload, verify=False, allow_redirects=False, stream=False)

            # Proceed with the access_token extraction
            if int(resp.status_code) >= 400:
                print("Fail to login user: %s; reason: %s; status: %s" \
                      % (username, resp.text, resp.status_code))
            elif 'access_token' not in resp.json():
                print("'access_token' not in response msg: %s" \
                      % resp.json())
            else:
                access_token = resp.json()['access_token']
                return access_token
        except requests.exceptions.ConnectionError as e:
            print("Connection error create user: %s" % e)
        

    def openAccount(self, userID, token):
        accNum = None
        url = '{}/users/{}/accounts'.format(self.BASE_URL, userID)
        try:
            payload = {'access_token': token}
            resp = self.s.post(url, json=payload, verify=False, allow_redirects=False, stream=False)

            if int(resp.status_code) >= 400:
                print("Fail to open account for user: %s; reason: %s; status: %s" \
                      % (userID, resp.text, resp.status_code))
            elif 'accNum' not in resp.json():
                print("'accNum' not in response msg: %s" % resp.json())
            else:
                accNum = resp.json()['accNum']

        except requests.exceptions.ConnectionError as e:
            print("Connection error open account: %s" % e)
        return accNum

    def pay(self, fromAccNum, toAccNum, amount, userID, token):
        res = False
        try:
            url = self.BASE_URL + '/users/%s/pay' % userID
            payload = {'fromAccNum':fromAccNum, 
                       'toAccNum':toAccNum, 
                       'amount':amount,
                       'access_token': token}
            resp = self.s.post(url, json=payload, verify=False, allow_redirects=False, stream=False)

            if int(resp.status_code) >= 400:
                print("Fail to pay: %s; reason: %s; status: %s" \
                      % (payload, resp.text, resp.status_code))
            else:
                res = True

        except requests.exceptions.ConnectionError as e:
            print("Connection error payment: %s" % e)
        return res




def main():
    numProcesses = 1
    queueList = []
    processList = []
    for x in xrange(0,numProcesses):
        q = Queue()
        queueList.append(q)
        p = Process(target=Simulation(x*2).runPaymentTest, args=(q,))
        processList.append(p)

    startTime = datetime.datetime.now()
    for p in processList:
        p.start()

    totalTime = 0
    for q in queueList:
        timeElapsed = q.get()
        totalTime+=timeElapsed
        #print "Result", timeElapsed

    endTime = datetime.datetime.now()
    secondsPassed = float((endTime - startTime).total_seconds())
    
    # operationsPerSec = float(NUM_PAYMENTS_PER_CLIENT*numProcesses / totalTime)
    # print "Transactions per second (%d/%f): %f" \
    #      % (NUM_PAYMENTS_PER_CLIENT*numProcesses, totalTime, operationsPerSec)
    operationsPerSec = float(NUM_PAYMENTS_PER_CLIENT*numProcesses / secondsPassed)
    print "Transactions per second (%d/%f): %f" \
         % (NUM_PAYMENTS_PER_CLIENT*numProcesses, secondsPassed, operationsPerSec)

    for p in processList:
        p.join()




if __name__ == "__main__":
    main()
