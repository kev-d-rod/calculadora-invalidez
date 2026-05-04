def construir_lx_array(qx, l0=1_000_000):
    import numpy as np

    lx = np.zeros(len(qx))
    lx[0] = l0

    for i in range(len(qx) - 1):
        lx[i+1] = lx[i] * (1 - qx[i])

    return lx