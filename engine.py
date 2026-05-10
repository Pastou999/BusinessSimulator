"""
Pollo e Cucina — Business Simulation Engine
Core data model: ingredients, recipes, P&L, scenarios
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# SEASONALITY (Six-Fours-les-Plages, Var)
# ─────────────────────────────────────────────────────────────────────────────
MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
          "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

SEASONALITY_BASE = {
    "Jan": 0.50, "Fév": 0.50, "Mar": 0.65, "Avr": 0.75,
    "Mai": 1.00, "Jun": 1.20, "Jul": 1.40, "Aoû": 1.50,
    "Sep": 1.10, "Oct": 0.70, "Nov": 0.55, "Déc": 0.50,
}

# ─────────────────────────────────────────────────────────────────────────────
# INGREDIENT CATALOGUE (Supplier A = estimated prices)
# ─────────────────────────────────────────────────────────────────────────────
INGREDIENTS_DEFAULT = {
    # ref: (name, category, unit, price_A, price_B)
    "V01": ("Poulet fermier Label Rouge", "Viande", "kg", 5.50, 4.80),
    "V02": ("Poulet conventionnel", "Viande", "kg", 3.80, 3.50),
    "V04": ("Cuisses de poulet", "Viande", "kg", 4.50, 4.10),
    "V06": ("Ailes de poulet", "Viande", "kg", 3.50, 3.20),
    "V07": ("Aiguillettes de poulet", "Viande", "kg", 9.00, 8.50),
    "V08": ("Prosciutto crudo", "Charcuterie", "kg", 28.00, 25.00),
    "L01": ("Mozzarella di bufala", "Laitier", "pièce", 1.80, 1.60),
    "L02": ("Mozzarella râpée", "Laitier", "kg", 7.50, 6.80),
    "L03": ("Ricotta fraîche", "Laitier", "kg", 5.50, 5.00),
    "L04": ("Parmesan 24 mois râpé", "Laitier", "kg", 22.00, 20.00),
    "L05": ("Pecorino romano râpé", "Laitier", "kg", 18.00, 16.50),
    "L06": ("Beurre doux", "Laitier", "kg", 8.00, 7.50),
    "E01": ("Riz arborio", "Épicerie", "kg", 2.20, 2.00),
    "E02": ("Tomates pelées (boîte 2.5kg)", "Épicerie", "boîte", 3.50, 3.20),
    "E03": ("Concentré de tomate", "Épicerie", "kg", 4.50, 4.00),
    "E04": ("Pesto rosso", "Épicerie", "kg", 12.00, 11.00),
    "E06": ("Olives noires dénoyautées", "Épicerie", "kg", 6.50, 6.00),
    "E07": ("Câpres au vinaigre", "Épicerie", "kg", 8.00, 7.50),
    "E09": ("Huile d'olive vierge extra", "Épicerie", "L", 6.50, 6.00),
    "E10": ("Huile de truffe blanche", "Épicerie", "L", 45.00, 42.00),
    "E11": ("Vinaigre balsamique", "Épicerie", "L", 8.00, 7.50),
    "E12": ("Farine type 00", "Épicerie", "kg", 1.20, 1.10),
    "E13": ("Chapelure panko", "Épicerie", "kg", 4.50, 4.20),
    "E14": ("Œufs frais (calibre M)", "Épicerie", "pièce", 0.22, 0.20),
    "E16": ("Huile de friture", "Épicerie", "L", 2.80, 2.60),
    "E17": ("Sel marin de Camargue", "Épicerie", "kg", 1.50, 1.40),
    "E18": ("Poivre noir moulu", "Épicerie", "kg", 12.00, 11.00),
    "E19": ("Paprika fumé", "Épicerie", "kg", 10.00, 9.50),
    "E20": ("Origan séché", "Épicerie", "kg", 12.00, 11.00),
    "E21": ("Romarin frais", "Épicerie", "botte", 1.50, 1.40),
    "E22": ("Ail frais", "Épicerie", "kg", 4.00, 3.80),
    "E23": ("Citrons frais", "Épicerie", "kg", 2.50, 2.30),
    "E24": ("Basilic frais", "Épicerie", "botte", 1.80, 1.70),
    "E25": ("Roquette fraîche", "Épicerie", "kg", 8.00, 7.50),
    "E26": ("Jeunes pousses", "Épicerie", "kg", 12.00, 11.00),
    "E27": ("Herbes de Provence", "Épicerie", "kg", 8.00, 7.50),
    "E28": ("Pignons de pin", "Épicerie", "kg", 35.00, 32.00),
    "B01": ("Focaccia artisanale", "Boulangerie", "pièce", 0.80, 0.72),
    "B02": ("Bun brioché", "Boulangerie", "pièce", 0.55, 0.50),
    "B03": ("Piadina", "Boulangerie", "pièce", 0.45, 0.42),
    "LG01": ("Pommes de terre grenailles", "Légumes", "kg", 2.20, 2.00),
    "LG02": ("Aubergines", "Légumes", "kg", 2.50, 2.30),
    "LG03": ("Poivrons rouges", "Légumes", "kg", 2.80, 2.60),
    "LG04": ("Courgettes", "Légumes", "kg", 1.80, 1.70),
    "LG05": ("Tomates cerises", "Légumes", "kg", 4.00, 3.80),
    "LG06": ("Oignons jaunes", "Légumes", "kg", 1.20, 1.10),
    "BV01": ("Citrons pour limonata", "Boissons", "kg", 2.50, 2.30),
    "BV02": ("Menthe fraîche", "Boissons", "botte", 1.50, 1.40),
    "BV03": ("Eau pétillante", "Boissons", "L", 0.60, 0.55),
    "BV04": ("Chinotto San Pellegrino", "Boissons", "pièce", 0.90, 0.85),
    "BV05": ("Aranciata Rossa", "Boissons", "pièce", 0.90, 0.85),
    "BV06": ("Bière artisanale Var", "Boissons", "pièce", 1.80, 1.65),
    "BV07": ("Rosé de Provence (75cl)", "Boissons", "bouteille", 5.50, 5.00),
    "EM01": ("Boîte carton kraft", "Emballage", "pièce", 0.18, 0.16),
    "EM02": ("Barquette carton", "Emballage", "pièce", 0.12, 0.11),
    "EM03": ("Papier ingraissable", "Emballage", "feuille", 0.04, 0.04),
    "EM04": ("Sac kraft poignées", "Emballage", "pièce", 0.15, 0.14),
    "EM05": ("Boîte poulet entier", "Emballage", "pièce", 0.35, 0.32),
    "EM06": ("Couverts biodégradables", "Emballage", "set", 0.08, 0.07),
}

# ─────────────────────────────────────────────────────────────────────────────
# RECIPES: (ingredient_ref, qty_per_portion)
# ─────────────────────────────────────────────────────────────────────────────
RECIPES = {
    "Milanaise Sando": {
        "price": 9.50,
        "emoji": "🥖",
        "category": "Snacking",
        "ingredients": [
            ("V01", 0.150), ("B01", 1.0), ("E04", 0.030),
            ("L01", 0.5),   ("E25", 0.020), ("E09", 0.010),
            ("E17", 0.002), ("EM01", 1.0), ("EM03", 1.0),
        ],
    },
    "Piadina Riviera": {
        "price": 8.50,
        "emoji": "🫓",
        "category": "Snacking",
        "ingredients": [
            ("V04", 0.130), ("B03", 1.0), ("L03", 0.060),
            ("E22", 0.005), ("E23", 0.030), ("L05", 0.020),
            ("E26", 0.020), ("E20", 0.002), ("E09", 0.008),
            ("EM03", 1.0),
        ],
    },
    "Burger Chicken Parm": {
        "price": 11.00,
        "emoji": "🍔",
        "category": "Snacking",
        "ingredients": [
            ("V01", 0.180), ("B02", 1.0), ("E02", 0.120),
            ("E03", 0.015), ("L02", 0.040), ("V08", 0.030),
            ("E24", 0.050), ("E22", 0.005), ("E09", 0.010),
            ("L06", 0.010), ("EM01", 1.0),
        ],
    },
    "Arancini Cacciatore (3 pcs)": {
        "price": 7.50,
        "emoji": "🍡",
        "category": "Snacking",
        "ingredients": [
            ("E01", 0.120), ("V01", 0.060), ("E02", 0.080),
            ("E06", 0.020), ("L01", 0.25),  ("E21", 0.020),
            ("LG06", 0.030), ("E22", 0.005), ("E12", 0.030),
            ("E13", 0.040), ("E14", 1.0),   ("E16", 0.050),
            ("E09", 0.010), ("L04", 0.015), ("EM02", 1.0),
        ],
    },
    "Pollo Fries": {
        "price": 5.50,
        "emoji": "🍟",
        "category": "Snacking",
        "ingredients": [
            ("V07", 0.120), ("E12", 0.020), ("L04", 0.025),
            ("E10", 0.003), ("E16", 0.060), ("E17", 0.002),
            ("E19", 0.002), ("EM02", 1.0),
        ],
    },
    "Poulet Entier Signature": {
        "price": 16.50,
        "emoji": "🍗",
        "category": "Rôtisserie",
        "ingredients": [
            ("V01", 1.800), ("E27", 0.010), ("E22", 0.010),
            ("E23", 0.050), ("E09", 0.020), ("E17", 0.008),
            ("E18", 0.003), ("E21", 0.030), ("EM05", 1.0),
            ("EM04", 1.0),
        ],
    },
    "Demi-Poulet": {
        "price": 9.00,
        "emoji": "🍗",
        "category": "Rôtisserie",
        "ingredients": [
            ("V01", 0.900), ("E27", 0.005), ("E22", 0.005),
            ("E09", 0.010), ("E17", 0.004), ("EM04", 1.0),
        ],
    },
    "Quart de Poulet": {
        "price": 5.50,
        "emoji": "🍗",
        "category": "Rôtisserie",
        "ingredients": [
            ("V01", 0.450), ("E27", 0.003), ("E09", 0.005),
            ("E17", 0.002), ("EM03", 1.0),
        ],
    },
    "Patate Grenailles au Jus": {
        "price": 4.00,
        "emoji": "🥔",
        "category": "Accompagnement",
        "ingredients": [
            ("LG01", 0.200), ("E21", 0.020), ("E22", 0.005),
            ("E17", 0.002), ("EM02", 1.0),
        ],
    },
    "Caponata Sicilienne": {
        "price": 4.50,
        "emoji": "🫑",
        "category": "Accompagnement",
        "ingredients": [
            ("LG02", 0.100), ("LG03", 0.080), ("LG04", 0.060),
            ("LG05", 0.040), ("E28", 0.010), ("E07", 0.010),
            ("E11", 0.010), ("E09", 0.015), ("E17", 0.003),
            ("EM02", 1.0),
        ],
    },
    "Ailes Aperitivo": {
        "price": 6.00,
        "emoji": "🍖",
        "category": "Accompagnement",
        "ingredients": [
            ("V06", 0.250), ("E23", 0.040), ("E21", 0.020),
            ("E22", 0.005), ("E09", 0.015), ("E17", 0.003),
            ("EM02", 1.0),
        ],
    },
    "Limonata Maison": {
        "price": 3.50,
        "emoji": "🍋",
        "category": "Boisson",
        "ingredients": [
            ("BV01", 0.080), ("BV02", 0.100), ("BV03", 0.500),
            ("E17", 0.020), ("EM06", 1.0),
        ],
    },
    "Bière Artisanale du Var": {
        "price": 5.00,
        "emoji": "🍺",
        "category": "Boisson",
        "ingredients": [("BV06", 1.0), ("EM06", 1.0)],
    },
    "Rosé de Provence": {
        "price": 4.00,
        "emoji": "🥂",
        "category": "Boisson",
        "ingredients": [("BV07", 0.167), ("EM06", 1.0)],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DAILY SALES MIX (default portions per day at base activity)
# ─────────────────────────────────────────────────────────────────────────────
SALES_MIX_DEFAULT = {
    "Milanaise Sando": 15,
    "Piadina Riviera": 12,
    "Burger Chicken Parm": 10,
    "Arancini Cacciatore (3 pcs)": 8,
    "Pollo Fries": 15,
    "Poulet Entier Signature": 15,
    "Demi-Poulet": 8,
    "Quart de Poulet": 10,
    "Patate Grenailles au Jus": 20,
    "Caponata Sicilienne": 10,
    "Ailes Aperitivo": 8,
    "Limonata Maison": 18,
    "Bière Artisanale du Var": 12,
    "Rosé de Provence": 10,
}

# ─────────────────────────────────────────────────────────────────────────────
# FIXED COSTS (monthly, €)
# ─────────────────────────────────────────────────────────────────────────────
FIXED_COSTS_DEFAULT = {
    "Loyer / redevance emplacement": 800,
    "Assurance professionnelle": 150,
    "Comptable": 120,
    "Abonnement électrique": 200,
    "Eau / assainissement": 50,
    "Téléphone + internet": 50,
    "Logiciel caisse": 30,
    "Frais bancaires + TPE": 40,
    "Publicité / réseaux sociaux": 100,
    "Emballages & consommables": 200,
    "Entretien / maintenance": 100,
}

# ─────────────────────────────────────────────────────────────────────────────
# FORCE MAJEURE EVENTS
# ─────────────────────────────────────────────────────────────────────────────
FORCE_MAJEURE_EVENTS = {
    "🌩️ Tempête / Mauvais temps (semaine)": {
        "description": "Épisode météo violent — fermeture 5 jours, -70% activité sur la période",
        "cover_multiplier": 0.30,
        "cost_multiplier": 1.00,
        "energy_multiplier": 0.50,
        "duration_days": 7,
        "fixed_cost_multiplier": 1.00,
    },
    "🦠 Épidémie / Fermeture administrative": {
        "description": "Fermeture forcée 30 jours — zéro CA, charges fixes maintenues",
        "cover_multiplier": 0.00,
        "cost_multiplier": 1.00,
        "energy_multiplier": 0.10,
        "duration_days": 30,
        "fixed_cost_multiplier": 1.00,
    },
    "🔥 Incendie matériel (rôtissoire HS)": {
        "description": "Rôtissoire hors service — perte de 60% du CA rôtisserie pendant 2 semaines",
        "cover_multiplier": 0.70,
        "cost_multiplier": 1.00,
        "energy_multiplier": 0.80,
        "duration_days": 14,
        "fixed_cost_multiplier": 1.00,
    },
    "📈 Flambée prix matières premières (+30%)": {
        "description": "Crise d'approvisionnement — coût des matières premières +30% pendant 3 mois",
        "cover_multiplier": 1.00,
        "cost_multiplier": 1.30,
        "energy_multiplier": 1.00,
        "duration_days": 90,
        "fixed_cost_multiplier": 1.00,
    },
    "⚡ Coupure électrique prolongée (1 semaine)": {
        "description": "Panne réseau — fonctionnement au gaz uniquement, -40% capacité",
        "cover_multiplier": 0.60,
        "cost_multiplier": 1.00,
        "energy_multiplier": 1.50,
        "duration_days": 7,
        "fixed_cost_multiplier": 1.00,
    },
    "🏗️ Travaux voirie (accès difficile 1 mois)": {
        "description": "Chantier municipal devant le container — -50% de passage",
        "cover_multiplier": 0.50,
        "cost_multiplier": 1.00,
        "energy_multiplier": 1.00,
        "duration_days": 30,
        "fixed_cost_multiplier": 1.00,
    },
    "🎉 Événement exceptionnel (festival, marché)": {
        "description": "Événement local — +80% de fréquentation pendant 3 jours",
        "cover_multiplier": 1.80,
        "cost_multiplier": 1.00,
        "energy_multiplier": 1.20,
        "duration_days": 3,
        "fixed_cost_multiplier": 1.00,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compute_recipe_cost(recipe_name: str, prices: Dict[str, float]) -> float:
    """Compute the raw material cost for one portion of a recipe."""
    recipe = RECIPES[recipe_name]
    total = 0.0
    for ref, qty in recipe["ingredients"]:
        price = prices.get(ref, INGREDIENTS_DEFAULT.get(ref, ("", "", "", 0, 0))[3])
        total += price * qty
    return round(total, 3)

def compute_all_food_costs(prices: Dict[str, float]) -> Dict[str, dict]:
    """Compute food cost metrics for all recipes."""
    results = {}
    for name, recipe in RECIPES.items():
        cost = compute_recipe_cost(name, prices)
        sell = recipe["price"]
        results[name] = {
            "emoji": recipe["emoji"],
            "category": recipe["category"],
            "sell_price": sell,
            "raw_cost": cost,
            "margin": round(sell - cost, 2),
            "food_cost_pct": round(cost / sell * 100, 1) if sell > 0 else 0,
            "margin_pct": round((sell - cost) / sell * 100, 1) if sell > 0 else 0,
        }
    return results

def compute_monthly_pl(
    sales_mix: Dict[str, int],
    prices: Dict[str, float],
    fixed_costs: Dict[str, float],
    days_per_week: float,
    salary_net: float,
    tns_rate: float,
    loan_monthly: float,
    energy_daily: float,
    seasonality: Dict[str, float],
    force_majeure_event: Optional[str] = None,
    fm_month: Optional[str] = None,
    sell_prices: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Compute the 12-month P&L.
    Returns a DataFrame with one row per month.
    """
    # Use custom sell prices if provided
    effective_sell = {}
    for name, recipe in RECIPES.items():
        if sell_prices and name in sell_prices:
            effective_sell[name] = sell_prices[name]
        else:
            effective_sell[name] = recipe["price"]

    food_costs = compute_all_food_costs(prices)
    days_per_month = days_per_week * (52 / 12)
    salary_total = salary_net * (1 + tns_rate)
    total_fixed = sum(fixed_costs.values()) * 1.05  # +5% divers

    rows = []
    for month in MONTHS:
        coef = seasonality.get(month, 1.0)

        # Apply force majeure if applicable
        fm_cover_mult = 1.0
        fm_cost_mult = 1.0
        fm_energy_mult = 1.0
        if force_majeure_event and fm_month and month == fm_month:
            ev = FORCE_MAJEURE_EVENTS[force_majeure_event]
            days_in_month = 26
            fm_days = min(ev["duration_days"], days_in_month)
            normal_days = days_in_month - fm_days
            fm_cover_mult = (normal_days + fm_days * ev["cover_multiplier"]) / days_in_month
            fm_cost_mult = (normal_days + fm_days * ev["cost_multiplier"]) / days_in_month
            fm_energy_mult = (normal_days + fm_days * ev["energy_multiplier"]) / days_in_month

        # Revenue
        ca = 0.0
        raw_cost = 0.0
        for name, daily_qty in sales_mix.items():
            monthly_qty = daily_qty * days_per_month * coef * fm_cover_mult
            sell = effective_sell[name]
            cost = food_costs[name]["raw_cost"] * fm_cost_mult
            ca += monthly_qty * sell
            raw_cost += monthly_qty * cost

        # Gross margin
        gross_margin = ca - raw_cost
        food_cost_pct = (raw_cost / ca * 100) if ca > 0 else 0

        # Variable costs
        energy_cost = energy_daily * days_per_month * coef * fm_energy_mult

        # Total charges
        total_charges = total_fixed + energy_cost + salary_total + loan_monthly

        # EBITDA & Net
        ebitda = gross_margin - total_fixed - energy_cost - salary_total
        net_result = ebitda - loan_monthly

        rows.append({
            "Mois": month,
            "Coeff. Saison.": coef,
            "CA HT (€)": round(ca, 0),
            "Coût MP (€)": round(raw_cost, 0),
            "Marge Brute (€)": round(gross_margin, 0),
            "Food Cost %": round(food_cost_pct, 1),
            "Marge Brute %": round((gross_margin / ca * 100) if ca > 0 else 0, 1),
            "Charges Fixes (€)": round(total_fixed, 0),
            "Énergie (€)": round(energy_cost, 0),
            "RH Gérant (€)": round(salary_total, 0),
            "Remb. Emprunt (€)": round(loan_monthly, 0),
            "EBE (€)": round(ebitda, 0),
            "Résultat Net (€)": round(net_result, 0),
        })

    df = pd.DataFrame(rows)
    return df

