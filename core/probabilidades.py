import numpy as np
import pandas as pd

def generar_kpx(df, col_edad, col_qx, edad_inicio):
    """
    Convierte la probabilidad de muerte (qx) en un vector de 
    probabilidad de supervivencia acumulada (kpx).
    """
    df_filtrado = df[df[col_edad] >= edad_inicio].copy().reset_index(drop=True)
    qx = df_filtrado[col_qx].values
    px = 1.0 - qx
    
    kpx = np.cumprod(px)
    kpx = np.insert(kpx, 0, 1.0)[:-1] 
    return kpx

def calcular_pbsi(edad_trabajador, salarios_actualizados, conyuge, hijos, edades_asc, sexos_asc, df_inv, df_act, df_desercion):
    # Promedio diario
    promedio_diario = sum(salarios_actualizados) / len(salarios_actualizados) if salarios_actualizados else 0.0

    # Flags de control
    flag_conyuge = 1 if conyuge is not None else 0
    flag_hijos = 1 if len(hijos) > 0 else 0
    flag_padres = 1 if len(edades_asc) > 0 else 0
    
    num_hijos = len(hijos)
    num_asc = len(edades_asc)

    # Parámetros base
    INC = 0.11
    FACBI = 1.001982139
    cbiv_pct = 0.35
    PMG = 4177.2
    i = 0.035
    v_escalar = 1 / (1 + i)

    # ---- DATOS DEL TRABAJADOR ----
    kpx_trabajador = generar_kpx(df_inv, 'edad', 'qx', edad_trabajador)
    k_array = np.arange(len(kpx_trabajador))
    vk_array = v_escalar ** k_array
    kpxvk_trabajador = kpx_trabajador * vk_array

    salario_mensual = promedio_diario * 30.4
    cbiv = promedio_diario * cbiv_pct
    aguinaldo = (1/12) * max(cbiv * (365/12), PMG)
    cuantia_mensual_base_gral = cbiv * 365 * (1/12)

    pbsi_final = 0.0

    # CASO 1: SIN CÓNYUGE, SIN HIJOS, SIN PADRES
    if flag_conyuge == 0 and flag_hijos == 0 and flag_padres == 0:
        cuantia_base = cbiv * (1 + 0.15 + 0.0)
        cuantia_mensual_base = cuantia_base * 365 * (1/12)
        cuantia_mensual = min(max(cuantia_mensual_base, PMG), salario_mensual)
        b1 = cuantia_mensual + aguinaldo

        sum_ax = np.sum(kpxvk_trabajador)
        ax12 = sum_ax - (11/24)
        pbsi_final = b1 * 12 * ax12 * (1 + INC)

    # CASO 2: CON CÓNYUGE, SIN HIJOS
    elif flag_conyuge == 1 and flag_hijos == 0:
        b1 = min(max(cbiv * (1 + 0.15 + 0.16) * 365 / 12, PMG), salario_mensual) + aguinaldo
        b2 = min(max(cbiv * (1 + 0.15 + 0.0) * 365 / 12, PMG), salario_mensual) + aguinaldo

        col_qx_conyuge = 'Mujeres qx' if conyuge['sexo'].lower() == 'mujer' else 'Hombres qx'
        kpy_conyuge = generar_kpx(df_act, 'Edad', col_qx_conyuge, conyuge['edad'])

        min_len = min(len(kpxvk_trabajador), len(kpy_conyuge))
        conv = kpxvk_trabajador[:min_len] * ((kpy_conyuge[:min_len] * b1) + ((1 - kpy_conyuge[:min_len]) * b2))
        pbsi_final = 11.81 * np.sum(conv) * FACBI

    # CASO 3: CON CÓNYUGE Y CON HIJOS
    elif flag_conyuge == 1 and flag_hijos == 1:
        aa = 0.16
        def b1_j(j): return max(cuantia_mensual_base_gral * (1 + 0.15 + (j * 0.10) + aa), PMG) + (1/12 * max(cuantia_mensual_base_gral, PMG))
        def b2_j(j): return max(cuantia_mensual_base_gral * (1 + 0.15 + (0 if j==0 else j*0.10) + (0 if j==0 else aa)), PMG) + (1/12 * max(cuantia_mensual_base_gral, PMG))

        b1_vals = [b1_j(j) for j in range(num_hijos + 1)]
        b2_vals = [b2_j(j) for j in range(num_hijos + 1)]

        vectores_kph_finales = []
        for hijo in hijos:
            col_qx_h = 'Mujeres qx' if hijo['sexo'].lower() == 'mujer' else 'Hombres qx'
            df_h = df_act[df_act['Edad'] >= hijo['edad']].copy().reset_index(drop=True)
            px_h = 1.0 - df_h[col_qx_h].values
            edades_futuras = df_h['Edad'].values
            
            kpx_vector = [1.0] 
            prob_acumulada = 1.0
            
            for u, edad_actual_k in enumerate(edades_futuras[:-1]):
                prob_acumulada *= px_h[u] 
                
                if edad_actual_k + 1 < 16:
                    kpx_vector.append(prob_acumulada)
                elif 16 <= edad_actual_k + 1 < 25:
                    try:
                        qx_d = df_desercion.loc[df_desercion['Edad'] == (edad_actual_k + 1), 'qx (d)'].values[0]
                        prob_acumulada *= (1 - qx_d)
                    except:
                        pass
                    kpx_vector.append(prob_acumulada)
                else:
                    kpx_vector.append(0.0)
            
            vectores_kph_finales.append(np.array(kpx_vector))

        max_k = max([len(v) for v in vectores_kph_finales])
        prob_combinada = {}
        for k_idx in range(max_k):
            pk_hijos = [v[k_idx] if k_idx < len(v) else 0.0 for v in vectores_kph_finales]
            dist_k = np.array([1.0])
            for p in pk_hijos: dist_k = np.convolve(dist_k, np.array([1 - p, p]))
            prob_combinada[k_idx] = dist_k

        j_vectores = {j: [prob_combinada[k][j] if j < len(prob_combinada[k]) else 0.0 for k in range(max_k)] for j in range(num_hijos + 1)}

        sumab1 = np.sum([(np.array(j_vectores[j]) * b1_vals[j]).round(0) for j in range(num_hijos + 1)], axis=0)
        sumab2 = np.sum([(np.array(j_vectores[j]) * b2_vals[j]).round(0) for j in range(num_hijos + 1)], axis=0)

        col_qx_conyuge = 'Mujeres qx' if conyuge['sexo'].lower() == 'mujer' else 'Hombres qx'
        kpy_conyuge = generar_kpx(df_act, 'Edad', col_qx_conyuge, conyuge['edad'])

        min_len = min(len(kpy_conyuge), len(sumab1))
        tot_kpysubsum = (kpy_conyuge[:min_len] * sumab1[:min_len]) + ((1 - kpy_conyuge[:min_len]) * sumab2[:min_len])

        min_len_final = min(len(tot_kpysubsum), len(kpxvk_trabajador))
        pbsi_final = 11.81 * np.sum(tot_kpysubsum[:min_len_final] * kpxvk_trabajador[:min_len_final]) * (1 + INC)

    # CASO 4: SIN CÓNYUGE, SIN HIJOS, CON PADRES
    elif flag_conyuge == 0 and flag_hijos == 0 and flag_padres == 1:
        aa = 0.16
        def b1_j(j): return max(cuantia_mensual_base_gral * (1 + 0.15 + (0 if j==0 else j*0.10+aa)), PMG) + (1/12 * max(cuantia_mensual_base_gral, PMG))
        b1_vals = [b1_j(j) for j in range(num_asc + 1)]

        vectores_padres = []
        # Aquí emparejamos las dos listas que vienen de Streamlit
        for edad_asc, sexo_asc in zip(edades_asc, sexos_asc):
            col_qx_asc = 'Mujeres qx' if sexo_asc.lower() == 'mujer' else 'Hombres qx'
            vectores_padres.append(generar_kpx(df_act, 'Edad', col_qx_asc, edad_asc))

        min_len = min(max([len(v) for v in vectores_padres]), len(kpxvk_trabajador))
        suma_total_padres = 0

        if num_asc == 1:
            kp_z1 = vectores_padres[0]
            for k_idx in range(min_len):
                p1 = kp_z1[k_idx] if k_idx < len(kp_z1) else 0.0
                suma_total_padres += kpxvk_trabajador[k_idx] * ((1 - p1)*b1_vals[0] + p1*b1_vals[1])
        elif num_asc == 2:
            kp_z1, kp_z2 = vectores_padres[0], vectores_padres[1]
            for k_idx in range(min_len):
                p1 = kp_z1[k_idx] if k_idx < len(kp_z1) else 0.0
                p2 = kp_z2[k_idx] if k_idx < len(kp_z2) else 0.0
                suma_total_padres += kpxvk_trabajador[k_idx] * (
                    (1 - p1)*(1 - p2)*b1_vals[0] + 
                    (p1*(1 - p2) + (1 - p1)*p2)*b1_vals[1] + 
                    (p1*p2)*b1_vals[2]
                )

        pbsi_final = 11.81 * suma_total_padres * (1 + INC)

    return pbsi_final
