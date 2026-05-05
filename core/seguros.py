import numpy as np
from core.tablas import construir_lx_array


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
    elif sexo_conyuge.lower() == "mujer":
        lx_cony = lx_mujeres
    else:
        raise ValueError("sexo_conyuge debe ser 'hombre' o 'mujer'")

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

#  FUNCIÓN PRINCIPAL
def calcular_monto_constitutivo(
    edad,
    conyuge,
    hijos,
    salarios_actualizados,
    tabla_inv,
    tabla_act,
    tabla_desercion
):

    
    # -------------------------
    # lx
    # -------------------------
    lx_inv = construir_lx_array(tabla_inv["qx"].values)
    lx_h = construir_lx_array(tabla_act["Hombres qx"].values)
    lx_m = construir_lx_array(tabla_act["Mujeres qx"].values)

    # -------------------------
    # salarios
    # -------------------------
    salario_prom = sum(salarios_actualizados) / len(salarios_actualizados)

    # -------------------------
    # CASO 1: cónyuge + hijos
    # -------------------------
    if conyuge and len(hijos) > 0:

        return pbss_con_hijos(
            x=edad,
            y=conyuge,
            hijos=hijos,
            salario_prom=salario_prom,
            tabla_inv=tabla_inv,
            tabla_act=tabla_act,
            tabla_desercion=tabla_desercion
        )

    # -------------------------
    # CASO 2: solo cónyuge
    # -------------------------
    elif conyuge and len(hijos) == 0:

        return pbss_invalidez(
            x=edad,
            y=conyuge["edad"],
            sexo_conyuge=conyuge["sexo"],
            lx_inv=lx_inv,
            lx_hombres=lx_h,
            lx_mujeres=lx_m,
            b1=1
            # aquí tus lx como ya los tienes
        )

    return 0
# -------------------------
# Probabilidad hijo activo
# -------------------------
def prob_hijo_activo(k, hijo, lx_h, lx_m, edades_act, tabla_desercion):


    edad_hijo = hijo["edad"]
    sexo = hijo["sexo"].lower()

    edad_k = edad_hijo + k

    # Mayor a 25 → ya no es beneficiario
    if edad_k > 25:
        return 0.0

    # índice base
    idx_0 = np.where(edades_act == edad_hijo)[0][0]
    idx_k = idx_0 + k

    if sexo == "hombre":
        lx = lx_h
    else:
        lx = lx_m

    if idx_k >= len(lx):
        return 0.0
    kp = lx[idx_k] / lx[idx_0]

    # menor de 16 → solo supervivencia
    if edad_k < 16:
        return kp

    # entre 16 y 25 → incluye deserción
    qd = tabla_desercion.loc[
        tabla_desercion["Edad"] == edad_k, "qx (d)"
    ].values

    qd = qd[0] if len(qd) > 0 else 0

    return kp * (1 - qd)


# -------------------------
# Convolución hijos
# -------------------------
def distribucion_hijos_activos(k, hijos, lx_h, lx_m, edades_act, tabla_desercion):

    # empezamos con P(0 hijos activos) = 1
    dist = np.array([1.0])

    for hijo in hijos:
        p = prob_hijo_activo(
            k,
            hijo,
            lx_h,
            lx_m,
            edades_act,
            tabla_desercion
        )

        # convolución Bernoulli: [1-p, p]
        dist = np.convolve(dist, [1 - p, p])

    return dist  # tamaño = n+1


# -------------------------
# Funciones b1 y b2
# -------------------------
def b1_func(j, cuant_mens):
    return min(0.9 + j * 0.2, 1) * cuant_mens


def b2_func(j, cuant_mens):
    return min(j * 0.3, 1) * cuant_mens


# -------------------------
# PBSS COMPLETA
# -------------------------
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

    # -------------------------
    # lx
    # -------------------------
    edades_inv = tabla_inv["edad"].values
    qx_inv = tabla_inv["qx"].values

    edades_act = tabla_act["Edad"].values
    qx_h = tabla_act["Hombres qx"].values
    qx_m = tabla_act["Mujeres qx"].values

    lx_inv = construir_lx_array(qx_inv)
    lx_h = construir_lx_array(qx_h)
    lx_m = construir_lx_array(qx_m)

    # -------------------------
    # lx cónyuge
    # -------------------------
    if y["sexo"].lower() == "hombre":
        lx_cony = lx_h
    else:
        lx_cony = lx_m

    # índices
    idx_x = np.where(edades_inv == x)[0][0]
    idx_y = np.where(edades_act == y["edad"])[0][0]

    # -------------------------
    # cuantía
    # -------------------------
    cbiv = salario_prom * 0.35
    cbiv_mens = cbiv * (365 / 12)

    PMG = 4177.2
    cuant_mens = max(cbiv_mens, PMG)

    # -------------------------
    # constantes
    # -------------------------
    v = 1 / (1 + i)
    a12 = 11.81

    # máximo k
    max_k = min(len(lx_inv) - idx_x, len(lx_cony) - idx_y)

    suma = 0.0

    for k in range(max_k):

        # probabilidades base
        kpx_inv = lx_inv[idx_x + k] / lx_inv[idx_x]
        kpy = lx_cony[idx_y + k] / lx_cony[idx_y]

        # distribución de hijos
        dist = distribucion_hijos_activos(
            k,
            hijos,
            lx_h,
            lx_m,
            edades_act,
            tabla_desercion
        )

        # suma sobre j
        suma_b1 = 0.0
        suma_b2 = 0.0

        for j in range(len(dist)):
            pj = dist[j]
            suma_b1 += pj * b1_func(j, cuant_mens)
            suma_b2 += pj * b2_func(j, cuant_mens)

        termino = (
            (1 - kpx_inv)
            * (v ** k)
            * (
                kpy * suma_b1
                + (1 - kpy) * suma_b2
            )
        )

        suma += termino

    return b1_func(0, cuant_mens)
    #(13 / 12) * a12 * suma
