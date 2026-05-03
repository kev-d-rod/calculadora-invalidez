def factor_actualizacion(inpc_df, anio):
    """
    Calcula el factor de actualización para un año dado
    usando INPC (junio segunda quincena vs último disponible)
    """

    # Último índice disponible
    indice_actual = inpc_df["Indice"].iloc[-1]

    # Buscar junio segunda quincena del año
    periodo_objetivo = f"{anio}/06/02"

    fila = inpc_df[inpc_df["Periodos"] == periodo_objetivo]

    if fila.empty:
        raise ValueError(f"No se encontró INPC para {periodo_objetivo}")

    indice_pasado = fila["Indice"].values[0]

    return indice_actual / indice_pasado

def actualizar_salarios(inpc_df, salarios, anios):
    """
    Ajusta todos los salarios por inflación
    """

    salarios_actualizados = []

    for salario, anio in zip(salarios, anios):

        if salario == 0:
            continue  # ignoras ceros como ya definiste

        factor = factor_actualizacion(inpc_df, anio)

        salarios_actualizados.append(salario * factor)

    return salarios_actualizados
