"""Cartões e gráficos individuais dos motores."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from .dados import dados_motor

def mostrar_motor(motor, df):
    dados, demo = dados_motor(df, motor)
    st.markdown(f"### {motor}")
    velocidade = float(dados["velocidade"].iloc[-1]) if not dados.empty else float("nan")
    corrente = float(dados["corrente"].iloc[-1]) if not dados.empty else float("nan")
    card_vel, card_status, card_corr = st.columns(3)
    card_vel.metric("Velocidade", f"{velocidade:.1f} %" if np.isfinite(velocidade) else "—")
    # Ainda não há endereço mapeado para status ligado/desligado.
    card_status.metric("Status", "Não mapeado")
    card_corr.metric("Corrente", f"{corrente:.2f} A" if np.isfinite(corrente) else "—")
    fig = go.Figure(go.Scatter(
        x=dados["timestamp"], y=dados["corrente"], mode="lines",
        line=dict(color="#2878b8", width=2),
        hovertemplate="%{x|%H:%M:%S}<br>%{y:.2f} A<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=245,
        margin=dict(l=5,r=10,t=8,b=5),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="A", gridcolor="#edf1f5", rangemode="tozero"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"grafico_{motor}")
    return demo
