#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd

@st.cache_data
def cargar_datos():
    tabla_inv = pd.read_csv("data/TablaMortalidad_Inv.csv")
    inpc = pd.read_csv("data/inpc.csv")  # usa el nombre real
    return tabla_inv, inpc

tabla_inv, inpc = cargar_datos()

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
if tiene_conyuge:
    edad_conyuge = st.number_input("Edad del cónyuge", min_value=0, max_value=120)

# -------------------------
# HIJOS
# -------------------------
num_hijos = st.number_input("Número de hijos", min_value=0, max_value=10, step=1)

hijos = []

for i in range(num_hijos):
    st.subheader(f"Hijo {i+1}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        edad = st.number_input(
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
        "edad": edad,
        "sexo": sexo_hijo
    })

# -------------------------
# ASCENDIENTES
# -------------------------
num_asc = st.number_input("Número de ascendientes", min_value=0, max_value=2)

edades_asc = []
for i in range(num_asc):
    edad_asc = st.number_input(f"Edad ascendiente {i+1}", min_value=0, max_value=120)
    edades_asc.append(edad_asc)

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

st.write("Salarios actualizados:", salarios_actualizados)

# -------------------------
# VALIDACIONES
# -------------------------
errores = []

if edad < 15:
    errores.append("La edad del asegurado es demasiado baja")

if tiene_conyuge and edad_conyuge is not None:
    if edad_conyuge < 15:
        errores.append("Edad del cónyuge inválida")

for i, e in enumerate(hijos):
    if e > 25:
        errores.append(f"Hijo {i+1} con edad mayor a 25 (revisar dependencia)")

if sum(salarios) == 0:
    errores.append("No has ingresado salarios")

# -------------------------
# FUNCIÓN DE CÁLCULO (placeholder)
# -------------------------
def calcular_monto():
    """
    Aquí metes tu modelo actuarial real.
    Por ahora es un ejemplo sencillo.
    """

    salario_promedio = sum(salarios) / len(salarios)

    factor_familiar = 1

    if tiene_conyuge:
        factor_familiar += 0.15

    factor_familiar += 0.10 * len(hijos)
    factor_familiar += 0.05 * len(edades_asc)

    monto = salario_promedio * 30 * factor_familiar

    return monto

# -------------------------
# RESULTADOS
# -------------------------
st.header("Resultado")

if st.button("Calcular monto constitutivo"):

    if errores:
        st.error("❌ Hay errores en los datos:")
        for e in errores:
            st.write(f"- {e}")
    else:
        monto = calcular_monto()

        st.success("✅ Cálculo realizado correctamente")

        st.metric(label="Monto constitutivo estimado", value=f"${monto:,.2f}")

        # Mostrar resumen
        with st.expander("Ver resumen de datos"):
            st.write({
                "Sexo": sexo,
                "Edad": edad,
                "Semanas": semanas,
                "Cónyuge": edad_conyuge if tiene_conyuge else "No",
                "Hijos": hijos,
                "Ascendientes": edades_asc,
                "Salarios": dict(zip(anios, salarios))
            })

