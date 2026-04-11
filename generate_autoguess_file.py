def generate_autoguess_file(rounds: int = 11, filename: str = "strumok512_autoguess.txt"):
    """Генерує файл зв'язків для Autoguess"""
    
    lines = [
        "# Autoguess input file for Strumok-512",
        f"# {rounds} rounds of keystream generation",
        "",
        "# Variables: s_i_j (LFSR, i=round, j=0..15), r1_i, r2_i (FSM), z_i (keystream)",
        "# Operations: T(x), alpha(x), alphainv(x), add(x,y) (mod 2^64)",
        "",
        "algebraic_relations:",
        "  s_i_j, r1_i, r2_i, z_i in GF(2^64)",
        "",
        "connection_relations:",
    ]
    
    # Початковий стан
    for j in range(16):
        lines.append(f"  s_0_{j} unknown")
    lines.append("  r1_0 unknown")
    lines.append("  r2_0 unknown")
    lines.append("")
    
    for i in range(rounds):
        # Вихід гами
        lines.append(f"  z_{i} = (r1_{i} + s_{i}_0) ^ r2_{i}")
        
        # Оновлення FSM
        lines.append(f"  r2_{i+1} = T(r1_{i})")
        lines.append(f"  r1_{i+1} = T(r2_{i} + s_{i}_2)")
        
        # Оновлення LFSR
        lines.append(f"  s_{i+1}_15 = alpha(s_{i}_0) ^ s_{i}_2 ^ alphainv(s_{i}_15) ^ z_{i}")
        
        # Зсув LFSR
        for j in range(15):
            lines.append(f"  s_{i+1}_{j} = s_{i}_{j+1}")
        
        lines.append("")
    
    # Відома гама
    lines.append("known:")
    for i in range(rounds):
        lines.append(f"  z_{i}")
    
    lines.append("")
    lines.append("target:")
    lines.append("  s_0_0, s_0_1, s_0_2, s_0_3, s_0_4, s_0_5, s_0_6, s_0_7,")
    lines.append("  s_0_8, s_0_9, s_0_10, s_0_11, s_0_12, s_0_13, s_0_14, s_0_15,")
    lines.append("  r1_0, r2_0")
    lines.append("")
    lines.append("end")
    
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Файл '{filename}' створено з {rounds} тактами")
    return filename


def generate_compact_file(rounds: int = 11, filename: str = "strumok512_compact.txt"):
    """Компактна версія без коментарів."""
    
    lines = [
        "algebraic_relations:",
        "  s_i_j, r1_i, r2_i, z_i in GF(2^64)",
        "",
        "connection_relations:",
    ]
    
    # Початковий стан (16 слів LFSR + 2 регістри FSM)
    lines.extend(f"  s_0_{j} unknown" for j in range(16))
    lines.extend(["  r1_0 unknown", "  r2_0 unknown", ""])
    
    for i in range(rounds):
        lines.append(f"  z_{i} = (r1_{i} + s_{i}_0) ^ r2_{i}")
        lines.append(f"  r2_{i+1} = T(r1_{i})")
        lines.append(f"  r1_{i+1} = T(r2_{i} + s_{i}_2)")
        lines.append(f"  s_{i+1}_15 = alpha(s_{i}_0) ^ s_{i}_2 ^ alphainv(s_{i}_15) ^ z_{i}")
        lines.extend(f"  s_{i+1}_{j} = s_{i}_{j+1}" for j in range(15))
        lines.append("")
    
    lines.extend(["known:", *[f"  z_{i}" for i in range(rounds)], ""])
    lines.append("target:")
    lines.append("  " + ", ".join(f"s_0_{j}" for j in range(16)) + ", r1_0, r2_0")
    lines.append("end")
    
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"файл '{filename}' створено")
    return filename


if __name__ == "__main__":
    print("ГЕНЕРАЦІЯ ФАЙЛУ ДЛЯ AUTOGUESS")
    
    generate_autoguess_file(rounds=11)
    generate_compact_file(rounds=11)
    