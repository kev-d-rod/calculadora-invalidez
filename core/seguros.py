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

def pbss_asc(
    x,
    edades_asc,
    sexos_asc,
    salario_prom,
    tabla_inv,
    tabla_act,
    i=0.035
):
    """
    Calcula el Monto Constitutivo del Seguro de Sobrevivencia (MCSS)
    para un inválido con ascendientes (padres).
    
    Fórmula:
    PBSS_{x,z1,z2} = Σ A^{(IV)}_{x,zj}
    A^{(IV)}_{x,z} = 0.2 × 13 × Σ_{k} (1 - kpx_inv) × V^k × kp_z
    
    PNSS = CB_IV_mensual × FACBI × PBSS
    MCSS = PNSS × (1 + α)
    
    Parámetros:
    - x: edad del inválido
    - edades_asc: lista de edades de los ascendientes
    - sexos_asc: lista de sexos ('hombre' o 'mujer')
    - salario_prom: salario promedio del inválido
    - tabla_inv: DataFrame con columnas 'edad' y 'qx' para inválidos
    - tabla_act: DataFrame con columnas 'Edad', 'Hombres qx', 'Mujeres qx'
    - i: tasa de interés (default 3.5%)
    """
    
    # ============================================================
    # 1. CALCULAR CBIV MENSUAL
    # ============================================================
    cbiv_diario = salario_prom * 0.35
    cbiv_mensual = cbiv_diario * (365 / 12)
    
    # ============================================================
    # 2. VECTOR DE SUPERVIVENCIA DEL INVÁLIDO
    # ============================================================
    qx_inv = tabla_inv["qx"].values
    edad_inv = tabla_inv["edad"].values
    
    px_inv = 1.0 - qx_inv
    kpx_inv = np.cumprod(px_inv)
    kpx_inv = np.insert(kpx_inv, 0, 1.0)[:-1]  # kpx[0]=1, kpx[1]=1px, ...
    
    # Encontrar el índice correspondiente a la edad x
    idx_x = np.where(edad_inv == x)[0]
    if len(idx_x) == 0:
        raise ValueError(f"Edad {x} no encontrada en tabla de inválidos")
    idx_x = idx_x[0]
    
    # kpx_inv desde edad x en adelante
    kpx_inv_x = kpx_inv[idx_x:]
    
    # Probabilidad de que el inválido HAYA FALLECIDO antes de k
    prob_fallecimiento = 1.0 - kpx_inv_x
    
    # ============================================================
    # 3. FACTOR DE DESCUENTO V^k
    # ============================================================
    max_k = len(prob_fallecimiento)
    k_values = np.arange(max_k)
    v = 1.0 / (1.0 + i)
    Vk = v ** k_values
    
    # ============================================================
    # 4. CALCULAR PBSS PARA CADA ASCENDIENTE Y SUMAR
    # ============================================================
    suma_total_actuarial = 0.0
    
    for edad_asc, sexo_asc in zip(edades_asc, sexos_asc):
        # Seleccionar columna de mortalidad según sexo
        if sexo_asc.lower() == "mujer":
            col_qx = "Mujeres qx"
        elif sexo_asc.lower() == "hombre":
            col_qx = "Hombres qx"
        else:
            raise ValueError(f"Sexo no reconocido: {sexo_asc}")
        
        # Generar vector de supervivencia del ascendiente
        kp_asc = generar_kpx(tabla_act, "Edad", col_qx, edad_asc)
        
        if len(kp_asc) == 0:
            continue  # Si no hay datos, asumimos que no hay beneficio
        
        # Longitud mínima entre los vectores
        min_len = min(len(prob_fallecimiento), len(kp_asc))
        
        # Suma actuarial: Σ (1 - kpx_inv) × V^k × kp_asc
        suma_actuarial = np.sum(
            prob_fallecimiento[:min_len] * 
            Vk[:min_len] * 
            kp_asc[:min_len]
        )
        
        suma_total_actuarial += suma_actuarial
    
    # ============================================================
    # 5. CALCULAR PBSS
    # ============================================================
    # 0.2 = 20% del salario
    # 13 = 13 pagos al año (12 mensualidades + aguinaldo)
    PBSS = 0.2 * 13 * suma_total_actuarial
    
    # ============================================================
    # 6. CALCULAR PNSS
    # ============================================================
    FACBI = 1.00198213882427
    PNSS = cbiv_mensual * FACBI * PBSS
    
    # ============================================================
    # 7. CALCULAR MCSS
    # ============================================================
    alpha = 0.02
    MCSS = PNSS * (1.0 + alpha)
    
    return MCSS

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

    K = len(factor_base)

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
    tabla_desercion,
    edades_asc,
    sexos_asc,
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
    # 5.
    elif (not conyuge) and len(hijos) == 0 and len(edades_asc) > 0:

        return pbss_asc(
            x=edad,
            edades_asc=edades_asc,
            sexos_asc=sexos_asc,
            salario_prom=salario_prom,
            tabla_inv=tabla_inv,
            tabla_act=tabla_act
        )
        # =========================
    else:
        return 0.0