"""
Pollo e Cucina — Business Simulator
Interactive Streamlit web application
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from engine import (
    INGREDIENTS_DEFAULT, RECIPES, SALES_MIX_DEFAULT,
    FIXED_COSTS_DEFAULT, SEASONALITY_BASE, FORCE_MAJEURE_EVENTS,
    MONTHS, compute_recipe_cost, compute_all_food_costs,
    compute_monthly_pl, compute_breakeven, compute_scenarios,
    compute_monte_carlo,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pollo e Cucina — Business Simulator",
    page_icon="🍗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #C0392B 0%, #922B21 50%, #1A1A1A 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { font-size: 2.2rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .main-header p { font-size: 1rem; opacity: 0.85; margin: 0.4rem 0 0; }
    
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border-left: 4px solid #C0392B;
        height: 100%;
    }
    .kpi-card.green { border-left-color: #27AE60; }
    .kpi-card.orange { border-left-color: #E67E22; }
    .kpi-card.blue { border-left-color: #2980B9; }
    .kpi-card.purple { border-left-color: #8E44AD; }
    
    .kpi-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.8px; color: #888; margin-bottom: 0.3rem; }
    .kpi-value { font-size: 1.8rem; font-weight: 700; color: #1A1A1A; line-height: 1; }
    .kpi-sub { font-size: 0.8rem; color: #666; margin-top: 0.3rem; }
    
    .fm-banner {
        background: linear-gradient(135deg, #922B21, #C0392B);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-weight: 600;
    }
    
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1A1A1A;
        border-bottom: 2px solid #C0392B;
        padding-bottom: 0.4rem;
        margin: 1.5rem 0 1rem;
    }
    
    .sidebar-section {
        background: #F8F9FA;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
    }
    
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 0.8rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
    }
    
    .highlight-positive { color: #27AE60; font-weight: 600; }
    .highlight-negative { color: #C0392B; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt_eur(v):
    if v >= 0:
        return f"**+{v:,.0f} €**"
    return f"**{v:,.0f} €**"

def color_net(val):
    color = "#27AE60" if val >= 0 else "#C0392B"
    return f'<span style="color:{color};font-weight:600">{val:,.0f} €</span>'

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if "prices_A" not in st.session_state:
    st.session_state.prices_A = {k: v[3] for k, v in INGREDIENTS_DEFAULT.items()}
if "prices_B" not in st.session_state:
    st.session_state.prices_B = {k: v[4] for k, v in INGREDIENTS_DEFAULT.items()}
if "sales_mix" not in st.session_state:
    st.session_state.sales_mix = dict(SALES_MIX_DEFAULT)
if "fixed_costs" not in st.session_state:
    st.session_state.fixed_costs = dict(FIXED_COSTS_DEFAULT)
if "seasonality" not in st.session_state:
    st.session_state.seasonality = dict(SEASONALITY_BASE)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — GLOBAL PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Paramètres Globaux")

    st.markdown("### 📅 Exploitation")
    days_per_week = st.slider("Jours d'ouverture / semaine", 4, 7, 6)
    open_months = st.slider("Mois d'ouverture / an", 6, 12, 10)

    st.markdown("### 💰 Financement")
    loan_amount = st.number_input("Montant emprunt (€)", 0, 200000, 80000, 5000)
    loan_rate = st.number_input("Taux annuel (%)", 0.0, 10.0, 3.5, 0.1)
    loan_years = st.slider("Durée (années)", 3, 10, 7)
    if loan_amount > 0 and loan_rate > 0:
        r = loan_rate / 100 / 12
        n = loan_years * 12
        loan_monthly = loan_amount * r * (1 + r)**n / ((1 + r)**n - 1)
    else:
        loan_monthly = loan_amount / (loan_years * 12) if loan_years > 0 else 0
    st.caption(f"Mensualité estimée : **{loan_monthly:,.0f} €/mois**")

    st.markdown("### 👤 Rémunération Gérant")
    salary_net = st.number_input("Salaire net souhaité (€/mois)", 0, 5000, 1800, 100)
    tns_rate = st.slider("Taux charges TNS (%)", 20, 45, 35) / 100
    st.caption(f"Coût total gérant : **{salary_net * (1 + tns_rate):,.0f} €/mois**")

    st.markdown("### ⚡ Énergie")
    energy_option = st.selectbox("Configuration énergie",
        ["Tout Électrique", "Mixte Gaz + Élec", "Feu de Bois"])
    energy_map = {"Tout Électrique": 28, "Mixte Gaz + Élec": 22, "Feu de Bois": 18}
    energy_daily = st.number_input("Coût énergie / jour (€)", 5, 80,
                                    energy_map[energy_option], 1)

    st.markdown("### 🏦 TVA")
    tva_rate = st.selectbox("Régime TVA", ["Micro (franchise)", "Réel simplifié 10%",
                                            "Réel normal 10%"])

    st.markdown("---")
    st.markdown("### 🔴 Force Majeure")
    fm_active = st.toggle("Activer un événement", value=False)
    fm_event = None
    fm_month = None
    if fm_active:
        fm_event = st.selectbox("Événement", list(FORCE_MAJEURE_EVENTS.keys()))
        fm_month = st.selectbox("Mois impacté", MONTHS)
        ev = FORCE_MAJEURE_EVENTS[fm_event]
        st.warning(f"**Impact :** {ev['description']}")

    st.markdown("---")
    st.markdown("### 🏪 Fournisseur actif")
    active_supplier = st.radio("Utiliser les prix de :", ["Fournisseur A", "Fournisseur B"])
    prices = (st.session_state.prices_A if active_supplier == "Fournisseur A"
              else st.session_state.prices_B)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🍗 Pollo e Cucina — Business Simulator</h1>
    <p>Six-Fours-les-Plages · Snacking & Rôtisserie · Simulateur de gestion dynamique</p>
</div>
""", unsafe_allow_html=True)

