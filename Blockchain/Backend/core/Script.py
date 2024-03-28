from Blockchain.Backend.util.util import int_to_little_endian, endcode_variant

class Script:
    def __init__(self, cmds = None):
        if cmds is None:
            self.cmds = []
        else:
            self.cmds = cmds
    
    def serialize(self):
        # initialize what we`ll send back
        result = b''
        # Go through each cmd
        for cmd in self.cmds:
            # if the cmd is an integer, it`s an opcode
            if type(cmd) == int:
                result += int_to_little_endian(cmd,1)
            else:
                # Otherwise this is and element
                # get length in bytes
                length = len(cmd)
                if length < 75:
                    result += int_to_little_endian(length,1)
                elif length > 75 and length < 0x100:
                    result += int_to_little_endian(76,1)
                    result += int_to_little_endian(length,1)
                elif length >= 0x100 and length <= 520:
                    result += int_to_little_endian(77,1)
                    result += int_to_little_endian(length,2)
                else:
                    raise ValueError('Too long cmd')
                
                result += cmd
        # Get length of the whole thing
        total = len(result)
        # encode variant the total length of the result and prepend
        return endcode_variant(total) + result

    @classmethod
    def p2pkh_script(cls, h160):
        """Takes a hash160 and returns the p2pkh ScriptPubKey"""
        return Script([0x76, 0xa9, h160, 0x88, 0xac])
    
