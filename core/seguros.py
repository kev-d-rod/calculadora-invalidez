import numpy as np

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
    """
    Calcula la PBSS completa
    """

    # Selección de tabla del cónyuge
    if sexo_conyuge.lower() == "hombre":
        lx_cony = lx_hombres
    elif sexo_conyuge.lower() == "mujer":
        lx_cony = lx_mujeres
    else:
        raise ValueError("sexo_conyuge debe ser 'hombre' o 'mujer'")

    # Índices (edad mínima 15)
    edad_min = 15
    idx_x = x - edad_min
    idx_y = y - edad_min

    # Máximo k
    max_k = min(len(lx_inv) - idx_x, len(lx_cony) - idx_y)

    k = np.arange(0, max_k)

    # Probabilidades
    kpx_inv = lx_inv[idx_x + k] / lx_inv[idx_x]
    kpy = lx_cony[idx_y + k] / lx_cony[idx_y]

    # Descuento
    v = 1 / (1 + i)
    vk = v ** k

    # Suma actuarial
    suma = np.sum((1 - kpx_inv) * kpy * vk)

    # PBSS final
    return b1 * 13 * suma