if fm_active and fm_event:
    ev = FORCE_MAJEURE_EVENTS[fm_event]
    st.markdown(f"""
    <div class="fm-banner">
        ⚠️ MODE FORCE MAJEURE ACTIVÉ — {fm_event} en <strong>{fm_month}</strong><br>
        <small>{ev['description']}</small>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE
# ─────────────────────────────────────────────────────────────────────────────
food_costs = compute_all_food_costs(prices)
pl_df = compute_monthly_pl(
    sales_mix=st.session_state.sales_mix,
    prices=prices,
    fixed_costs=st.session_state.fixed_costs,
    days_per_week=days_per_week,
    salary_net=salary_net,
    tns_rate=tns_rate,
    loan_monthly=loan_monthly,
    energy_daily=energy_daily,
    seasonality=st.session_state.seasonality,
    force_majeure_event=fm_event if fm_active else None,
    fm_month=fm_month if fm_active else None,
)
be = compute_breakeven(
    fixed_costs=st.session_state.fixed_costs,
    salary_net=salary_net,
    tns_rate=tns_rate,
    loan_monthly=loan_monthly,
    energy_daily=energy_daily,
    avg_food_cost_pct=pl_df["Food Cost %"].mean(),
)
scenarios_df = compute_scenarios(
    prices=prices,
    fixed_costs=st.session_state.fixed_costs,
    salary_net=salary_net,
    tns_rate=tns_rate,
    loan_monthly=loan_monthly,
    energy_daily=energy_daily,
)

# Annual totals
annual_ca = pl_df["CA HT (€)"].sum()
annual_net = pl_df["Résultat Net (€)"].sum()
annual_ebe = pl_df["EBE (€)"].sum()
avg_food_cost = pl_df["Food Cost %"].mean()
profitable_months = (pl_df["Résultat Net (€)"] > 0).sum()

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">CA Annuel HT</div>
        <div class="kpi-value">{annual_ca:,.0f} €</div>
        <div class="kpi-sub">{annual_ca/12:,.0f} €/mois en moy.</div>
    </div>""", unsafe_allow_html=True)
with k2:
    color_class = "green" if annual_net > 0 else ""
    st.markdown(f"""<div class="kpi-card {color_class}">
        <div class="kpi-label">Résultat Net Annuel</div>
        <div class="kpi-value" style="color:{'#27AE60' if annual_net>0 else '#C0392B'}">{annual_net:+,.0f} €</div>
        <div class="kpi-sub">{profitable_months}/12 mois bénéficiaires</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card blue">
        <div class="kpi-label">EBE Annuel</div>
        <div class="kpi-value">{annual_ebe:+,.0f} €</div>
        <div class="kpi-sub">{annual_ebe/annual_ca*100:.1f}% du CA</div>
    </div>""", unsafe_allow_html=True)
