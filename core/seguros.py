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
    salarios_actualizados,
    tabla_inv,
    tabla_act
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
    # cuantías
    # -------------------------
    PMG = 4177.2

    cuant_diaria = 0.35 * 0.9 * salario_prom
    cuant_mensual = cuant_diaria * 365 / 12

    b1 = max(0.9 * PMG, cuant_mensual)

    # -------------------------
    # PBSS (solo con cónyuge por ahora)
    # -------------------------
    if conyuge:
        suma = pbss_invalidez(
            x=edad,
            y=conyuge["edad"],
            sexo_conyuge=conyuge["sexo"],
            lx_inv=lx_inv,
            lx_hombres=lx_h,
            lx_mujeres=lx_m,
            b1=1
        )

        PBSS = b1 * 13 * suma

        FACBI = 1.00198213882427
        alpha = 0.02

        PNSS = FACBI * PBSS
        MCSS = PNSS * (1 + alpha)

        return MCSS

    return 0