def compute_breakeven(
    fixed_costs: Dict[str, float],
    salary_net: float,
    tns_rate: float,
    loan_monthly: float,
    energy_daily: float,
    avg_food_cost_pct: float,
    avg_energy_pct: float = 0.05,
) -> dict:
    """Compute monthly break-even metrics."""
    salary_total = salary_net * (1 + tns_rate)
    total_fixed = sum(fixed_costs.values()) * 1.05
    days_per_month = 26
    energy_monthly = energy_daily * days_per_month

    total_fixed_all = total_fixed + salary_total + loan_monthly + energy_monthly
    variable_rate = avg_food_cost_pct / 100 + avg_energy_pct / 100
    contribution_margin_rate = 1 - variable_rate

    ca_seuil = total_fixed_all / contribution_margin_rate if contribution_margin_rate > 0 else 0
    ca_seuil_day = ca_seuil / days_per_month

    # Weighted average selling price (from default sales mix)
    total_qty = sum(SALES_MIX_DEFAULT.values())
    avg_sell = sum(
        RECIPES[n]["price"] * q for n, q in SALES_MIX_DEFAULT.items()
    ) / total_qty if total_qty > 0 else 9.0

    covers_seuil = ca_seuil_day / avg_sell if avg_sell > 0 else 0

    return {
        "ca_seuil_mensuel": round(ca_seuil, 0),
        "ca_seuil_journalier": round(ca_seuil_day, 0),
        "couverts_seuil": round(covers_seuil, 0),
        "total_charges_fixes": round(total_fixed_all, 0),
        "taux_marge_contribution": round(contribution_margin_rate * 100, 1),
    }

