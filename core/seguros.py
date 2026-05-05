import numpy as np
import pandas as pd
from core.tablas import construir_lx_array

def generar_kpx(df, col_edad, col_qx, edad_inicio):
    df_filtrado = df[df[col_edad] >= edad_inicio].copy().reset_index(drop=True)
    qx = df_filtrado[col_qx].values
    px = 1.0 - qx
    
    kpx = np.cumprod(px)
    kpx = np.insert(kpx, 0, 1.0)[:-1]
    return kpx

def pbss_invalidez(
    x,
    y,
    sexo_conyuge,
    lx_inv,
    lx_hombres,
    lx_mujeres,
    b1,
    i=0.035
):

    if sexo_conyuge.lower() == "hombre":
        lx_cony = lx_hombres
    else:
        lx_cony = lx_mujeres

    edad_min = 15
    idx_x = x - edad_min
    idx_y = y

    max_k = min(len(lx_inv) - idx_x, len(lx_cony) - idx_y)
    k = np.arange(0, max_k)

    kpx_inv = lx_inv[idx_x + k] / lx_inv[idx_x]
    kpy = lx_cony[idx_y + k] / lx_cony[idx_y]

    v = 1 / (1 + i)
    vk = v ** k

    suma = np.sum((1 - kpx_inv) * kpy * vk)
    return suma

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

    # CLAVE PBSS

    factor_base = kpx_inv * vk

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

    K = len(factor_muerte)

    sumab1 = np.zeros(K)
    sumab2 = np.zeros(K)

    for k in range(K):

        dist = prob_combinada[k] if k in prob_combinada else np.array([1.0])

        s1 = 0.0
        s2 = 0.0

        for j in range(len(dist)):
            pj = dist[j]
            s1 += pj * b1_vals[j]
            s2 += pj * b2_vals[j]

        sumab1[k] = s1
        sumab2[k] = s2

    # =========================
    # 7. CÓNYUGE
    # =========================
    col_qx_cony = "Mujeres qx" if y["sexo"].lower() == "mujer" else "Hombres qx"

    kpy = generar_kpx(tabla_act, "Edad", col_qx_cony, y["edad"])

    # =========================
    # 8. COMBINACIÓN FINAL
    # =========================
    min_len = min(len(kpy), len(sumab1), len(factor_base))

    total = (
        kpy[:min_len] * sumab1[:min_len]
        + (1 - kpy[:min_len]) * sumab2[:min_len]
    )

    #  aquí está la magia
    suma = np.sum(total * factor_base[:min_len])

    # =========================
    # 9. FACTORES FINALES
    # =========================
    PBSS = 11.81 * suma

    FACBI = 1.00198213882427
    alpha = 0.02

    PNSS = FACBI * PBSS
    MCSS = PNSS * (1 + alpha)

    return MCSS

def calcular_monto_constitutivo(
    edad,
    conyuge,
    hijos,
    salarios_actualizados,
    tabla_inv,
    tabla_act,
    tabla_desercion
):

    # =========================
    # 1. PROMEDIO SALARIAL
    # =========================
    if len(salarios_actualizados) == 0:
        return 0.0

    salario_prom = sum(salarios_actualizados) / len(salarios_actualizados)

    # =========================
    # 2. FLAGS
    # =========================
    tiene_conyuge = conyuge is not None
    tiene_hijos = len(hijos) > 0

    # =========================
    # 3. CASO: CONYUGE + HIJOS
    # =========================
    if tiene_conyuge and tiene_hijos:

        return pbss_con_hijos(
            x=edad,
            y=conyuge,
            hijos=hijos,
            salario_prom=salario_prom,
            tabla_inv=tabla_inv,
            tabla_act=tabla_act,
            tabla_desercion=tabla_desercion
        )

    # =========================
    # 4. CASO: SOLO CONYUGE
    # =========================
    elif tiene_conyuge and not tiene_hijos:

        # ---- lx ----
        from core.tablas import construir_lx_array

        lx_inv = construir_lx_array(tabla_inv["qx"].values)
        lx_h = construir_lx_array(tabla_act["Hombres qx"].values)
        lx_m = construir_lx_array(tabla_act["Mujeres qx"].values)

        # ---- suma actuarial ----
        suma = pbss_invalidez(
            x=edad,
            y=conyuge["edad"],
            sexo_conyuge=conyuge["sexo"],
            lx_inv=lx_inv,
            lx_hombres=lx_h,
            lx_mujeres=lx_m,
            b1=1  # aquí solo queremos la suma
        )

        # =========================
        # CUANTÍA (tu definición)
        # =========================
        PMG = 4177.2

        cuant_diaria = 0.35 * 0.9 * salario_prom
        cuant_mensual = cuant_diaria * 365 / 12

        b1 = max(0.9 * PMG, cuant_mensual)

        # =========================
        # PBSS
        # =========================
        PBSS = b1 * 13 * suma

        # =========================
        # AJUSTES
        # =========================
        FACBI = 1.00198213882427
        alpha = 0.02

        PNSS = FACBI * PBSS
        MCSS = PNSS * (1 + alpha)

        return MCSS

    # =========================
    # 5. OTROS CASOS (no implementados)
    # =========================
    else:
        return 0.0