"""Cartões e gráficos individuais dos motores."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from .dados import dados_motor

def mostrar_motor(motor, df):
    dados, demo = dados_motor(df, motor)
    st.markdown(f"### {motor}")
    if dados.empty:
        st.info("Sem leituras disponíveis para este motor.")
        return demo
    velocidade = float(dados["velocidade"].iloc[-1]) if not dados.empty else float("nan")
    corrente = float(dados["corrente"].iloc[-1]) if not dados.empty else float("nan")
    card_vel, card_status, card_corr = st.columns([1, 1.3, 1], gap="small")
    card_vel.metric("Velocidade", f"{velocidade:.1f} %" if np.isfinite(velocidade) else "—")
    # Valor ilustrativo para testes: o sinal de estado real ainda não foi mapeado.
    card_status.metric("Status", "ON", help="Indicador demonstrativo: o estado real do motor ainda não está mapeado.")
    card_corr.metric("Corrente", f"{corrente:.2f} A" if np.isfinite(corrente) else "—")
    fig = go.Figure(go.Scatter(
        x=dados["timestamp"], y=dados["corrente"], mode="lines",
        line=dict(color="#2878b8", width=2),
        hovertemplate="%{x|%H:%M:%S}<br>%{y:.2f} A<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=235,
        margin=dict(l=5,r=10,t=8,b=5),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="A", gridcolor="#edf1f5", rangemode="tozero"),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key=f"grafico_{motor}")
    return demo
