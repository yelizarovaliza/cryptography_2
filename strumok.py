from strumok_tables import (
    strumok_T0, strumok_T1, strumok_T2, strumok_T3,
    strumok_T4, strumok_T5, strumok_T6, strumok_T7,
    strumok_alpha_mul, strumok_alphainv_mul
)

MASK64 = 0xFFFFFFFFFFFFFFFF


def transform_T(x: int) -> int:
    return (strumok_T0[x & 0xff] ^
            strumok_T1[(x >> 8) & 0xff] ^
            strumok_T2[(x >> 16) & 0xff] ^
            strumok_T3[(x >> 24) & 0xff] ^
            strumok_T4[(x >> 32) & 0xff] ^
            strumok_T5[(x >> 40) & 0xff] ^
            strumok_T6[(x >> 48) & 0xff] ^
            strumok_T7[(x >> 56) & 0xff])


def alpha_mul(x: int) -> int:
    """ Множення на α в GF(2^64)
    Відповідає зсуву байтів вліво + XOR з попередньо обчисленим значенням"""
    return (((x << 8) ^ strumok_alpha_mul[x >> 56]) & MASK64)


def alphainv_mul(x: int) -> int:
    """Обернена операція до alpha_mul"""
    return (((x >> 8) ^ strumok_alphainv_mul[x & 0xff]) & MASK64)


def add64(a: int, b: int) -> int:
    return (a + b) & MASK64


def to_uint64_list(data: bytes, count: int) -> list:
    """Перетворення байтів у список 64-бітних слів"""
    result = []
    for i in range(count):
        word = int.from_bytes(data[i*8:(i+1)*8], 'little')
        result.append(word)
    return result


def from_uint64_list(words: list) -> bytes:
    """Перетворення списку 64-бітних слів у байти"""
    return b''.join(w.to_bytes(8, 'little') for w in words)


class Strumok:
    def __init__(self, nwords: int):
        self.nwords = nwords
        self.s = [0] * 16
        self.r1 = 0
        self.r2 = 0

    def _key_setup(self, key_words: list, iv_words: list):
        n = self.nwords
        for i in range(n):
            self.s[i] = key_words[i]
            self.s[i + n] = iv_words[i]
            if n == 4:
                self.s[i + 8] = key_words[i]
                self.s[i + 12] = iv_words[i]
        self.r1 = 0
        self.r2 = 0

    def _fsm_output(self) -> int:
        return add64(transform_T(add64(self.r1, self.s[0])), self.r2)

    def _fsm_update(self):
        """
        Оновлення регістрів FSM:
          r2 ← T(r1)
          r1 ← T(add(r2, s[2]))  (змішування зі станом LFSR)
        """
        new_r2 = transform_T(self.r1)
        new_r1 = transform_T(add64(self.r2, self.s[2]))
        self.r1 = new_r1
        self.r2 = new_r2

    def _lfsr_update(self):
        new_s = (alpha_mul(self.s[0]) ^
                 self.s[2] ^
                 alphainv_mul(self.s[15]))
        self.s = self.s[1:] + [new_s]

    def _warmup(self, rounds: int = 16):
        for _ in range(rounds):
            z = self._fsm_output()
            self._fsm_update()
            #під час ініціалізації вихід подається назад у LFSR (повне перемішування)
            self.s[15] ^= z
            self._lfsr_update()

    def _clock(self) -> int:
        """Один такт генератора: повертає 64-бітне слово гами"""
        z = self._fsm_output()
        self._fsm_update()
        self._lfsr_update()
        return z

    def setup(self, key: bytes, iv: bytes):
        """Ініціалізація шифру ключем та ІV"""
        n = self.nwords
        expected_len = n * 8
        if len(key) != expected_len:
            raise ValueError(f"Ключ має бути {expected_len} байт")
        if len(iv) != expected_len:
            raise ValueError(f"ІV має бути {expected_len} байт")

        key_words = to_uint64_list(key, n)
        iv_words = to_uint64_list(iv, n)
        self._key_setup(key_words, iv_words)
        self._warmup(16)

    def keystream(self, length: int) -> bytes:
        """Генерація гами заданої довжини"""
        nwords = (length + 7) // 8
        result = []
        for _ in range(nwords):
            result.append(self._clock())
        return from_uint64_list(result)[:length]

    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """encryption: гама XOR відкритий текст"""
        self.setup(key, iv)
        ks = self.keystream(len(plaintext))
        return bytes(a ^ b for a, b in zip(plaintext, ks))

    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        return self.encrypt(ciphertext, key, iv)


class Strumok256(Strumok):
    def __init__(self):
        super().__init__(nwords=4)


class Strumok512(Strumok):
    def __init__(self):
        super().__init__(nwords=8)
