def b1_j(j):
        b1_j = max(cuantia_mensual_base * (1 + 0.15 + (j * 0.10) + aa), PMG) + (1/12 * max(cuantia_mensual_base, PMG))
        return b1_j

    def b2_j(j):
        if j == 0:
            b2_j = max(cuantia_mensual_base * (1 + 0.15), PMG) + (1/12 * max(cuantia_mensual_base, PMG))
        if j != 0:
            b2_j = max(cuantia_mensual_base * (1 + (j * 0.10) + aa), PMG) + (1/12 * max(cuantia_mensual_base, PMG))
        return b2_j

    b1 = []
    for j in range(n_hijos + 1):
        b1.append(b1_j(j))
        print(f"j={j}, b1={b1[j]:.2f}")

    b2 = []
    for j in range(n_hijos + 1):
        b2.append(b2_j(j))
        print(f"j={j}, b2={b2[j]:.2f}")