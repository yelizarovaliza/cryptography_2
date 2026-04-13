import time
import sys
sys.path.insert(0, '.')

from strumok import Strumok256, Strumok512


def measure_throughput(cipher_class, key_size: int, label: str,
                       data_mb: float = 1.0, repeats: int = 3):
    """Вимірює пропускну здатність генерації гами"""
    data_bytes = int(data_mb * 1024 * 1024)
    key = bytes(range(key_size % 256)) * (key_size // 256 + 1)
    key = key[:key_size]
    iv = bytes(key_size)

    timings = []
    for _ in range(repeats):
        c = cipher_class()
        c.setup(key, iv)
        t0 = time.perf_counter()
        _ = c.keystream(data_bytes)
        t1 = time.perf_counter()
        timings.append(t1 - t0)

    best_t = min(timings)
    mb_s = data_mb / best_t
    return mb_s


def make_fast_keystream(nwords: int):
    from strumok_tables import (
        strumok_T0 as T0, strumok_T1 as T1, strumok_T2 as T2, strumok_T3 as T3,
        strumok_T4 as T4, strumok_T5 as T5, strumok_T6 as T6, strumok_T7 as T7,
        strumok_alpha_mul as AM, strumok_alphainv_mul as AIM
    )
    M = 0xFFFFFFFFFFFFFFFF

    def keystream_fast(key: bytes, iv: bytes, length: int) -> bytes:
        # Ініціалізація LFSR
        n = nwords
        key_w = [int.from_bytes(key[i*8:i*8+8], 'little') for i in range(n)]
        iv_w = [int.from_bytes(iv[i*8:i*8+8], 'little') for i in range(n)]

        s = [0] * 16
        for i in range(n):
            s[i] = key_w[i]
            s[i + n] = iv_w[i]
            if n == 4:
                s[i + 8] = key_w[i]
                s[i + 12] = iv_w[i]
        r1, r2 = 0, 0

        # Inline T
        def T(x):
            return (T0[x & 0xff] ^ T1[(x >> 8) & 0xff] ^
                    T2[(x >> 16) & 0xff] ^ T3[(x >> 24) & 0xff] ^
                    T4[(x >> 32) & 0xff] ^ T5[(x >> 40) & 0xff] ^
                    T6[(x >> 48) & 0xff] ^ T7[(x >> 56) & 0xff])

        def lfsr_step():
            new_s = ((s[0] << 8) ^ AM[s[0] >> 56]) & M ^ s[2] ^ ((s[15] >> 8) ^ AIM[s[15] & 0xff]) & M
            s.pop(0)
            s.append(new_s)

        # warmup 16 тактів
        for _ in range(16):
            z = ((r1 + s[0]) & M) ^ r2
            new_r2 = T(r1)
            new_r1 = T((r2 + s[2]) & M)
            r1, r2 = new_r1, new_r2
            s[15] ^= z
            lfsr_step()

        # Генерація гами
        nw = (length + 7) // 8
        out = []
        for _ in range(nw):
            z = ((r1 + s[0]) & M) ^ r2
            out.append(z)
            new_r2 = T(r1)
            new_r1 = T((r2 + s[2]) & M)
            r1, r2 = new_r1, new_r2
            new_s = ((s[0] << 8) ^ AM[s[0] >> 56]) & M ^ s[2] ^ ((s[15] >> 8) ^ AIM[s[15] & 0xff]) & M
            s.pop(0)
            s.append(new_s)

        return b''.join(w.to_bytes(8, 'little') for w in out)[:length]

    return keystream_fast


def measure_fast(nwords: int, key_size: int, data_mb: float = 1.0, repeats: int = 3):
    """Вимірює пропускну здатність оптимізованої"""
    data_bytes = int(data_mb * 1024 * 1024)
    key = bytes(range(key_size % 256)) * (key_size // 256 + 1)
    key = key[:key_size]
    iv = bytes(key_size)

    fn = make_fast_keystream(nwords)
    timings = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        _ = fn(key, iv, data_bytes)
        t1 = time.perf_counter()
        timings.append(t1 - t0)

    best_t = min(timings)
    mb_s = data_mb / best_t
    return mb_s


def print_table():
    SEP = "═" * 49
    DATA_MB = 10.0 #можна змінювати на 100 і тд для більш показовго результату але довго працює
    REPEATS = 3

    print(f"\n{SEP}")
    print(f"Обсяг даних: {DATA_MB} MB, повторень: {REPEATS}")
    print(SEP)

    print("\nВимірювання: ...")
    base256 = measure_throughput(Strumok256, 32, "Струмок-256", DATA_MB, REPEATS)
    base512 = measure_throughput(Strumok512, 64, "Струмок-512", DATA_MB, REPEATS)
    opt256 = measure_fast(4, 32, DATA_MB, REPEATS)
    opt512 = measure_fast(8, 64, DATA_MB, REPEATS)

    print(f"\n{SEP}")
    print("РЕЗУЛЬТАТИ")
    print(SEP)
    
    print(f"\n  {'Реалізація':<25} {'Струмок-256':>15} {'Струмок-512':>15} {'Прискорення (256/512)':>20}")
    print(f"  {'-'*25}  {'-'*15}  {'-'*15}  {'-'*20}")
    
    print(f"  {'Базова (MB/s)':<25}  {base256:>15.2f}  {base512:>15.2f}  {base256/base512:>19.2f}x")
    print(f"  {'Оптимізована (MB/s)':<25}  {opt256:>15.2f}  {opt512:>15.2f}  {opt256/opt512:>19.2f}x")
    print(f"  {'Прискорення (opt/base)':<25}  {opt256/base256:>14.1f}x  {opt512/base512:>14.1f}x  {'':>20}")
    
    print(f"\n{SEP}")


if __name__ == "__main__":
    print_table()