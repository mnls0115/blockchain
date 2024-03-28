import sys
sys.path.append('/Users/user/Dropbox/2024Projects/Blockchain')
# sys.path.append('/Users/mnls0/Dropbox/2024Projects/Blockchain')

from Blockchain.Backend.core.EllepticCurve.EllepticCurve import Sha256Point
from Blockchain.Backend.util.util import hash160, hash256
from Blockchain.Backend.core.database.database import AccountDB
import secrets

class account:
    def createKeys(self):
        """엘립틱 곡선 위 한 점을 사용해서 Private key, Publikc Key 생성"""
        Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
        Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
        G = Sha256Point (Gx, Gy)

        self.privateKey = secrets.randbits(256)

        unCompressesPublicKey = self.privateKey * G
        xpoint = unCompressesPublicKey.x
        ypoint = unCompressesPublicKey.y

        """y점의 짝수/홀수 여부와 x점을 통해 compress Key를 만들게 됨 > 공개키 크기를 줄임"""
        if ypoint.num % 2 == 0:
            compressKey = b'\x02' + xpoint.num.to_bytes(32, 'big')
        else:
            compressKey = b'\x03' + xpoint.num.to_bytes(32, 'big')
        
        """Compress Public Key를 RIPEMD160 Hashing 알고리즘 넣음"""
        hsh160 = hash160(compressKey)

        """ 메인넷 prefix 및 newAdress """
        main_prefix = b'\x00'
        newAddress = main_prefix + hsh160

        """ 체크섬 = 오류 없는지 확인하기 위해 붙임 """
        checksum = hash256(newAddress)[:4]
        newAddress = newAddress + checksum
        BASE58_ALPHABET = '123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

        """ 앞쪽 0 제거 """
        count = 0
        for c in newAddress:
            if c == 0:
                count += 1
            else:
                break
        
        """ new Adress를 BASE58에 넣는 과정을 반복해서 Public Adress 를 얻음 """
        num = int.from_bytes(newAddress, 'big')
        prefix = '1' * count
        result = ''
        while num > 0:
            num, mod = divmod(num, 58)
            result = BASE58_ALPHABET[mod] + result

        self.PublicAddress = prefix + result

        print (f'Private Key {self.privateKey}')
        print (f'Public Key {self.PublicAddress}')

if __name__ == '__main__':
    acct = account()
    acct.createKeys()
    AccountDB().write([acct.__dict__])