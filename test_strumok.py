import sys
sys.path.insert(0, '.')

from strumok import Strumok256, Strumok512, transform_T, alpha_mul, alphainv_mul

PASS = "✓"
FAIL = "✗"
SEP  = "─" * 49


def check(name: str, cond: bool, got=None, expected=None):
    if cond:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}")
        if got is not None:
            print(f"       Отримано:  {got}")
        if expected is not None:
            print(f"       Очікується:{expected}")
    return cond


def test_math_properties():
    print(f"\n{SEP}")
    print("1. Математичні властивості")
    print(SEP)
    ok = True

    # α та α^(-1) мають бути взаємно оберненими
    test_vals = [0x1, 0xff, 0x100, 0xabcdef1234567890,
                 0xffffffffffffffff, 0x8000000000000000]
    for v in test_vals:
        r1 = alphainv_mul(alpha_mul(v)) == v
        r2 = alpha_mul(alphainv_mul(v)) == v
        ok &= check(f"α⁻¹(α(0x{v:x})) = 0x{v:x}", r1)
        ok &= check(f"α(α⁻¹(0x{v:x})) = 0x{v:x}", r2)

    # T - детермінований
    ok &= check("T є детермінованою", transform_T(0x123456789abcdef0) ==
                transform_T(0x123456789abcdef0))
    return ok


def test_reproducibility_256():
    print(f"\n{SEP}")
    print("2. Відтворюваність Струмок-256")
    print(SEP)
    ok = True

    key = bytes(range(32))
    iv  = bytes(range(32, 64))

    c1 = Strumok256()
    c1.setup(key, iv)
    ks1 = c1.keystream(128)

    c2 = Strumok256()
    c2.setup(key, iv)
    ks2 = c2.keystream(128)

    ok &= check("Однаковий ключ/ІV дає однакову гаму", ks1 == ks2,
                got=ks1.hex(), expected=ks2.hex())
    return ok

def test_uniqueness():
    print(f"\n{SEP}")
    print("3. Унікальність гами")
    print(SEP)
    ok = True

    key1 = bytes(32)
    key2 = bytes([1]) + bytes(31)
    iv   = bytes(32)

    c1 = Strumok256()
    c1.setup(key1, iv)
    ks1 = c1.keystream(64)

    c2 = Strumok256()
    c2.setup(key2, iv)
    ks2 = c2.keystream(64)

    ok &= check("Різні ключі -> різні гами", ks1 != ks2,
                got=f"ks1={ks1[:8].hex()}...", expected="відрізняються")

    # Різний ІV
    iv2 = bytes([1]) + bytes(31)
    c3 = Strumok256()
    c3.setup(key1, iv2)
    ks3 = c3.keystream(64)
    ok &= check("Різні ІV -> різні гами", ks1 != ks3)
    return ok

def test_encrypt_decrypt():
    print(f"\n{SEP}")
    print("4. Симетрія encrypt/decrypt")
    print(SEP)
    ok = True

    key = bytes(range(32))
    iv  = bytes(32)
    pt  = b"DSTU Strumok cipher test message " * 3

    c = Strumok256()
    ct = c.encrypt(pt, key, iv)
    ok &= check("Шифротекст відрізняється від відкритого тексту", ct != pt)

    c2 = Strumok256()
    decrypted = c2.decrypt(ct, key, iv)
    ok &= check("decrypt(encrypt(m)) == m", decrypted == pt,
                got=decrypted[:20], expected=pt[:20])

    # Те саме для Струмок-512
    key512 = bytes(range(64))
    iv512  = bytes(64)
    c512 = Strumok512()
    ct512 = c512.encrypt(pt, key512, iv512)
    c512b = Strumok512()
    dec512 = c512b.decrypt(ct512, key512, iv512)
    ok &= check("Струмок-512: decrypt(encrypt(m)) == m", dec512 == pt)
    return ok

