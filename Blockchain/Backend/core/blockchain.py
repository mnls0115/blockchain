import sys
sys.path.append('/Users/user/Dropbox/2024Projects/Blockchain')
# sys.path.append('/Users/mnls0/Dropbox/2024Projects/Blockchain')

import configparser
from Blockchain.Backend.core.block import Block
from Blockchain.Backend.core.blockheader import BlockHeader
from Blockchain.Backend.util.util import hash256, merkle_root, target_to_bits
from Blockchain.Backend.core.database.database import BlockchainDB, NodeDB
from Blockchain.Backend.core.Tx import CoinbaseTx
from multiprocessing import Process, Manager
from Blockchain.Frontend.run import main
from Blockchain.Backend.core.network.syncManager import syncManager
import time

Zero_HASH = '0' * 64
VERSION = 1
INITIAL_TARGET = 0x0000ffff00000000000000000000000000000000000000000000000000000000

class Blockchain:
    def __init__(self, utxos, MemPool):
        self.utxos = utxos
        self.MemPool = MemPool
        self.current_target = INITIAL_TARGET
        self.bits = target_to_bits(INITIAL_TARGET)
    
    def write_on_disk(self, block):
        blockchainDB = BlockchainDB()
        blockchainDB.write(block)

    def fetch_last_block(self):
        blockchainDB = BlockchainDB()
        return blockchainDB.lastBlock()

    def GenesisBlock(self):
        BlockHeight = 0
        prevBlockHash = Zero_HASH
        self.addBlock(BlockHeight = BlockHeight,
                      prevBlockHash = prevBlockHash)
        
    """ Start the Sync Node """
    def startSync(self):
        node = NodeDB()
        portList = node.read()

        for port in portList:
            if localHostPort != port:
                sync = syncManager(localHost, port)
                sync.startDownload(port)

    """ Keep track of all the unspent Transaction in cache memory for fast retrival"""
    def store_utxos_in_cache(self):
        for tx in self.addTransactionsInBlock:
            print(f"Transaction added {tx.TxId}")
            print(self.utxos)
            self.utxos[tx.TxId] = tx

    def remove_spent_Transaction(self):
        for txId_index in self.remove_spent_transaction:
            hex0 = txId_index[0].hex()
            if hex0 in self.utxos:
                if len(self.utxos[hex0].tx_outs) < 2:
                    print(f"Spent Transaction removed {hex0}")
                    del self.utxos[hex0]
                else:
                    prev_trans = self.utxos[hex0]
                    self.utxos[hex0] = prev_trans.tx_outs.pop(txId_index[1])

    """ Read Transaction from Memory Pool """
    def read_transaction_from_memorypool(self):
        self.Blocksize = 80
        self.TxIds = []
        self.addTransactionsInBlock = []
        self.remove_spent_transaction = []

        for tx in self.MemPool:
            self.TxIds.append(bytes.fromhex(tx))
            self.addTransactionsInBlock.append(self.MemPool[tx])
            self.Blocksize += len(self.MemPool[tx].serialize())

            for spent in self.MemPool[tx].tx_ins:
                self.remove_spent_transaction.append([spent.prev_tx, spent.prev_index])
    
    """ Remove transactions from memory pool """
    def remove_transactions_from_memorypool(self):
        for tx in self.TxIds:
            if tx.hex() in self.MemPool:
                del self.MemPool[tx.hex()]

    def convert_to_json(self):
        self.TxJson = []

        for tx in self.addTransactionsInBlock:
            self.TxJson.append(tx.to_dict())

    def calculate_fee(self):
        self.input_amount = 0
        self.output_amout = 0

        """ Calculate input amount """
        for TxId_index in self.remove_spent_transaction:
            if TxId_index[0].hex() in self.utxos:
                self.input_amount += self.utxos[TxId_index[0].hex()].tx_outs[TxId_index[1]].amount
        
        """ Calculate output amount """
        for tx in self.addTransactionsInBlock:
            for tx_out in tx.tx_outs:
                self.output_amout += tx_out.amount
        
        self.fee = self. input_amount - self.output_amout

    def addBlock(self, BlockHeight, prevBlockHash):
        self.read_transaction_from_memorypool()
        self.calculate_fee()
        timestamp = int(time.time())
        coinbaseInstance = CoinbaseTx(BlockHeight=BlockHeight)
        coinbaseTx = coinbaseInstance.CoinbaseTransaction()
        self.Blocksize += len(coinbaseTx.serialize())

        coinbaseTx.tx_outs[0].amount = coinbaseTx.tx_outs[0].amount + self.fee

        self.TxIds.insert(0, bytes.fromhex(coinbaseTx.id()))
        self.addTransactionsInBlock.insert(0, coinbaseTx)

        merkleRoot = merkle_root(self.TxIds)[::-1].hex()
        blockHeader = BlockHeader(version = VERSION,
                                  prevBlockHash = prevBlockHash,
                                  merkleRoot = merkleRoot,
                                  timestamp = timestamp,
                                  bits = self.bits,
                                  nonce = 0)
        blockHeader.mine(self.current_target)

        self.remove_spent_Transaction()
        self.remove_transactions_from_memorypool()
        self.store_utxos_in_cache()
        self.convert_to_json()

        self.write_on_disk([Block(BlockHeight = BlockHeight,
                                Blocksize = self.Blocksize,
                                BlockHeader = blockHeader.__dict__,
                                TxCount = len(self.TxJson),
                                Txs = self.TxJson).__dict__])

    def main(self):
        lastBlock = self.fetch_last_block()
        if lastBlock is None:
            self.GenesisBlock()

        while True:
            lastBlock = self.fetch_last_block()
            BlockHeight = lastBlock["BlockHeight"] + 1
            prevBlockHash = lastBlock["BlockHeader"]["blockHash"]
            self.addBlock(BlockHeight = BlockHeight,
                          prevBlockHash = prevBlockHash)

if __name__ == "__main__":
    """ Read configuration file"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    localHost = config['DEFAULT']['host']
    localHostPort = int(config['MINER']['port'])
    webport = int(config['webhost']['port'])

    with Manager() as manager:
        utxos = manager.dict()
        MemPool = manager.dict()

        webapp = Process(target = main, args = (utxos, MemPool, webport))
        webapp.start()

        """ Start server and Listen for miner requests """
        sync = syncManager(localHost, localHostPort)
        startServer = Process(target = sync.spinUpTheServer)
        startServer.start()

        blockchain = Blockchain(utxos, MemPool)
        blockchain.startSync()
        blockchain.main()