with k4:
    fc_color = "green" if avg_food_cost < 32 else ("orange" if avg_food_cost < 38 else "")
    st.markdown(f"""<div class="kpi-card {fc_color}">
        <div class="kpi-label">Food Cost Moyen</div>
        <div class="kpi-value">{avg_food_cost:.1f}%</div>
        <div class="kpi-sub">Cible : &lt; 32%</div>
    </div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="kpi-card purple">
        <div class="kpi-label">Seuil Rentabilité</div>
        <div class="kpi-value">{be['ca_seuil_journalier']:,.0f} €/j</div>
        <div class="kpi-sub">≈ {be['couverts_seuil']:.0f} couverts/jour</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 P&L Mensuel",
    "🍗 Fiches Recettes",
    "🎯 Scénarios",
    "🎲 Monte Carlo",
    "🔴 Force Majeure",
    "⚙️ Paramètres Avancés",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — P&L MENSUEL
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-title">Compte de Résultat Mensuel</div>', unsafe_allow_html=True)

    # Main chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Chiffre d'Affaires & Charges", "Résultat Net Mensuel"),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4],
    )

    fig.add_trace(go.Bar(
        x=pl_df["Mois"], y=pl_df["CA HT (€)"],
        name="CA HT", marker_color="#C0392B", opacity=0.9,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=pl_df["Mois"], y=pl_df["Coût MP (€)"],
        name="Coût MP", marker_color="#E8A89C", opacity=0.9,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=pl_df["Mois"], y=pl_df["EBE (€)"],
        name="EBE", mode="lines+markers",
        line=dict(color="#F39C12", width=2.5),
        marker=dict(size=7),
    ), row=1, col=1)

    colors_net = ["#27AE60" if v >= 0 else "#C0392B" for v in pl_df["Résultat Net (€)"]]
    fig.add_trace(go.Bar(
        x=pl_df["Mois"], y=pl_df["Résultat Net (€)"],
        name="Résultat Net", marker_color=colors_net,
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="#888", row=2, col=1)

    fig.update_layout(
        height=520, barmode="group",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_yaxes(ticksuffix=" €", gridcolor="#F0F0F0")
    st.plotly_chart(fig, use_container_width=True)

    # Food cost trend
    col_fc, col_margin = st.columns(2)
    with col_fc:
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=pl_df["Mois"], y=pl_df["Food Cost %"],
            fill="tozeroy", fillcolor="rgba(192,57,43,0.15)",
            line=dict(color="#C0392B", width=2),
            name="Food Cost %",
        ))
        fig_fc.add_hline(y=32, line_dash="dash", line_color="#27AE60",
                         annotation_text="Cible 32%")
        fig_fc.update_layout(
            title="Food Cost % mensuel", height=280,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(ticksuffix="%", range=[0, 50], gridcolor="#F0F0F0"),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_fc, use_container_width=True)

    with col_margin:
        fig_mg = go.Figure()
        fig_mg.add_trace(go.Bar(
            x=pl_df["Mois"], y=pl_df["Marge Brute (€)"],
            marker_color="#2980B9", name="Marge Brute",
        ))
        fig_mg.update_layout(
            title="Marge Brute mensuelle (€)", height=280,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(ticksuffix=" €", gridcolor="#F0F0F0"),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_mg, use_container_width=True)

    # Table
    st.markdown('<div class="section-title">Tableau détaillé</div>', unsafe_allow_html=True)
    display_df = pl_df.copy()
    st.dataframe(
        display_df.style
        .format({
            "CA HT (€)": "{:,.0f} €",
            "Coût MP (€)": "{:,.0f} €",
            "Marge Brute (€)": "{:,.0f} €",
            "Food Cost %": "{:.1f}%",
            "Marge Brute %": "{:.1f}%",
            "Charges Fixes (€)": "{:,.0f} €",
            "Énergie (€)": "{:,.0f} €",
            "RH Gérant (€)": "{:,.0f} €",
            "Remb. Emprunt (€)": "{:,.0f} €",
            "EBE (€)": "{:,.0f} €",
            "Résultat Net (€)": "{:,.0f} €",
        })
        .map(lambda v: "color: #27AE60; font-weight:600" if isinstance(v, (int, float)) and v > 0
                  else ("color: #C0392B; font-weight:600" if isinstance(v, (int, float)) and v < 0 else ""),
                  subset=["Résultat Net (€)", "EBE (€)"])
        .set_properties(**{"background-color": "#FAFAFA", "border": "1px solid #E0E0E0"}),
        use_container_width=True,
        height=460,
    )

    # Annual summary
    st.markdown('<div class="section-title">Récapitulatif Annuel</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA Total HT", f"{annual_ca:,.0f} €")
    c2.metric("Coût MP Total", f"{pl_df['Coût MP (€)'].sum():,.0f} €",
              f"{pl_df['Coût MP (€)'].sum()/annual_ca*100:.1f}% du CA")
    c3.metric("EBE Annuel", f"{annual_ebe:+,.0f} €",
              f"{annual_ebe/annual_ca*100:.1f}% du CA")
    c4.metric("Résultat Net Annuel", f"{annual_net:+,.0f} €",
              f"{profitable_months}/12 mois positifs")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — FICHES RECETTES
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Analyse Food Cost par Recette</div>', unsafe_allow_html=True)

    # Category filter
    categories = sorted(set(r["category"] for r in RECIPES.values()))
    cat_filter = st.multiselect("Filtrer par catégorie", categories, default=categories)

    fc_data = []
    for name, data in food_costs.items():
        if data["category"] in cat_filter:
            fc_data.append({
                "Recette": f"{data['emoji']} {name}",
                "Catégorie": data["category"],
                "Prix Vente (€)": data["sell_price"],
                "Coût MP (€)": data["raw_cost"],
                "Marge (€)": data["margin"],
                "Food Cost %": data["food_cost_pct"],
                "Marge %": data["margin_pct"],
            })
    fc_df = pd.DataFrame(fc_data)

    # Chart: food cost per recipe
    fig_fc2 = go.Figure()
    colors_fc = ["#27AE60" if v < 30 else ("#F39C12" if v < 38 else "#C0392B")
                 for v in fc_df["Food Cost %"]]
    fig_fc2.add_trace(go.Bar(
        x=fc_df["Recette"], y=fc_df["Food Cost %"],
        marker_color=colors_fc, text=fc_df["Food Cost %"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
    ))
    fig_fc2.add_hline(y=32, line_dash="dash", line_color="#27AE60",
                      annotation_text="Cible 32%", annotation_position="right")
    fig_fc2.add_hline(y=38, line_dash="dot", line_color="#E74C3C",
                      annotation_text="Seuil alerte 38%", annotation_position="right")
    fig_fc2.update_layout(
        title="Food Cost % par recette",
        height=380, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(ticksuffix="%", range=[0, 55], gridcolor="#F0F0F0"),
        xaxis=dict(tickangle=-30),
        margin=dict(l=10, r=80, t=50, b=100),
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig_fc2, use_container_width=True)

    # Waterfall: margin per recipe
    fig_wf = go.Figure(go.Bar(
        x=fc_df["Recette"],
        y=fc_df["Marge (€)"],
        marker_color=["#27AE60" if v > 3 else ("#F39C12" if v > 1.5 else "#C0392B")
                      for v in fc_df["Marge (€)"]],
        text=fc_df["Marge (€)"].apply(lambda x: f"{x:.2f} €"),
        textposition="outside",
    ))
    fig_wf.update_layout(
        title="Marge brute par portion (€)",
        height=340, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(ticksuffix=" €", gridcolor="#F0F0F0"),
        xaxis=dict(tickangle=-30),
        margin=dict(l=10, r=10, t=50, b=100),
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Table
    st.dataframe(
        fc_df.style
        .format({
            "Prix Vente (€)": "{:.2f} €",
            "Coût MP (€)": "{:.3f} €",
            "Marge (€)": "{:.2f} €",
            "Food Cost %": "{:.1f}%",
            "Marge %": "{:.1f}%",
        })
        .background_gradient(subset=["Food Cost %"], cmap="RdYlGn_r", vmin=20, vmax=45)
        .background_gradient(subset=["Marge %"], cmap="RdYlGn", vmin=50, vmax=80),
        use_container_width=True,
    )

    # Ingredient detail for selected recipe
    st.markdown('<div class="section-title">Détail ingrédients d\'une recette</div>',
                unsafe_allow_html=True)
    selected_recipe = st.selectbox("Choisir une recette", list(RECIPES.keys()))
    recipe = RECIPES[selected_recipe]
    ing_rows = []
    for ref, qty in recipe["ingredients"]:
        ing = INGREDIENTS_DEFAULT[ref]
        price = prices.get(ref, ing[3])
        cost = price * qty
        ing_rows.append({
            "Réf.": ref,
            "Ingrédient": ing[0],
            "Catégorie": ing[1],
            "Unité": ing[2],
            "Quantité": qty,
            "Prix unit. (€)": price,
            "Coût portion (€)": round(cost, 4),
            "% du coût total": 0,
        })
    ing_df = pd.DataFrame(ing_rows)
    total_cost = ing_df["Coût portion (€)"].sum()
    ing_df["% du coût total"] = (ing_df["Coût portion (€)"] / total_cost * 100).round(1)

    col_ing, col_pie = st.columns([2, 1])
    with col_ing:
        st.dataframe(
            ing_df.style.format({
                "Quantité": "{:.3f}",
                "Prix unit. (€)": "{:.3f} €",
                "Coût portion (€)": "{:.4f} €",
                "% du coût total": "{:.1f}%",
            }).background_gradient(subset=["% du coût total"], cmap="Oranges"),
            use_container_width=True,
        )
        sell = recipe["price"]
        st.info(f"**Coût MP total :** {total_cost:.3f} € | **Prix de vente :** {sell:.2f} € | "
                f"**Food Cost :** {total_cost/sell*100:.1f}% | **Marge :** {sell-total_cost:.2f} €")
    with col_pie:
        fig_pie = px.pie(
            ing_df, values="Coût portion (€)", names="Ingrédient",
            title=f"Répartition des coûts\n{selected_recipe}",
            color_discrete_sequence=px.colors.sequential.Reds_r,
        )
        fig_pie.update_layout(height=380, margin=dict(l=0, r=0, t=60, b=0),
                               font=dict(family="Inter"))
        st.plotly_chart(fig_pie, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — SCÉNARIOS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Comparaison de Scénarios d\'Activité</div>',
                unsafe_allow_html=True)

    fig_sc = make_subplots(
        rows=1, cols=3,
        subplot_titles=("CA Mensuel (€)", "EBE (€)", "Résultat Net (€)"),
        horizontal_spacing=0.08,
    )
    scenario_colors = ["#C0392B", "#E67E22", "#F1C40F", "#27AE60", "#2980B9", "#8E44AD"]
    for i, row in scenarios_df.iterrows():
        color = scenario_colors[i % len(scenario_colors)]
        fig_sc.add_trace(go.Bar(
            x=[row["Scénario"]], y=[row["CA mensuel (€)"]],
            marker_color=color, showlegend=False,
            text=f"{row['CA mensuel (€)']:,.0f} €", textposition="outside",
        ), row=1, col=1)
        fig_sc.add_trace(go.Bar(
            x=[row["Scénario"]], y=[row["EBE (€)"]],
            marker_color=color, showlegend=False,
            text=f"{row['EBE (€)']:+,.0f} €", textposition="outside",
        ), row=1, col=2)
        fig_sc.add_trace(go.Bar(
            x=[row["Scénario"]], y=[row["Résultat Net (€)"]],
            marker_color=color, showlegend=False,
            text=f"{row['Résultat Net (€)']:+,.0f} €", textposition="outside",
        ), row=1, col=3)

    fig_sc.add_hline(y=0, line_dash="dash", line_color="#888", row=1, col=2)
    fig_sc.add_hline(y=0, line_dash="dash", line_color="#888", row=1, col=3)
    fig_sc.update_layout(
        height=440, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=60, b=80),
    )
    fig_sc.update_yaxes(ticksuffix=" €", gridcolor="#F0F0F0")
    fig_sc.update_xaxes(tickangle=-25)
    st.plotly_chart(fig_sc, use_container_width=True)

    # Scenario table
    st.dataframe(
        scenarios_df.style
        .format({
            "CA mensuel (€)": "{:,.0f} €",
            "Coût MP (€)": "{:,.0f} €",
            "Food Cost %": "{:.1f}%",
            "Marge Brute (€)": "{:,.0f} €",
            "EBE (€)": "{:+,.0f} €",
            "Résultat Net (€)": "{:+,.0f} €",
        })
        .map(lambda v: "color: #27AE60; font-weight:600" if isinstance(v, (int, float)) and v > 0
                  else ("color: #C0392B; font-weight:600" if isinstance(v, (int, float)) and v < 0 else ""),
                  subset=["EBE (€)", "Résultat Net (€)"]),
        use_container_width=True,
        height=280,
    )

    # Break-even analysis
    st.markdown('<div class="section-title">Analyse du Seuil de Rentabilité</div>',
                unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CA Seuil / mois", f"{be['ca_seuil_mensuel']:,.0f} €")
    c2.metric("CA Seuil / jour", f"{be['ca_seuil_journalier']:,.0f} €")
    c3.metric("Couverts / jour", f"{be['couverts_seuil']:.0f}")
    c4.metric("Charges fixes totales", f"{be['total_charges_fixes']:,.0f} €/mois")
    c5.metric("Taux de marge sur CV", f"{be['taux_marge_contribution']:.1f}%")

    # Break-even chart
    ca_range = np.linspace(0, be["ca_seuil_mensuel"] * 2, 200)
    charges_fixes_line = np.full_like(ca_range, be["total_charges_fixes"])
    total_costs_line = charges_fixes_line + ca_range * (1 - be["taux_marge_contribution"] / 100)
    revenue_line = ca_range

    fig_be = go.Figure()
    fig_be.add_trace(go.Scatter(
        x=ca_range, y=revenue_line, name="Revenus",
        line=dict(color="#27AE60", width=2.5),
    ))
    fig_be.add_trace(go.Scatter(
        x=ca_range, y=total_costs_line, name="Charges totales",
        line=dict(color="#C0392B", width=2.5),
    ))
    fig_be.add_trace(go.Scatter(
        x=ca_range, y=charges_fixes_line, name="Charges fixes",
        line=dict(color="#888", width=1.5, dash="dash"),
    ))
    fig_be.add_vline(
        x=be["ca_seuil_mensuel"], line_dash="dot", line_color="#F39C12",
        annotation_text=f"Seuil : {be['ca_seuil_mensuel']:,.0f} €",
        annotation_position="top right",
    )
    fig_be.update_layout(
        title="Graphique du Seuil de Rentabilité",
        height=380, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="CA mensuel (€)", ticksuffix=" €", gridcolor="#F0F0F0"),
        yaxis=dict(title="Montant (€)", ticksuffix=" €", gridcolor="#F0F0F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=60, b=40),
    )
    st.plotly_chart(fig_be, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — MONTE CARLO
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">Simulation Monte Carlo — Distribution des Résultats</div>',
                unsafe_allow_html=True)
    st.markdown("""
    La simulation Monte Carlo génère **N scénarios aléatoires** en faisant varier simultanément
    le niveau d'activité et les coûts matières premières autour de vos hypothèses de base.
    Elle vous donne une distribution de probabilité du résultat net mensuel.
    """)

    col_mc1, col_mc2, col_mc3 = st.columns(3)
    with col_mc1:
        n_sim = st.slider("Nombre de simulations", 500, 5000, 2000, 500)
    with col_mc2:
        activity_mean = st.slider("Activité moyenne (base 1.0)", 0.5, 2.0, 1.0, 0.05)
    with col_mc3:
        activity_std = st.slider("Volatilité activité (σ)", 0.05, 0.50, 0.25, 0.05)

    cost_std = st.slider("Volatilité coût matières premières (σ %)", 2, 25, 10, 1) / 100

    with st.spinner("Calcul en cours..."):
        mc_results = compute_monte_carlo(
            prices=prices,
            fixed_costs=st.session_state.fixed_costs,
            salary_net=salary_net,
            tns_rate=tns_rate,
            loan_monthly=loan_monthly,
            energy_daily=energy_daily,
            n_simulations=n_sim,
            activity_mean=activity_mean,
            activity_std=activity_std,
            cost_std_pct=cost_std,
        )

    # Stats
    p5, p25, p50, p75, p95 = np.percentile(mc_results, [5, 25, 50, 75, 95])
    prob_positive = (mc_results > 0).mean() * 100
    prob_above_1k = (mc_results > 1000).mean() * 100

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Médiane", f"{p50:+,.0f} €")
    c2.metric("P25 — P75", f"{p25:+,.0f} € / {p75:+,.0f} €")
    c3.metric("P5 (pire 5%)", f"{p5:+,.0f} €")
    c4.metric("P95 (meilleur 5%)", f"{p95:+,.0f} €")
    c5.metric("Prob. résultat > 0", f"{prob_positive:.1f}%")

    # Histogram
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Histogram(
        x=mc_results, nbinsx=80,
        marker_color="#C0392B", opacity=0.75,
        name="Distribution résultats",
    ))
    fig_mc.add_vline(x=0, line_dash="dash", line_color="#888",
                     annotation_text="Seuil 0 €")
    fig_mc.add_vline(x=p50, line_dash="dot", line_color="#F39C12",
                     annotation_text=f"Médiane : {p50:+,.0f} €")
    fig_mc.add_vline(x=p5, line_dash="dot", line_color="#2980B9",
                     annotation_text=f"P5 : {p5:+,.0f} €")
    fig_mc.add_vline(x=p95, line_dash="dot", line_color="#27AE60",
                     annotation_text=f"P95 : {p95:+,.0f} €")

    # Color zones
    fig_mc.add_vrect(x0=min(mc_results), x1=0,
                     fillcolor="rgba(192,57,43,0.08)", line_width=0,
                     annotation_text="Zone perte", annotation_position="top left")
    fig_mc.add_vrect(x0=0, x1=max(mc_results),
                     fillcolor="rgba(39,174,96,0.06)", line_width=0,
                     annotation_text="Zone profit", annotation_position="top right")

    fig_mc.update_layout(
        title=f"Distribution du Résultat Net Mensuel ({n_sim:,} simulations)",
        height=420, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Résultat Net Mensuel (€)", ticksuffix=" €", gridcolor="#F0F0F0"),
        yaxis=dict(title="Fréquence", gridcolor="#F0F0F0"),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=60, b=40),
    )
    st.plotly_chart(fig_mc, use_container_width=True)

    # Cumulative probability
    sorted_results = np.sort(mc_results)
    cumulative_prob = np.arange(1, len(sorted_results) + 1) / len(sorted_results) * 100

    fig_cdf = go.Figure()
    fig_cdf.add_trace(go.Scatter(
        x=sorted_results, y=cumulative_prob,
        mode="lines", line=dict(color="#2980B9", width=2.5),
        fill="tozeroy", fillcolor="rgba(41,128,185,0.1)",
        name="Probabilité cumulée",
    ))
    fig_cdf.add_vline(x=0, line_dash="dash", line_color="#C0392B",
                      annotation_text="Seuil 0 €")
    fig_cdf.update_layout(
        title="Courbe de Probabilité Cumulée",
        height=320, plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(title="Résultat Net (€)", ticksuffix=" €", gridcolor="#F0F0F0"),
        yaxis=dict(title="Probabilité (%)", ticksuffix="%", range=[0, 100],
                   gridcolor="#F0F0F0"),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=50, b=40),
    )
    st.plotly_chart(fig_cdf, use_container_width=True)

    st.info(f"""
    **Lecture :** Avec vos hypothèses actuelles, la simulation indique que :
    - Il y a **{prob_positive:.1f}%** de probabilité d'atteindre un résultat net positif sur un mois donné.
    - Il y a **{prob_above_1k:.1f}%** de probabilité de dépasser **+1 000 €** de résultat net.
    - Dans les 5% de pires cas, le résultat net descend à **{p5:+,.0f} €**.
    - Dans les 5% de meilleurs cas, il monte à **{p95:+,.0f} €**.
    """)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — FORCE MAJEURE
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-title">Simulateur d\'Événements Force Majeure</div>',
                unsafe_allow_html=True)
    st.markdown("""
    Sélectionnez un événement et un mois d'impact pour visualiser immédiatement son effet
    sur le P&L annuel. Activez le toggle **Force Majeure** dans la barre latérale pour
    appliquer l'événement à tous les onglets.
    """)

    col_fm1, col_fm2 = st.columns(2)
    with col_fm1:
        fm_event_tab = st.selectbox("Événement à simuler",
                                     list(FORCE_MAJEURE_EVENTS.keys()), key="fm_tab")
    with col_fm2:
        fm_month_tab = st.selectbox("Mois d'impact", MONTHS, index=6, key="fm_month_tab")

    ev_tab = FORCE_MAJEURE_EVENTS[fm_event_tab]

    # Compute with and without FM
    pl_normal = compute_monthly_pl(
        sales_mix=st.session_state.sales_mix, prices=prices,
        fixed_costs=st.session_state.fixed_costs, days_per_week=days_per_week,
        salary_net=salary_net, tns_rate=tns_rate, loan_monthly=loan_monthly,
        energy_daily=energy_daily, seasonality=st.session_state.seasonality,
    )
    pl_fm = compute_monthly_pl(
        sales_mix=st.session_state.sales_mix, prices=prices,
        fixed_costs=st.session_state.fixed_costs, days_per_week=days_per_week,
        salary_net=salary_net, tns_rate=tns_rate, loan_monthly=loan_monthly,
        energy_daily=energy_daily, seasonality=st.session_state.seasonality,
        force_majeure_event=fm_event_tab, fm_month=fm_month_tab,
    )

    impact_ca = pl_fm["CA HT (€)"].sum() - pl_normal["CA HT (€)"].sum()
    impact_net = pl_fm["Résultat Net (€)"].sum() - pl_normal["Résultat Net (€)"].sum()

    # Event card
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1A1A1A,#2C3E50);color:white;
                padding:1.2rem 1.5rem;border-radius:12px;margin:1rem 0;">
        <h3 style="margin:0 0 0.5rem">{fm_event_tab}</h3>
        <p style="margin:0;opacity:0.85">{ev_tab['description']}</p>
        <div style="display:flex;gap:2rem;margin-top:0.8rem;flex-wrap:wrap">
            <span>📉 Activité : <strong>{ev_tab['cover_multiplier']:.0%}</strong></span>
            <span>💰 Coûts MP : <strong>{ev_tab['cost_multiplier']:.0%}</strong></span>
            <span>⚡ Énergie : <strong>{ev_tab['energy_multiplier']:.0%}</strong></span>
            <span>📅 Durée : <strong>{ev_tab['duration_days']} jours</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Impact metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Impact CA annuel", f"{impact_ca:+,.0f} €",
              delta_color="inverse")
    c2.metric("Impact Résultat Net annuel", f"{impact_net:+,.0f} €",
              delta_color="inverse")
    month_idx = MONTHS.index(fm_month_tab)
    ca_normal_month = pl_normal.loc[month_idx, "CA HT (€)"]
    ca_fm_month = pl_fm.loc[month_idx, "CA HT (€)"]
    c3.metric(f"CA {fm_month_tab} normal", f"{ca_normal_month:,.0f} €")
    c4.metric(f"CA {fm_month_tab} avec FM", f"{ca_fm_month:,.0f} €",
              delta=f"{ca_fm_month - ca_normal_month:+,.0f} €",
              delta_color="inverse")

    # Comparison chart
    fig_fm = go.Figure()
    fig_fm.add_trace(go.Bar(
        x=pl_normal["Mois"], y=pl_normal["CA HT (€)"],
        name="CA Normal", marker_color="#2980B9", opacity=0.7,
    ))
    fig_fm.add_trace(go.Bar(
        x=pl_fm["Mois"], y=pl_fm["CA HT (€)"],
        name="CA avec Force Majeure", marker_color="#C0392B", opacity=0.9,
    ))
    fig_fm.add_trace(go.Scatter(
        x=pl_normal["Mois"], y=pl_normal["Résultat Net (€)"],
        name="Résultat Net Normal", mode="lines+markers",
        line=dict(color="#27AE60", width=2, dash="dot"),
    ))
    fig_fm.add_trace(go.Scatter(
        x=pl_fm["Mois"], y=pl_fm["Résultat Net (€)"],
        name="Résultat Net avec FM", mode="lines+markers",
        line=dict(color="#E74C3C", width=2.5),
        marker=dict(size=8),
    ))
    fig_fm.add_hline(y=0, line_dash="dash", line_color="#888")
    fig_fm.update_layout(
        title=f"Impact de '{fm_event_tab}' en {fm_month_tab}",
        height=420, barmode="group",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(ticksuffix=" €", gridcolor="#F0F0F0"),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=60, b=40),
    )
    st.plotly_chart(fig_fm, use_container_width=True)

    # Resilience analysis
    st.markdown('<div class="section-title">Analyse de Résilience</div>', unsafe_allow_html=True)
    st.markdown("Combien de mois faut-il pour absorber la perte générée par cet événement ?")

    cumulative_normal = pl_normal["Résultat Net (€)"].cumsum()
    cumulative_fm = pl_fm["Résultat Net (€)"].cumsum()

    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(
        x=pl_normal["Mois"], y=cumulative_normal,
        name="Résultat cumulé normal", mode="lines+markers",
        line=dict(color="#27AE60", width=2.5),
        fill="tozeroy", fillcolor="rgba(39,174,96,0.08)",
    ))
    fig_res.add_trace(go.Scatter(
        x=pl_fm["Mois"], y=cumulative_fm,
        name="Résultat cumulé avec FM", mode="lines+markers",
        line=dict(color="#C0392B", width=2.5),
        fill="tozeroy", fillcolor="rgba(192,57,43,0.08)",
    ))
    fig_res.add_hline(y=0, line_dash="dash", line_color="#888",
                      annotation_text="Seuil 0 €")
    fig_res.update_layout(
        title="Résultat Net Cumulé sur 12 mois",
        height=340, plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(ticksuffix=" €", gridcolor="#F0F0F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Inter"),
        margin=dict(l=10, r=10, t=60, b=40),
    )
    st.plotly_chart(fig_res, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — PARAMÈTRES AVANCÉS
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-title">Paramètres Avancés</div>', unsafe_allow_html=True)

    adv_tab1, adv_tab2, adv_tab3, adv_tab4 = st.tabs([
        "📦 Prix Fournisseurs",
        "🍽️ Mix de Ventes",
        "💸 Charges Fixes",
        "📅 Saisonnalité",
    ])

    # ── Supplier Prices ──────────────────────────────────────────────────────
    with adv_tab1:
        st.markdown("Modifiez les prix des deux fournisseurs. Le fournisseur actif est "
                    "sélectionné dans la barre latérale.")

        categories_ing = sorted(set(v[1] for v in INGREDIENTS_DEFAULT.values()))
        cat_ing = st.selectbox("Filtrer par catégorie", ["Toutes"] + categories_ing,
                               key="cat_ing_filter")

        ing_edit_data = []
        for ref, (name, cat, unit, pa, pb) in INGREDIENTS_DEFAULT.items():
            if cat_ing == "Toutes" or cat == cat_ing:
                ing_edit_data.append({
                    "Réf.": ref,
                    "Ingrédient": name,
                    "Catégorie": cat,
                    "Unité": unit,
                    "Prix Fourn. A (€)": st.session_state.prices_A.get(ref, pa),
                    "Prix Fourn. B (€)": st.session_state.prices_B.get(ref, pb),
                    "Écart (%)": round((st.session_state.prices_A.get(ref, pa) /
                                        max(st.session_state.prices_B.get(ref, pb), 0.001) - 1) * 100, 1),
                })
        ing_edit_df = pd.DataFrame(ing_edit_data)

        edited_ing = st.data_editor(
            ing_edit_df,
            column_config={
                "Prix Fourn. A (€)": st.column_config.NumberColumn(
                    "Prix Fourn. A (€)", min_value=0.0, step=0.01, format="%.3f €"),
                "Prix Fourn. B (€)": st.column_config.NumberColumn(
                    "Prix Fourn. B (€)", min_value=0.0, step=0.01, format="%.3f €"),
                "Écart (%)": st.column_config.NumberColumn(
                    "Écart A vs B (%)", disabled=True, format="%.1f%%"),
                "Réf.": st.column_config.TextColumn(disabled=True),
                "Ingrédient": st.column_config.TextColumn(disabled=True),
                "Catégorie": st.column_config.TextColumn(disabled=True),
                "Unité": st.column_config.TextColumn(disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="ing_editor",
        )

        if st.button("💾 Appliquer les prix", type="primary"):
            for _, row in edited_ing.iterrows():
                ref = row["Réf."]
                st.session_state.prices_A[ref] = row["Prix Fourn. A (€)"]
                st.session_state.prices_B[ref] = row["Prix Fourn. B (€)"]
            st.success("✅ Prix mis à jour ! Les calculs sont recalculés automatiquement.")
            st.rerun()

        # Supplier comparison summary
        st.markdown('<div class="section-title">Impact Fournisseur A vs B sur le Food Cost</div>',
                    unsafe_allow_html=True)
        fc_a = compute_all_food_costs(st.session_state.prices_A)
        fc_b = compute_all_food_costs(st.session_state.prices_B)
        comp_rows = []
        for name in RECIPES:
            comp_rows.append({
                "Recette": f"{RECIPES[name]['emoji']} {name}",
                "Food Cost A (%)": fc_a[name]["food_cost_pct"],
                "Food Cost B (%)": fc_b[name]["food_cost_pct"],
                "Écart (pts)": round(fc_a[name]["food_cost_pct"] - fc_b[name]["food_cost_pct"], 1),
                "Économie B/portion (€)": round(fc_a[name]["raw_cost"] - fc_b[name]["raw_cost"], 3),
            })
        comp_df = pd.DataFrame(comp_rows)
        st.dataframe(
            comp_df.style.format({
                "Food Cost A (%)": "{:.1f}%",
                "Food Cost B (%)": "{:.1f}%",
                "Écart (pts)": "{:+.1f} pts",
                "Économie B/portion (€)": "{:+.3f} €",
            }).background_gradient(subset=["Écart (pts)"], cmap="RdYlGn"),
            use_container_width=True,
        )

    # ── Sales Mix ────────────────────────────────────────────────────────────
    with adv_tab2:
        st.markdown("Ajustez le nombre de portions vendues par jour (à activité de base).")
        mix_data = []
        for name, qty in st.session_state.sales_mix.items():
            recipe = RECIPES[name]
            mix_data.append({
                "Recette": f"{recipe['emoji']} {name}",
                "Catégorie": recipe["category"],
                "Portions/jour": qty,
                "Prix vente (€)": recipe["price"],
                "CA/jour (€)": round(qty * recipe["price"], 2),
            })
        mix_df = pd.DataFrame(mix_data)

        edited_mix = st.data_editor(
            mix_df,
            column_config={
                "Portions/jour": st.column_config.NumberColumn(
                    "Portions/jour", min_value=0, max_value=200, step=1),
                "Recette": st.column_config.TextColumn(disabled=True),
                "Catégorie": st.column_config.TextColumn(disabled=True),
                "Prix vente (€)": st.column_config.NumberColumn(
                    "Prix vente (€)", min_value=0.0, step=0.50, format="%.2f €"),
                "CA/jour (€)": st.column_config.NumberColumn(disabled=True, format="%.2f €"),
            },
            use_container_width=True,
            hide_index=True,
            key="mix_editor",
        )

        if st.button("💾 Appliquer le mix de ventes", type="primary"):
            for _, row in edited_mix.iterrows():
                recipe_name = row["Recette"].split(" ", 1)[1]
                if recipe_name in st.session_state.sales_mix:
                    st.session_state.sales_mix[recipe_name] = int(row["Portions/jour"])
            st.success("✅ Mix de ventes mis à jour !")
            st.rerun()

        total_ca_day = mix_df["CA/jour (€)"].sum()
        total_portions = mix_df["Portions/jour"].sum()
        st.info(f"**CA journalier estimé (base) :** {total_ca_day:,.2f} € | "
                f"**Total portions :** {total_portions:.0f}/jour | "
                f"**Ticket moyen :** {total_ca_day/max(total_portions,1):.2f} €")

        # Mix chart
        fig_mix = px.bar(
            mix_df, x="Recette", y="CA/jour (€)", color="Catégorie",
            title="CA journalier par recette (base)",
            color_discrete_sequence=["#C0392B", "#E67E22", "#2980B9", "#27AE60"],
        )
        fig_mix.update_layout(
            height=360, plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(tickangle=-30),
            yaxis=dict(ticksuffix=" €", gridcolor="#F0F0F0"),
            font=dict(family="Inter"),
            margin=dict(l=10, r=10, t=50, b=100),
        )
        st.plotly_chart(fig_mix, use_container_width=True)

    # ── Fixed Costs ──────────────────────────────────────────────────────────
    with adv_tab3:
        st.markdown("Modifiez les charges fixes mensuelles.")
        fc_edit_data = [{"Poste": k, "Montant mensuel (€)": v}
                        for k, v in st.session_state.fixed_costs.items()]
        fc_edit_df = pd.DataFrame(fc_edit_data)

        edited_fc = st.data_editor(
            fc_edit_df,
            column_config={
                "Poste": st.column_config.TextColumn(disabled=True),
                "Montant mensuel (€)": st.column_config.NumberColumn(
                    "Montant mensuel (€)", min_value=0, step=10, format="%.0f €"),
            },
            use_container_width=True,
            hide_index=True,
            key="fc_editor",
        )

        if st.button("💾 Appliquer les charges fixes", type="primary"):
            for _, row in edited_fc.iterrows():
                st.session_state.fixed_costs[row["Poste"]] = row["Montant mensuel (€)"]
            st.success("✅ Charges fixes mises à jour !")
            st.rerun()

        total_fc = sum(st.session_state.fixed_costs.values())
        st.metric("Total charges fixes mensuelles", f"{total_fc:,.0f} €",
                  f"+ {total_fc * 1.05:,.0f} € avec divers (+5%)")

        fig_fc_pie = px.pie(
            fc_edit_df, values="Montant mensuel (€)", names="Poste",
            title="Répartition des charges fixes",
            color_discrete_sequence=px.colors.sequential.Reds_r,
        )
        fig_fc_pie.update_layout(height=400, font=dict(family="Inter"),
                                  margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_fc_pie, use_container_width=True)

    # ── Seasonality ──────────────────────────────────────────────────────────
    with adv_tab4:
        st.markdown("Ajustez les coefficients de saisonnalité pour chaque mois "
                    "(1.0 = activité de base).")
        sea_data = [{"Mois": m, "Coefficient": st.session_state.seasonality[m]}
                    for m in MONTHS]
        sea_df = pd.DataFrame(sea_data)

        edited_sea = st.data_editor(
            sea_df,
            column_config={
                "Mois": st.column_config.TextColumn(disabled=True),
                "Coefficient": st.column_config.NumberColumn(
                    "Coefficient", min_value=0.1, max_value=3.0, step=0.05, format="%.2f"),
            },
            use_container_width=True,
            hide_index=True,
            key="sea_editor",
        )

        if st.button("💾 Appliquer la saisonnalité", type="primary"):
            for _, row in edited_sea.iterrows():
                st.session_state.seasonality[row["Mois"]] = row["Coefficient"]
            st.success("✅ Saisonnalité mise à jour !")
            st.rerun()

        fig_sea = go.Figure()
        fig_sea.add_trace(go.Bar(
            x=sea_df["Mois"], y=sea_df["Coefficient"],
            marker_color=["#C0392B" if v >= 1.2 else ("#F39C12" if v >= 0.8 else "#2980B9")
                          for v in sea_df["Coefficient"]],
            text=sea_df["Coefficient"].apply(lambda x: f"{x:.2f}"),
            textposition="outside",
        ))
        fig_sea.add_hline(y=1.0, line_dash="dash", line_color="#888",
                          annotation_text="Base 1.0")
        fig_sea.update_layout(
            title="Coefficients de saisonnalité — Six-Fours-les-Plages",
            height=340, plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(range=[0, 2.0], gridcolor="#F0F0F0"),
            font=dict(family="Inter"),
            margin=dict(l=10, r=10, t=50, b=40),
        )
        st.plotly_chart(fig_sea, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#888;font-size:0.8rem'>"
    "🍗 Pollo e Cucina Business Simulator · Six-Fours-les-Plages · "
    "Données modifiables — résultats indicatifs"
    "</div>",
    unsafe_allow_html=True,
)
