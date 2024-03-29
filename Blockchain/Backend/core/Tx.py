from Blockchain.Backend.core.Script import Script
from Blockchain.Backend.util.util import int_to_little_endian, bytes_needed, decode_base58, little_endian_to_int, endcode_variant, hash256

Zero_HASH = b'\0' * 32
REWARD = 50

PRIVATEkey = '114400065097829751540911245889892421501368495624583924999187444662061965611155'
MINER_ADDRESS = '1H1TM38tlGswV89qs5j23WpoP6NuXbgMn5'
SIGHASH_ALL = 1

class CoinbaseTx:
    def __init__(self, BlockHeight):
        self.BlockHeightInLittleEndian = int_to_little_endian(BlockHeight, bytes_needed(BlockHeight))

    def CoinbaseTransaction(self):
        prev_tx = Zero_HASH
        prev_index = 0xffffffff

        tx_ins = []
        tx_ins.append(TxIn(prev_tx = prev_tx,
                           prev_index = prev_index))
        tx_ins[0].script_sig.cmds.append(self.BlockHeightInLittleEndian)
        
        tx_outs = []
        target_amount = REWARD * 100000000
        target_h160 = decode_base58(MINER_ADDRESS)
        target_script = Script.p2pkh_script(target_h160)
        tx_outs.append(TxOut(amount = target_amount,
                             script_pubkey= target_script))
        coinBaseTx = Tx(version=1,
                        tx_ins=tx_ins,
                        tx_outs=tx_outs,
                        locktime=0)
        coinBaseTx.TxId = coinBaseTx.id()

        return coinBaseTx

class Tx:
    def __init__(self, version, tx_ins, tx_outs, locktime):
        self.version = version
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs
        self.locktime = locktime

    def id(self):
        """Human readable Tx id"""
        return self.hash().hex()

    def hash(self):
        """Binary hash of serialization"""
        return hash256(self.serialize())[::-1]
    
    def serialize(self):
        result = int_to_little_endian(self.version,4)
        
        result += endcode_variant(len(self.tx_ins))
        for tx_in in self.tx_ins:
            result += tx_in.serialize()
        
        result += endcode_variant(len(self.tx_outs))
        for tx_out in self.tx_outs:
            result += tx_out.serialize()

        result += int_to_little_endian(self.locktime, 4)

        return result
    
    def sing_hash(self, input_index, script_pubkey):
        s = int_to_little_endian(self.version, 4)

        s += endcode_variant(len(self.tx_ins))
        for i, tx_in in enumerate(self.tx_ins):
            if i == input_index:
                s += TxIn(prev_tx = tx_in.prev_tx,
                          prev_index = tx_in.prev_index,
                          script_sig = script_pubkey).serialize()
            else:
                s += TxIn(prev_tx = tx_in.prev_tx,
                          prev_index = tx_in.prev_index).serialize()
        
        s += endcode_variant(len(self.tx_outs))
        for tx_out in self.tx_outs:
            s += tx_out.serialize()

        s += int_to_little_endian(self.locktime,4)
        s += int_to_little_endian(SIGHASH_ALL,4)
        h256 = hash256(s)
        return int.from_bytes(h256,'big')

    def sign_input(self, input_index, private_key, script_pubkey):
        z = self.sing_hash(input_index = input_index,
                           script_pubkey = script_pubkey)
        der = private_key.sign(z).der()
        sig = der + SIGHASH_ALL.to_bytes(1,'big')
        sec = private_key.point.sec()
        self.tx_ins[input_index].script_sig = Script([sig, sec])

    def verify_input(self, input_index, script_pubkey):
        tx_in = self.tx_ins[input_index]
        z = self.sing_hash(input_index = input_index,
                           script_pubkey = script_pubkey)
        combined = tx_in.script_sig + script_pubkey
        return combined.evaluate(z)

    def is_coinbase(self):
        """
        # Check that there is exactly 1 input
        # Grab the first input and check if the prev_tx is b'\x00' * 32
        # Chect that the first input prev_index is 0xffffffff
        """

        if len(self.tx_ins) != 1:
            return False
        
        first_input = self.tx_ins[0]
        if first_input.prev_tx != b'\x00' * 32:
            return False
        
        if first_input.prev_index != 0xffffffff:
            return False
        
        return True

    def to_dict(self):
        """
        Convert transaction
        # convert prev_tx hash in gex from bytes
        # convert BlockHeight in hex which is stored in Script signiture
        """

        for tx_index, tx_in in enumerate(self.tx_ins):
            if self.is_coinbase():
                tx_in.script_sig.cmds[0] = little_endian_to_int(tx_in.script_sig.cmds[0])

            tx_in.prev_tx = tx_in.prev_tx.hex()

            for index, cmd in enumerate(tx_in.script_sig.cmds):
                if isinstance(cmd, bytes):
                    tx_in.script_sig.cmds[index] = cmd.hex()
            
            tx_in.script_sig = tx_in.script_sig.__dict__
            self.tx_ins[tx_index] = tx_in.__dict__

        """ Coinbase 때는 쓰였으나, 이후 transaction 추가하며 제거됨 (3.29) """
        # if self.is_coinbase:
        #     self.tx_ins[0].prev_tx = self.tx_ins[0].prev_tx.hex()
        #     self.tx_ins[0].script_sig.cmds[0] = little_endian_to_int(self.tx_ins[0].script_sig.cmds[0])
        #     self.tx_ins[0].script_sig = self.tx_ins[0].script_sig.__dict__
        # self.tx_ins[0] = self.tx_ins[0].__dict__

        """
        Convert Transaction Output to dict
        # If there are numbers we don`t need to do anything
        # If values is in bytes, convert it to hex
        # Loop through all the TxOut Objects and convert them into dict
        """
        
        for index, tx_out in enumerate(self.tx_outs):
            tx_out.script_pubkey.cmds[2] = tx_out.script_pubkey.cmds[2].hex()
            tx_out.script_pubkey = tx_out.script_pubkey.__dict__
            self.tx_outs[index] = tx_out.__dict__

        """ Coinbase 때는 쓰였으나, 이후 transaction 추가하며 제거됨 (3.29) """
        # self.tx_outs[0].script_pubkey.cmds[2] = self.tx_outs[0].script_pubkey.cmds[2].hex()
        # self.tx_outs[0].script_pubkey = self.tx_outs[0].script_pubkey.__dict__
        # self.tx_outs[0] = self.tx_outs[0].__dict__

        return self.__dict__

class TxIn:
    def __init__(self, prev_tx, prev_index, script_sig = None, sequence = 0xffffffff):
        self.prev_tx = prev_tx
        self.prev_index = prev_index
        
        if script_sig is None:
            self.script_sig = Script()
        else:
            self.script_sig = script_sig

        self.sequence = sequence
    
    def serialize (self):
        result = self.prev_tx[::-1]
        result += int_to_little_endian(self.prev_index,4)
        result += self.script_sig.serialize()
        result += int_to_little_endian(self.sequence,4)
        return result

class TxOut:
    def __init__(self, amount, script_pubkey):
        self.amount = amount
        self.script_pubkey = script_pubkey
    
    def serialize(self):
        result = int_to_little_endian(self.amount,8)
        result += self.script_pubkey.serialize()
        return result