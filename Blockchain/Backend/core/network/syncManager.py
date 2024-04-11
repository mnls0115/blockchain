from Blockchain.Backend.core.network.connection import Node
from Blockchain.Backend.core.database.database import BlockchainDB
from Blockchain.Backend.core.network.network import requestBlock, NetworkEnvelope, FinishedSending
from Blockchain.Backend.core.block import Block
from threading import Thread

class syncManager:
    def __init__(self, host, port):
        self.host = host
        self.port = port

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
            if envelope.command == requestBlock.command:
                start_block, end_block = requestBlock.parse(envelope.stream())
                self.sendBlockTORequestor(start_block)
                print(f"start block is {start_block} \n end block is {end_block}")
        except Exception as e:
            print(f"Error while processing the clinet request \n {e}")

    def sendBlockTORequestor(self, start_block):
        blockToSend = self.fetchBlocksFromBlockchain(start_block)

        try:
            self.sendBlock(blockToSend)
            self.sendFinishedMessage()
        except Exception as e:
            print(f"unable to send the blocks \n {e}")
    
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


    def startDownload(self, port):
        lastBlock = BlockchainDB().lastBlock()

        if not lastBlock:
            GENESISBLOCK = "0000e1dfe5b172fb6eb904379055d9e53eba18a5041c3ebad4bc709abd65fe4b"
        else:
            lastBlockHeader = lastBlock['BlockHeader']['blockHash']

        startBlock = bytes.fromhex(lastBlockHeader)
        
        getHeaders = requestBlock(startBlock = startBlock)
        self.connect = Node(host = self.host, port = port)
        self.socket = self.connect.connect(port)
        self.connect.send(getHeaders)

        while True:
            self.stream = self.socket.makefile('rb', None)
            envelope = NetworkEnvelope.parse(self.stream)

            if envelope.command == b'Finished':
                print(f"All Blocks Recieved")
                self.socket.close()

            if envelope.command == b'block':
                blockObj = Block.parse(envelope.stram())
                print(f"Block Recieved = {blockObj.BlockHeight}")