import numpy as np
import pandas as pd

def generar_kpx(df, col_edad, col_qx, edad_inicio):
    df_filtrado = df[df[col_edad] >= edad_inicio].copy().reset_index(drop=True)
    qx = df_filtrado[col_qx].values
    px = 1.0 - qx
    
    kpx = np.cumprod(px)
    kpx = np.insert(kpx, 0, 1.0)[:-1]
    return kpx

def pbss_con_hijos(
    x,
    y,
    hijos,
    salario_prom,
    tabla_inv,
    tabla_act,
    tabla_desercion,
    i=0.035
):

    # =========================
    # 1. SUPERVIVENCIA INVÁLIDO
    # =========================
    qx_inv = tabla_inv["qx"].values
    edades_inv = tabla_inv["edad"].values

    px_inv = 1 - qx_inv
    kpx_inv = np.cumprod(px_inv)
    kpx_inv = np.insert(kpx_inv, 0, 1.0)[:-1]

    idx_x = np.where(edades_inv == x)[0][0]
    kpx_inv = kpx_inv[idx_x:]

    k_array = np.arange(len(kpx_inv))
    v = 1 / (1 + i)
    vk = v ** k_array

    # 🔥 CLAVE PBSS
    factor_muerte = (1 - kpx_inv) * vk

    # =========================
    # 2. CUANTÍA
    # =========================
    cbiv = salario_prom * 0.35
    cbiv_mens = cbiv * (365 / 12)

    PMG = 4177.2
    cuant_mens = max(cbiv_mens, PMG)

    # =========================
    # 3. b1(j) y b2(j)
    # =========================
    def b1_j(j):
        return min(0.9 + j * 0.2, 1) * cuant_mens

    def b2_j(j):
        return min(j * 0.3, 1) * cuant_mens

    num_hijos = len(hijos)

    b1_vals = [b1_j(j) for j in range(num_hijos + 1)]
    b2_vals = [b2_j(j) for j in range(num_hijos + 1)]

    # =========================
    # 4. VECTORES HIJOS (IGUAL QUE MCSI)
    # =========================
    vectores_kph = []

    for hijo in hijos:
        col_qx = "Mujeres qx" if hijo["sexo"].lower() == "mujer" else "Hombres qx"

        df_h = tabla_act[tabla_act["Edad"] >= hijo["edad"]].copy().reset_index(drop=True)

        px = 1 - df_h[col_qx].values
        edades = df_h["Edad"].values

        kpx_vector = [1.0]
        prob_acum = 1.0

        for u, edad_actual in enumerate(edades[:-1]):
            prob_acum *= px[u]

            if edad_actual + 1 < 16:
                kpx_vector.append(prob_acum)

            elif 16 <= edad_actual + 1 < 25:
                try:
                    qd = tabla_desercion.loc[
                        tabla_desercion["Edad"] == (edad_actual + 1),
                        "qx (d)"
                    ].values[0]
                    prob_acum *= (1 - qd)
                except:
                    pass
                kpx_vector.append(prob_acum)

            else:
                kpx_vector.append(0.0)

        vectores_kph.append(np.array(kpx_vector))

    # =========================
    # 5. CONVOLUCIONES (IGUAL QUE MCSI)
    # =========================
    max_k = max(len(v) for v in vectores_kph)

    prob_combinada = {}

    for k in range(max_k):
        pk = [v[k] if k < len(v) else 0.0 for v in vectores_kph]

        dist = np.array([1.0])
        for p in pk:
            dist = np.convolve(dist, np.array([1 - p, p]))

        prob_combinada[k] = dist

    # =========================
    # 6. ARMAR SUMAS b1 y b2
    # =========================
    j_vectores = {
        j: [
            prob_combinada[k][j] if j < len(prob_combinada[k]) else 0.0
            for k in range(max_k)
        ]
        for j in range(num_hijos + 1)
    }

    sumab1 = np.sum([
        np.array(j_vectores[j]) * b1_vals[j]
        for j in range(num_hijos + 1)
    ], axis=0)

    sumab2 = np.sum([
        np.array(j_vectores[j]) * b2_vals[j]
        for j in range(num_hijos + 1)
    ], axis=0)

    # =========================
    # 7. CÓNYUGE
    # =========================
    col_qx_cony = "Mujeres qx" if y["sexo"].lower() == "mujer" else "Hombres qx"

    kpy = generar_kpx(tabla_act, "Edad", col_qx_cony, y["edad"])

    # =========================
    # 8. COMBINACIÓN FINAL
    # =========================
    min_len = min(len(kpy), len(sumab1), len(factor_muerte))

    total = (
        kpy[:min_len] * sumab1[:min_len]
        + (1 - kpy[:min_len]) * sumab2[:min_len]
    )

    # 🔥 aquí está la magia
    suma = np.sum(total * factor_muerte[:min_len])

    # =========================
    # 9. FACTORES FINALES
    # =========================
    PBSS = 11.81 * suma

    FACBI = 1.00198213882427
    alpha = 0.02

    PNSS = FACBI * PBSS
    MCSS = PNSS * (1 + alpha)

    return MCSS