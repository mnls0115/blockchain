import sys
sys.path.append('/Users/user/Dropbox/2024Projects/Blockchain')
# sys.path.append('/Users/mnls0/Dropbox/2024Projects/Blockchain')

from Blockchain.Backend.core.block import Block
from Blockchain.Backend.core.blockheader import BlockHeader
from Blockchain.Backend.util.util import hash256
from Blockchain.Backend.core.database.database import BlockchainDB
from Blockchain.Backend.core.Tx import CoinbaseTx
from multiprocessing import Process, Manager
from Blockchain.Frontend.run import main
import time

Zero_HASH = '0' * 64
VERSION = 1

class Blockchain:
    def __init__(self, utxos):
        self.utxos = utxos
    
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

    """ Keep track of all the unspent Transaction in cache memory for fast retrival"""
    def store_utxos_in_cache(self, Transaction):
        self.utxos[Transaction.TxId] = Transaction

    def addBlock(self, BlockHeight, prevBlockHash):
        timestamp = int(time.time())
        coinbaseInstance = CoinbaseTx(BlockHeight=BlockHeight)
        coinbaseTx = coinbaseInstance.CoinbaseTransaction()

        merkleRoot = coinbaseTx.TxId
        bits = 'ffff001f'
        blockHeader = BlockHeader(version = VERSION,
                                  prevBlockHash = prevBlockHash,
                                  merkleRoot = merkleRoot,
                                  timestamp = timestamp,
                                  bits = bits)
        blockHeader.mine()
        self.store_utxos_in_cache(coinbaseTx)
        self.write_on_disk([Block(BlockHeight = BlockHeight,
                                Blocksize = 1,
                                BlockHeader = blockHeader.__dict__,
                                TxCount = 1,
                                Txs = coinbaseTx.to_dict()).__dict__])

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
    with Manager() as manager:
        utxos = manager.dict()

        webapp = Process(target = main, args = (utxos,))
        webapp.start()

        blockchain = Blockchain(utxos)
        blockchain.main()