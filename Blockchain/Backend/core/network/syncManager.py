from Blockchain.Backend.core.network.connection import Node
from Blockchain.Backend.core.blockheader import BlockHeader
from Blockchain.Backend.core.database.database import BlockchainDB, NodeDB
from Blockchain.Backend.core.Tx import Tx
from Blockchain.Backend.core.network.network import (requestBlock,
                                                     NetworkEnvelope,
                                                     FinishedSending,
                                                     portlist)
from Blockchain.Backend.core.block import Block
from Blockchain.Backend.util.util import little_endian_to_int
from threading import Thread

class syncManager:
    def __init__(self, host, port, newBlockAvailable = None, secondaryChain = None, Mempool = None):
        self.host = host
        self.port = port
        self.newBlockAvailable = newBlockAvailable
        self.secondaryChain = secondaryChain
        self.Mempool = Mempool

    def spinUpTheServer(self):
        self.server = Node(self.host, self.port)
        self.server.startServer()
        print("SERVER STARTED")
        print(f"[LISTENING] at {self.host}:{self.port}")

        while True:
            self.conn, self.addr = self.server.acceptConnection()
            handleConn = Thread(target = self.handleConnection)
            handleConn.start()

    def handleConnection(self):
        envelope = self.server.read()
        try:
            if len(str(self.addr[1])) == 4:
               self.addNode()

            if envelope.command == b'Tx':
                Transaction = Tx.parse(envelope.stream())
                Transaction.TxId = Transaction.id()
                self.Mempool[Transaction.TxId] = Transaction

            if envelope.command == b'block':
                blockObj = Block.parse(envelope.stream())
                BlockHeaderObj = BlockHeader(blockObj.BlockHeader.version,
                                             blockObj.BlockHeader.prevBlockHash,
                                             blockObj.BlockHeader.merkleRoot,
                                             blockObj.BlockHeader.timestamp,
                                             blockObj.BlockHeader.bits,
                                             blockObj.BlockHeader.nonce)
                
                self.newBlockAvailable[BlockHeaderObj.generateBlockHash()] = blockObj
                print(f"New Block Received : {blockObj.BlockHeight}")

            if envelope.command == requestBlock.command:
                start_block, end_block = requestBlock.parse(envelope.stream())
                self.sendBlockTORequestor(start_block)
                print(f"start block is {start_block} \n end block is {end_block}")

            self.conn.close()
            
        except Exception as e:
            self.conn.close()
            print(f"Error while processing the clinet request \n {e}")
    
    def addNode(self):
        nodeDB = NodeDB()
        portList = nodeDB.read()

        if self.addr[1] and (self.addr[1] +1) not in portList:
            nodeDB.write([self.addr[1]+1])
        
    def sendBlockTORequestor(self, start_block):
        blockToSend = self.fetchBlocksFromBlockchain(start_block)

        try:
            self.sendBlock(blockToSend)
            self.sendSecondaryChain()
            self.sendPortlist()
            self.sendFinishedMessage()
        except Exception as e:
            print(f"unable to send the blocks \n {e}")

    def sendPortlist(self):
        nodeDB = NodeDB()
        portlists = nodeDB.read()

        portLst = portlist(portlists)
        envelope = NetworkEnvelope(portLst.command, portLst.serialize())
        self.conn.sendall(envelope.serialize())

    def sendSecondaryChain(self):
        tempSecChain = dict(self.sendSecondaryChain)
        for blockHash in tempSecChain:
            envelope = NetworkEnvelope(tempSecChain[blockHash].command,
                                       tempSecChain[blockHash].serialize())
            self.conn.sendall(envelope.serialize())

    def sendFinishedMessage(self):
        MessaggeFinish = FinishedSending()
        envelope = NetworkEnvelope(MessaggeFinish.command, MessaggeFinish.serialize())
        self.conn.sendall(envelope.serialize())
    
    def sendBlock(self,blockstoSend):
        for block in blockstoSend:
            cblock = Block.to_obj(block)
            envelope = NetworkEnvelope(cblock.command, cblock.serialize())
            self.conn.sendall(envelope.serialize())
            print(f"Block Sent {cblock.BlockHeight}")

    def fetchBlocksFromBlockchain(self, start_block):
        fromBlockonwards = start_block.hex()
        blocksToSend = []

        blockchain = BlockchainDB()
        blocks = blockchain.read()
        
        foundBlock = False
        for block in blocks:
            if block['BlockHeader']['blockHash'] == fromBlockonwards:
                foundBlock = True
                continue

            if foundBlock:
                blocksToSend.append(block)

        return blocksToSend
    
    def connectToHost(self, localport, port, bindPort = None):
        self.connect = Node(host = self.host,
                            port = port)
        if bindPort:
            self.socket = self.connect.connect(port = localport,
                                               bindPort = bindPort)
        else:
            self.socket = self.connect.connect(port = localport)
            
        self.stream = self.socket.makefile('rb', None)

    def publishBlock(self, localport, port, block):
        self.connectToHost(localport = localport,
                           port = port)
        self.connect.send(block)

    def publishTx(self,Tx):
        self.connect.send(Tx)

    def startDownload(self, localport, port, bindPort):
        lastBlock = BlockchainDB().lastBlock()

        if not lastBlock:
            GENESISBLOCK = "0000916688ae85fd9b1c3f2a9c232e011a961137290f0ff56734e36410ed7855"
        else:
            lastBlockHeader = lastBlock['BlockHeader']['blockHash']

        startBlock = bytes.fromhex(lastBlockHeader)
        
        getHeaders = requestBlock(startBlock = startBlock)
        self.connectToHost(localport = localport,
                           port = port,
                           bindPort = bindPort)
        self.connect.send(getHeaders)

        while True:
            envelope = NetworkEnvelope.parse(self.stream)

            if envelope.command == b'Finished':
                print(f"All Blocks Recieved")
                self.socket.close()
                break

            if envelope.command == b'portlist':
                ports = portlist.parse(envelope.stream)
                nodeDB = NodeDB()
                portlists = nodeDB.read()

                for port in ports:
                    if port not in portlists:
                        nodeDB.write([port])

            if envelope.command == b'block':
                blockObj = Block.parse(envelope.stram())
                BlockHeaderObj = BlockHeader(blockObj.BlockHeader.version,
                                             blockObj.BlockHeader.prevBlockHash,
                                             blockObj.BlockHeader.merkleRoot,
                                             blockObj.BlockHeader.timestamp,
                                             blockObj.BlockHeader.bits,
                                             blockObj.BlockHeader.nonce)
                
                if BlockHeaderObj.validateBlock():
                    for idx, tx in enumerate(blockObj.Txs):
                        tx.TxId = tx.id()
                        blockObj.Tx[idx] = tx.to_dict()
                    
                    BlockHeaderObj.blockHash = BlockHeaderObj.generateBlockHash()
                    BlockHeaderObj.prevBlockHash = BlockHeaderObj.prevBlockHash.hex()
                    BlockHeaderObj.merkleRoot = BlockHeaderObj.merkleRoot.hex()
                    BlockHeaderObj.nonce = little_endian_to_int(BlockHeaderObj.nonce)
                    BlockHeaderObj.bits = BlockHeaderObj.bits.hex()
                    blockObj.BlockHeader = BlockHeaderObj
                    BlockchainDB().write([blockObj.to_dict()])
                    print(f"Block Recieved - {blockObj.BlockHeight}")

                else:
                    self.secondaryChain[BlockHeaderObj.generateBlockHash()] = blockObj