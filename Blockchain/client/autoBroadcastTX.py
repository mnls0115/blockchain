import requests
import time
import random
from Blockchain.Backend.core.database.database import AccountDB

fromAccount = "1H1TM38tlGswV89qs5j23WpoP6NuXbgMn5"

""" Read all the accounts """
AllAccounts = AccountDB().read()

""" 3초마다 random 하게 coin을 발산시키는 코드로, 추후 수정 필요"""
def autoBroadcast():
    while True:
        for account in AllAccounts:
            if account["PublicAddress"] != fromAccount:
                paras = {"fromAddress" : fromAccount,
                        "toAddress" : account["PublicAddress"],
                        "Amount" : random.randint(1,15)}
                
                res = requests.post(url = "http://localhost:5900/wallet", data = paras)
        time.sleep(3)