def compute_scenarios(
    prices: Dict[str, float],
    fixed_costs: Dict[str, float],
    salary_net: float,
    tns_rate: float,
    loan_monthly: float,
    energy_daily: float,
) -> pd.DataFrame:
    """Compute P&L for 6 predefined scenarios."""
    scenarios = [
        ("🔴 Pire cas", 0.40, "Hiver, mauvais temps"),
        ("🟠 Bas de fourchette", 0.55, "Basse saison"),
        ("🟡 Seuil de rentabilité", 0.72, "Point mort"),
        ("🟢 Hypothèse de base", 1.00, "Saison normale"),
        ("🔵 Bonne saison", 1.45, "Été, juillet-août"),
        ("⭐ Excellente saison", 1.90, "Juillet-août + événements"),
    ]

    food_costs = compute_all_food_costs(prices)
    days_per_month = 26
    salary_total = salary_net * (1 + tns_rate)
    total_fixed = sum(fixed_costs.values()) * 1.05
    energy_monthly = energy_daily * days_per_month

    rows = []
    for label, activity_mult, comment in scenarios:
        ca = 0.0
        raw_cost = 0.0
        for name, daily_qty in SALES_MIX_DEFAULT.items():
            monthly_qty = daily_qty * days_per_month * activity_mult
            ca += monthly_qty * RECIPES[name]["price"]
            raw_cost += monthly_qty * food_costs[name]["raw_cost"]

        gross_margin = ca - raw_cost
        food_cost_pct = (raw_cost / ca * 100) if ca > 0 else 0
        ebitda = gross_margin - total_fixed - energy_monthly * activity_mult - salary_total
        net = ebitda - loan_monthly

        rows.append({
            "Scénario": label,
            "Activité": f"{activity_mult:.0%}",
            "CA mensuel (€)": round(ca, 0),
            "Coût MP (€)": round(raw_cost, 0),
            "Food Cost %": round(food_cost_pct, 1),
            "Marge Brute (€)": round(gross_margin, 0),
            "EBE (€)": round(ebitda, 0),
            "Résultat Net (€)": round(net, 0),
            "Commentaire": comment,
        })

    return pd.DataFrame(rows)

