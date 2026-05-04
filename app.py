#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
from core.inflacion import actualizar_salarios
from core.seguros import calcular_monto_constitutivo
from core.probabilidades import calcular_mcsi

@st.cache_data
def cargar_datos():
    tabla_inv = pd.read_csv("data/TablaMortalidad_Inv.csv")
    tabla_act = pd.read_csv("data/TablaMortalidad_Act.csv")
    tabla_desercion = pd.read_csv("data/TablaDesercion_D.csv")
    inpc = pd.read_csv("data/INPC_q.csv")  
    return tabla_inv, tabla_act, inpc, tabla_desercion

tabla_inv, tabla_act, inpc, tabla_desercion = cargar_datos()

st.set_page_config(page_title="Monto Constitutivo", layout="centered")

st.title(" Calculadora de Monto Constitutivo (Invalidez)")

# -------------------------
# DATOS GENERALES
# -------------------------
st.header("Datos del aseguradoooooo Jesús se está durmiendo. Lince xd")

sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])

edad = st.number_input("Edad", min_value=0, max_value=120, step=1)

semanas = st.number_input("Número de semanas cotizadas", min_value=0, step=1)

# -------------------------
# CONYUGE
# -------------------------
st.header("Beneficiarios")

tiene_conyuge = st.checkbox("¿Tiene cónyuge?")
 
edad_conyuge = None
sexo_conyuge = None

if tiene_conyuge:
    col1, col2 = st.columns(2)

    with col1:
        edad_conyuge = st.number_input(
            "Edad del cónyuge",
            min_value=0,
            max_value=120
        )

    with col2:
        sexo_conyuge = st.selectbox(
            "Sexo del cónyuge",
            ["Hombre", "Mujer"]
        )

conyuge = None

if tiene_conyuge:
    conyuge = {
        "edad": edad_conyuge,
        "sexo": sexo_conyuge
    }
# -------------------------
# HIJOS
# -------------------------
num_hijos = st.number_input("Número de hijos", min_value=0, max_value=10, step=1)

hijos = []

for i in range(num_hijos):
    st.subheader(f"Hijo {i+1}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        edad_hijo = st.number_input(
            f"Edad hijo {i+1}",
            min_value=0,
            max_value=30,
            key=f"edad_hijo_{i}"
        )
    
    with col2:
        sexo_hijo = st.selectbox(
            f"Sexo hijo {i+1}",
            ["Hombre", "Mujer"],
            key=f"sexo_hijo_{i}"
        )
    
    hijos.append({
        "edad": edad_hijo,
        "sexo": sexo_hijo
    })

# -------------------------
# ASCENDIENTES
# -------------------------
num_asc = st.number_input("Número de ascendientes", min_value=0, max_value=2)

edades_asc = []
sexos_asc = []

for i in range(num_asc):
    col1, col2 = st.columns(2)
    
    with col1:
        edad_asc = st.number_input(
            f"Edad ascendiente {i+1}",
            min_value=0,
            max_value=120,
            key=f"edad_asc_{i}"
        )
    
    with col2:
        sexo_asc = st.selectbox(
            f"Sexo ascendiente {i+1}",
            ["hombre", "mujer"],
            key=f"sexo_asc_{i}"
        )
    
    edades_asc.append(edad_asc)
    sexos_asc.append(sexo_asc)

# -------------------------
# SALARIOS
# -------------------------
st.header("Salarios promedio diarios")

anio_final = st.number_input(
    "Último año cotizado",
    min_value=1900,
    max_value=2100,
    value=2023
)

st.markdown(
"""
Ingresa los salarios promedio diarios de los últimos años.

- Puedes capturar **hasta 15 años** para cubrir posibles periodos sin cotización.
- Si en algún año **no cotizaste**, déjalo en **0**.
- El sistema tomará automáticamente **los últimos 10 años con salario distinto de 0**.
- Si ya tienes 10 años completos, puedes dejar los demás en 0.
"""
)

# Generar años
anios = [anio_final - i for i in range(15)]

df_salarios = pd.DataFrame({
    "Año": anios,
    "Salario promedio diario": [0.0]*15
})

st.write("Edita los salarios (puedes usar Enter como en Excel):")

df_editado = st.data_editor(
    df_salarios,
    num_rows="fixed",
    use_container_width=True,
    disabled=["Año"]
)

# Extraer datos
salarios = df_editado["Salario promedio diario"].tolist()

# Validación: negativos
for i, s in enumerate(salarios):
    if s < 0:
        errores.append(f"Salario negativo en año {anios[i]}")

# Filtrar salarios válidos (ignorar ceros)
salarios_validos = [s for s in salarios if s > 0]

# Validaciones importantes
errores = []

if len(salarios_validos) == 0:
    errores.append("No hay salarios válidos")

elif len(salarios_validos) < 10:
    errores.append("Se requieren al menos 10 años con salario para aproximar 500 semanas")

# Tomar SOLO los primeros 10 válidos
salarios_utilizados = salarios_validos[:10]

# (opcional) mostrar qué años se usaron
anios_validos = [anios[i] for i in range(len(salarios)) if salarios[i] > 0][:10]

salarios_actualizados = actualizar_salarios(
    inpc,
    salarios_validos,
    anios_validos
)

# -------------------------
# VALIDACIONES
# -------------------------

if edad < 15:
    errores.append("La edad del asegurado es demasiado baja")

if tiene_conyuge and edad_conyuge is not None:
    if edad_conyuge < 15:
        errores.append("Edad del cónyuge inválida")

if sum(salarios) == 0:
    errores.append("No has ingresado salarios")


# -------------------------
# RESULTADOS
# -------------------------
if st.button("Calcular monto constitutivo"):

    if len(errores) > 0:
        for e in errores:
            st.error(e)

    else:
        resultado_pbss = calcular_monto_constitutivo(
            edad=edad,
            conyuge=conyuge,
            salarios_actualizados=salarios_actualizados,
            tabla_inv=tabla_inv,
            tabla_act=tabla_act
        )

        resultado_pbsi = calcular_mcsi(
            edad_trabajador=edad,
            salarios_actualizados=salarios_actualizados,
            conyuge=conyuge,
            hijos=hijos,
            edades_asc=edades_asc,
            sexos_asc=sexos_asc,
            df_inv=tabla_inv,
            df_act=tabla_act,
            df_desercion=tabla_desercion
        )

        st.subheader("Resultados del Cálculo")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Monto Constitutivo (PBSS)", f"S{resultado_pbss:,.2f}")
        with col2:
            st.metric("Monto Constitutivo (MCSI)", f"S{calcular_mcsi:,.2f}")
