from flask import Flask, render_template, request
from Blockchain.client.sendBTC import SendBTC
from Blockchain.Backend.core.Tx import Tx

app = Flask(__name__)

@app.route('/', methods = ["GET", "POST"])
def wallet():
    message = ''

    print('1')

    if request.method == "POST":
        FromAddress = request.form.get("fromAddress")
        ToAddress = request.form.get("toAddress")
        Amount = request.form.get("Amount", type = int)
        sendCoin = SendBTC(fromAccount = FromAddress,
                toAccount = ToAddress,
                Amount = Amount,
                UTXOS=UTXOS)
        TxObj = sendCoin.prepareTransaction()
        
        print('2')

        scriptPubKey = sendCoin.scriptPubKey(FromAddress)
        verified = True

        
        if not TxObj:
            message = "Invalid Trasaction"
            print('3')

        if isinstance(TxObj, Tx):
            for index, tx in enumerate(TxObj.tx_ins):
                if not TxObj.verify_input(input_index=index, script_pubkey=scriptPubKey):
                    verified = False
                print('4')
            
            print('5')
            
            if verified:
                MEMPOOL[TxObj.TxId] = TxObj
                message = "Transaction added in Memory Pool"
                print('6')

    print('7')
    return render_template('wallet.html', message = message)

def main(utxos, MemPool):
    global UTXOS
    global MEMPOOL

    UTXOS = utxos
    MEMPOOL = MemPool

    app.run()