def test_256_vs_512():
    print(f"\n{SEP}")
    print("5. Струмок-256 проти Струмок-512")
    print(SEP)
    ok = True

    # Ключ 512 = два конкатенованих ключа 256
    key256 = bytes(range(32))
    iv256  = bytes(32)

    key512 = key256 + key256  # різна схема завантаження -> різний стан
    iv512  = iv256 + iv256

    c256 = Strumok256()
    c256.setup(key256, iv256)
    ks256 = c256.keystream(64)

    c512 = Strumok512()
    c512.setup(key512, iv512)
    ks512 = c512.keystream(64)

    ok &= check("256 та 512 генерують різні гами", ks256 != ks512)

    print(f"     Струмок-256: {ks256[:16].hex()}...")
    print(f"     Струмок-512: {ks512[:16].hex()}...")
    return ok


def test_reference_vectors():
    print(f"\n{SEP}")
    print("6. Референсні вектори (регресійні)")
    print(SEP)
    ok = True

    # Ці вектори виведені з реалізації та зафіксовані 
    # якщо будь-яка зміна алгоритму зламає їх, тест впаде
    VECTORS_256 = [
        {
            "key": bytes(32),
            "iv":  bytes(32),
            #перші 32 байти гами
            "ks":  "113a4d550dffb05580cb60a571e73d929c3eef410d00b9d91e97aa68cebb520e",
        },
        {
            "key": bytes(range(1, 33)),
            "iv":  bytes(32),
            "ks":  "fcf9782643f96d2ef5011a7a042513a7969865982d3d52c999c62131069dd6d4",
        },
        {
            "key": bytes(range(32)),
            "iv":  bytes(range(32, 64)),
            "ks":  None,  # Вивід і збереження при першому запуску
        },
    ]

    VECTORS_512 = [
        {
            "key": bytes(range(64)),
            "iv":  bytes(64),
            "ks":  "fe611955736b84b314e0212a788b4f9bc36f3a864e5f7c98ac4c09f94d48a7a2",
        },
    ]

    for i, v in enumerate(VECTORS_256):
        c = Strumok256()
        c.setup(v["key"], v["iv"])
        ks = c.keystream(32).hex()
        if v["ks"] is not None:
            ok &= check(f"Струмок-256 вектор #{i+1}", ks == v["ks"],
                        got=ks, expected=v["ks"])
        else:
            print(f"  (i)  Струмок-256 вектор #{i+1} (виведено): {ks}")

    for i, v in enumerate(VECTORS_512):
        c = Strumok512()
        c.setup(v["key"], v["iv"])
        ks = c.keystream(32).hex()
        if v["ks"] is not None:
            ok &= check(f"Струмок-512 вектор #{i+1}", ks == v["ks"],
                        got=ks, expected=v["ks"])

    return ok


def test_edge_cases():
    print(f"\n{SEP}")
    print("7. Edge cases")
    print(SEP)
    ok = True

    key = bytes(32)
    iv  = bytes(32)
    c = Strumok256()
    c.setup(key, iv)

    ks1 = c.keystream(1)
    ok &= check("Гама 1 байт", len(ks1) == 1)

    c.setup(key, iv)
    ks_fresh = c.keystream(32)
    c.setup(key, iv)
    ks_again  = c.keystream(32)
    ok &= check("Повторна ініціалізація дає той самий результат", ks_fresh == ks_again)

    #неправильний розмір ключа
    try:
        c.setup(bytes(16), bytes(32))
        ok &= check("Виключення для короткого ключа", False)
    except ValueError:
        ok &= check("Виключення для короткого ключа", True)

    return ok

# run all tests
def run_all():
    print("\n" + SEP)
    print("  ТЕСТУВАННЯ ШИФРУ СТРУМОК")
    print(SEP)

    results = [
        test_math_properties(),
        test_reproducibility_256(),
        test_uniqueness(),
        test_encrypt_decrypt(),
        test_256_vs_512(),
        test_reference_vectors(),
        test_edge_cases(),
    ]

    passed = sum(results)
    total  = len(results)

    print(SEP)
    if passed == total:
        print(f"Усі {total} груп тестів пройдено успішно!")
    else:
        print(f"Пройдено: {passed}/{total} груп тестів")
    print(SEP)


if __name__ == "__main__":
    run_all()