def compute_monte_carlo(
    prices: Dict[str, float],
    fixed_costs: Dict[str, float],
    salary_net: float,
    tns_rate: float,
    loan_monthly: float,
    energy_daily: float,
    n_simulations: int = 2000,
    activity_mean: float = 1.0,
    activity_std: float = 0.25,
    cost_std_pct: float = 0.10,
) -> np.ndarray:
    """Run Monte Carlo simulation on monthly net result."""
    food_costs = compute_all_food_costs(prices)
    days_per_month = 26
    salary_total = salary_net * (1 + tns_rate)
    total_fixed = sum(fixed_costs.values()) * 1.05
    energy_monthly = energy_daily * days_per_month

    results = []
    rng = np.random.default_rng(42)

    for _ in range(n_simulations):
        activity = max(0.1, rng.normal(activity_mean, activity_std))
        cost_shock = rng.normal(1.0, cost_std_pct)

        ca = 0.0
        raw_cost = 0.0
        for name, daily_qty in SALES_MIX_DEFAULT.items():
            monthly_qty = daily_qty * days_per_month * activity
            ca += monthly_qty * RECIPES[name]["price"]
            raw_cost += monthly_qty * food_costs[name]["raw_cost"] * cost_shock

        gross_margin = ca - raw_cost
        ebitda = gross_margin - total_fixed - energy_monthly * activity - salary_total
        net = ebitda - loan_monthly
        results.append(net)

    return np.array(results)
