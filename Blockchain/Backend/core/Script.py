from Blockchain.Backend.util.util import little_endian_to_int, int_to_little_endian, endcode_variant, read_variant
from Blockchain.Backend.core.EllepticCurve.op import OP_CODE_FUNCTION

class Script:
    def __init__(self, cmds = None):
        if cmds is None:
            self.cmds = []
        else:
            self.cmds = cmds

    def __add__(self, other):
        return Script(self.cmds + other.cmds)
    
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
    def parse(cls, s):
        # get the length of the entire field
        length = read_variant(s)
        # initialize the cmds array
        cmds = []
        # initialize the number of bytes we`ve read to 0
        count = 0
        # loop until we`ve read length bytes
        while count < length:
            current = s.read(1)
            count += 1
            current_byte = current[0]
            if current_byte >= 1 and current_byte <= 75:
                n = current_byte
                cmds.append(s.read(n))
                count += n
            elif current_byte == 76:
                data_length = little_endian_to_int(s.read(1))
                cmds.append(s.read(data_length))
                count += data_length +1
            elif current_byte == 77:
                data_length = little_endian_to_int(s.read(2))
                cmds.append(s.read(data_length))
                count += data_length + 2
            else:
                op_code = current_byte
                cmds.append(op_code)
        if count != length:
            raise SyntaxError ('parsing script failed')
        return cls(cmds)
    
    def evaluate(self, z):
        cmds = self.cmds[:]
        stack = []

        while len(cmds) > 0:
            cmd = cmds.pop(0)

            if type(cmd) == int:
                operation = OP_CODE_FUNCTION[cmd]
                
                if cmd == 172:
                    if not operation(stack, z):
                        print(f"Error in signiture verification")
                        return False
                    
                elif not operation(stack):
                    print(f"Error in signiture verification")
                    return False

            else:
                stack.append(cmd)
        
        return True
            

    @classmethod
    def p2pkh_script(cls, h160):
        """Takes a hash160 and returns the p2pkh ScriptPubKey"""
        return Script([0x76, 0xa9, h160, 0x88, 0xac])
    
