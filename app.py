import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
import math

st.set_page_config(
    page_title="SIPM Catamarca — Inteligencia Productiva",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA = Path(__file__).with_name("matriz_sipm_v2_demo.csv")

@st.cache_data
def load_data():
    df = pd.read_csv(DATA)

    # Normalización robusta de nombres de eslabonamiento.
    # Esto evita inconsistencias si en el CSV queda algún valor antiguo
    # o con diferencias de mayúsculas/minúsculas.
    df["tipo_eslabonamiento"] = (
        df["tipo_eslabonamiento"]
        .astype(str)
        .str.strip()
        .replace({
            "Hacia atrás": "Aguas arriba",
            "Hacia atras": "Aguas arriba",
            "hacia atrás": "Aguas arriba",
            "hacia atras": "Aguas arriba",
            "Aguas Arriba": "Aguas arriba",
            "aguas arriba": "Aguas arriba",
            "Hacia adelante": "Aguas abajo",
            "hacia adelante": "Aguas abajo",
            "Aguas Abajo": "Aguas abajo",
            "aguas abajo": "Aguas abajo"
        })
    )

    df["captura_local_usd_demo"] = df["demanda_anual_usd_demo"] * df["participacion_catamarca_pct_demo"] / 100
    df["gasto_fuera_catamarca_usd_demo"] = df["demanda_anual_usd_demo"] - df["captura_local_usd_demo"]
    df["puntaje_oportunidad_demo"] = (
        (1-df["participacion_catamarca_pct_demo"]/100)*45
        + df["gasto_fuera_catamarca_usd_demo"].clip(lower=10).apply(lambda x:min(1, math.log10(x)/8))*35
        + (df["empleo_local_potencial_demo"]/250).clip(upper=1)*20
    ).round()
    df["prioridad_demo"] = pd.cut(
        df["puntaje_oportunidad_demo"],
        bins=[-1,49,69,101],
        labels=["Consolidar","Media","Alta"]
    ).astype(str)
    return df

df = load_data()

# ------------------------------------------------
# UTILIDADES PARA ESCENARIOS
# ------------------------------------------------
# Columnas originales de la matriz. Las variables calculadas se regeneran
# automáticamente para evitar inconsistencias al editar o cargar escenarios.
SCENARIO_DERIVED_COLUMNS = [
    "captura_local_usd_demo",
    "gasto_fuera_catamarca_usd_demo",
    "puntaje_oportunidad_demo",
    "prioridad_demo",
]

SCENARIO_REQUIRED_COLUMNS = [
    c for c in df.columns if c not in SCENARIO_DERIVED_COLUMNS
]


def prepare_scenario_data(frame):
    """Normaliza y recalcula un DataFrame de escenario sin alterar la base SIPM."""
    out = frame.copy()

    # Acepta terminología histórica para que archivos anteriores sigan funcionando.
    if "tipo_eslabonamiento" in out.columns:
        out["tipo_eslabonamiento"] = (
            out["tipo_eslabonamiento"]
            .astype(str)
            .str.strip()
            .replace({
                "Hacia atrás": "Aguas arriba",
                "Hacia atras": "Aguas arriba",
                "hacia atrás": "Aguas arriba",
                "hacia atras": "Aguas arriba",
                "Aguas Arriba": "Aguas arriba",
                "aguas arriba": "Aguas arriba",
                "Hacia adelante": "Aguas abajo",
                "hacia adelante": "Aguas abajo",
                "Aguas Abajo": "Aguas abajo",
                "aguas abajo": "Aguas abajo",
            })
        )

    # Variables numéricas críticas: conversión defensiva.
    numeric_cols = [
        "demanda_anual_usd_demo",
        "participacion_catamarca_pct_demo",
        "participacion_resto_arg_pct_demo",
        "participacion_importada_pct_demo",
        "empleo_local_potencial_demo",
    ]
    for col in numeric_cols:
        if col in out.columns:
            # Forzamos float porque los escenarios pueden generar decimales.
            # Pandas 3.x ya no permite asignar floats dentro de columnas int
            # mediante .loc sin una conversión explícita.
            out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)

    # Límites lógicos para porcentajes y valores que no deberían ser negativos.
    for col in [
        "participacion_catamarca_pct_demo",
        "participacion_resto_arg_pct_demo",
        "participacion_importada_pct_demo",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(0).clip(lower=0, upper=100)

    if "demanda_anual_usd_demo" in out.columns:
        out["demanda_anual_usd_demo"] = out["demanda_anual_usd_demo"].fillna(0).clip(lower=0)
    if "empleo_local_potencial_demo" in out.columns:
        out["empleo_local_potencial_demo"] = out["empleo_local_potencial_demo"].fillna(0).clip(lower=0)

    # Recalcular siempre los indicadores derivados.
    out["captura_local_usd_demo"] = (
        out["demanda_anual_usd_demo"] * out["participacion_catamarca_pct_demo"] / 100
    )
    out["gasto_fuera_catamarca_usd_demo"] = (
        out["demanda_anual_usd_demo"] - out["captura_local_usd_demo"]
    )
    out["puntaje_oportunidad_demo"] = (
        (1 - out["participacion_catamarca_pct_demo"] / 100) * 45
        + out["gasto_fuera_catamarca_usd_demo"].clip(lower=10).apply(
            lambda x: min(1, math.log10(x) / 8)
        ) * 35
        + (out["empleo_local_potencial_demo"] / 250).clip(upper=1) * 20
    ).round()
    out["prioridad_demo"] = pd.cut(
        out["puntaje_oportunidad_demo"],
        bins=[-1, 49, 69, 101],
        labels=["Consolidar", "Media", "Alta"],
    ).astype(str)
    return out


def validate_scenario_file(frame):
    missing = [c for c in SCENARIO_REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        return False, missing
    return True, []


def filter_like_sidebar(frame):
    """Aplica al escenario exactamente los mismos filtros laterales del tablero."""
    return frame[
        frame["mineral"].isin(minerals)
        & frame["tipo_eslabonamiento"].isin(linkages)
        & frame["etapa_proyecto"].isin(stages)
        & frame["territorio_potencial"].isin(territories)
    ].copy()


def scenario_kpis(frame):
    demand = float(frame["demanda_anual_usd_demo"].sum()) if not frame.empty else 0.0
    local_value = float(frame["captura_local_usd_demo"].sum()) if not frame.empty else 0.0
    outside_value = float(frame["gasto_fuera_catamarca_usd_demo"].sum()) if not frame.empty else 0.0
    employment = float(frame["empleo_local_potencial_demo"].sum()) if not frame.empty else 0.0
    local_share = local_value / demand if demand else 0.0
    return {
        "demanda": demand,
        "captura_valor": local_value,
        "captura_pct": local_share,
        "gasto_fuera": outside_value,
        "empleo": employment,
    }


def rebalance_participations(frame, indices):
    """Reescala las tres participaciones para que sumen 100 manteniendo su relación relativa.

    La conversión explícita a float evita errores de dtype en pandas 3.x
    cuando una base CSV/Excel trae porcentajes guardados como enteros.
    """
    frame = frame.copy()

    cols = [
        "participacion_catamarca_pct_demo",
        "participacion_resto_arg_pct_demo",
        "participacion_importada_pct_demo",
    ]

    # Conversión defensiva: los porcentajes del escenario deben admitir decimales.
    for col in cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0).astype(float)

    # Normalizamos los índices para evitar problemas si provienen de filtros,
    # data_editor o archivos externos.
    selected_indices = frame.index.intersection(pd.Index(indices))

    if len(selected_indices) == 0:
        return frame

    values = frame.loc[selected_indices, cols].clip(lower=0).astype(float)
    totals = values.sum(axis=1)
    valid = totals > 0

    if valid.any():
        valid_idx = values.index[valid]
        normalized = (
            values.loc[valid_idx]
            .div(totals.loc[valid_idx], axis=0)
            .mul(100.0)
        )
        # Asignación por columna para mantener dtype float de forma estable
        # en pandas 3.x.
        for col in cols:
            frame.loc[valid_idx, col] = normalized[col].to_numpy(dtype=float)

    if (~valid).any():
        zero_idx = values.index[~valid]
        frame.loc[zero_idx, "participacion_catamarca_pct_demo"] = 100.0
        frame.loc[zero_idx, "participacion_resto_arg_pct_demo"] = 0.0
        frame.loc[zero_idx, "participacion_importada_pct_demo"] = 0.0

    return frame



def group_scenario_delta(base_frame, scenario_frame, group_col):
    """Compara base vs escenario por una dimensión y devuelve deltas económicos y laborales."""
    def agg(frame):
        if frame.empty:
            return pd.DataFrame(columns=[group_col, "demanda", "captura", "gasto_fuera", "empleo"])
        return frame.groupby(group_col, as_index=False).agg(
            demanda=("demanda_anual_usd_demo", "sum"),
            captura=("captura_local_usd_demo", "sum"),
            gasto_fuera=("gasto_fuera_catamarca_usd_demo", "sum"),
            empleo=("empleo_local_potencial_demo", "sum"),
        )

    b = agg(base_frame).rename(columns={
        "demanda":"demanda_base", "captura":"captura_base",
        "gasto_fuera":"gasto_fuera_base", "empleo":"empleo_base"
    })
    s = agg(scenario_frame).rename(columns={
        "demanda":"demanda_escenario", "captura":"captura_escenario",
        "gasto_fuera":"gasto_fuera_escenario", "empleo":"empleo_escenario"
    })
    comp = b.merge(s, on=group_col, how="outer").fillna(0)
    for metric in ["demanda", "captura", "gasto_fuera", "empleo"]:
        comp[f"delta_{metric}"] = comp[f"{metric}_escenario"] - comp[f"{metric}_base"]
    comp["captura_pct_base"] = comp["captura_base"].div(comp["demanda_base"].replace(0, pd.NA)).fillna(0) * 100
    comp["captura_pct_escenario"] = comp["captura_escenario"].div(comp["demanda_escenario"].replace(0, pd.NA)).fillna(0) * 100
    comp["delta_captura_pp"] = comp["captura_pct_escenario"] - comp["captura_pct_base"]
    return comp


def scenario_change_context(base_frame, scenario_frame):
    """Resumen agregado utilizado por distintas pestañas y por el motor de políticas."""
    b = scenario_kpis(base_frame)
    s = scenario_kpis(scenario_frame)
    return {
        "base": b,
        "scenario": s,
        "delta_demanda": s["demanda"] - b["demanda"],
        "delta_captura": s["captura_valor"] - b["captura_valor"],
        "delta_gasto_fuera": s["gasto_fuera"] - b["gasto_fuera"],
        "delta_empleo": s["empleo"] - b["empleo"],
        "delta_captura_pp": (s["captura_pct"] - b["captura_pct"]) * 100,
    }


def dynamic_policy_actions(base_frame, scenario_frame):
    """Genera acciones de política a partir de cambios observados entre la base y el escenario.

    Es deliberadamente un motor de reglas transparente: no pretende reemplazar el análisis técnico,
    sino convertir señales de la matriz en una agenda inicial de decisiones verificables.
    """
    if scenario_frame.empty:
        return []

    ctx = scenario_change_context(base_frame, scenario_frame)
    actions = []

    # 1) Compras anticipadas / desarrollo de proveedores según demanda y gasto externo.
    sector_delta = group_scenario_delta(base_frame, scenario_frame, "macrosector")
    if not sector_delta.empty:
        top_demand = sector_delta.sort_values("delta_demanda", ascending=False).iloc[0]
        top_outside = sector_delta.sort_values("gasto_fuera_escenario", ascending=False).iloc[0]
        top_local_gain = sector_delta.sort_values("delta_captura_pp", ascending=False).iloc[0]

        if ctx["delta_demanda"] > 0:
            actions.append({
                "prioridad":"Alta",
                "frente":"Compras anticipadas",
                "evidencia":f"La demanda del escenario aumenta US$ {ctx['delta_demanda']/1e6:,.1f} M. El mayor crecimiento aparece en {top_demand['macrosector']}.",
                "accion":"Solicitar y consolidar planes agregados de compra a 12–36 meses; publicar categorías, especificaciones generales y cronogramas para que la oferta local pueda invertir antes de las licitaciones.",
                "actores":"Minería + Producción + empresas mineras + cámaras",
            })

        if ctx["delta_gasto_fuera"] > 0 or ctx["delta_captura_pp"] < 0:
            actions.append({
                "prioridad":"Alta",
                "frente":"Desarrollo de proveedores",
                "evidencia":f"El gasto fuera de Catamarca queda en US$ {ctx['scenario']['gasto_fuera']/1e6:,.1f} M. {top_outside['macrosector']} concentra una de las mayores brechas.",
                "accion":"Abrir una mesa sectorial específica: mapear proveedores locales, homologaciones, escala, capital de trabajo y barreras de compra; definir un plan de cierre de brechas con metas verificables.",
                "actores":"Producción + CAPEM + cámaras + banca/CFI + empresas",
            })
        elif ctx["delta_captura_pp"] > 0.5:
            actions.append({
                "prioridad":"Media/Alta",
                "frente":"Consolidación y escala",
                "evidencia":f"La captura local mejora {ctx['delta_captura_pp']:+.1f} p.p. En {top_local_gain['macrosector']} se observa uno de los mayores avances.",
                "accion":"Consolidar proveedores que ganan participación: productividad, financiamiento, calidad, consorcios y estrategia comercial para abastecer también Salta, Jujuy y otros mercados mineros.",
                "actores":"Producción + empresas locales + cámaras + agencias de inversión",
            })

    # 2) Aguas abajo: prefactibilidad e inversión.
    b_fw = base_frame[base_frame["tipo_eslabonamiento"] == "Aguas abajo"]
    s_fw = scenario_frame[scenario_frame["tipo_eslabonamiento"] == "Aguas abajo"]
    fw_ctx = scenario_change_context(b_fw, s_fw) if (not b_fw.empty or not s_fw.empty) else None
    if fw_ctx and (fw_ctx["delta_demanda"] > 0 or fw_ctx["scenario"]["gasto_fuera"] > 0):
        high_complex = s_fw[s_fw["complejidad_tecnica"].astype(str).str.lower().isin(["alta", "muy alta"])]
        low_capacity = s_fw[s_fw["capacidad_local_demo"].astype(str).str.lower().isin(["incipiente", "parcial"])]
        if not high_complex.empty or not low_capacity.empty:
            actions.append({
                "prioridad":"Estratégica",
                "frente":"Industrialización / Aguas abajo",
                "evidencia":f"El escenario aguas abajo moviliza US$ {fw_ctx['scenario']['demanda']/1e6:,.1f} M y combina eslabones de complejidad elevada con capacidades locales aún parciales o incipientes.",
                "accion":"Seleccionar 2–3 eslabones y realizar prefactibilidad: escala mínima, energía, agua, logística, tecnología, socios, mercado regional y CAPEX. Diferenciar qué conviene desarrollar localmente, atraer como inversión o integrar regionalmente.",
                "actores":"Producción + Minería + Inversiones + UNCA + INTI + privados",
            })

    # 3) Territorio: infraestructura y formación localizada.
    terr = group_scenario_delta(base_frame, scenario_frame, "territorio_potencial")
    if not terr.empty:
        terr["presion"] = terr["delta_demanda"].clip(lower=0)/1e6 + terr["delta_empleo"].clip(lower=0)
        t = terr.sort_values("presion", ascending=False).iloc[0]
        if t["presion"] > 0:
            actions.append({
                "prioridad":"Alta",
                "frente":"Desarrollo territorial",
                "evidencia":f"{t['territorio_potencial']} concentra el mayor aumento combinado del escenario: Δ demanda US$ {t['delta_demanda']/1e6:,.1f} M y Δ empleo {t['delta_empleo']:+,.0f}.",
                "accion":"Preparar una agenda territorial específica: infraestructura habilitante, formación local, logística, suelo/servicios productivos y vinculación de proveedores del territorio con los nuevos requerimientos.",
                "actores":"Provincia + municipio + Educación + Producción + Infraestructura",
            })

    # 4) Capital humano: perfiles con mayor incremento equivalente.
    bp = estimate_profiles(base_frame)
    sp = estimate_profiles(scenario_frame)
    if not sp.empty:
        bp2 = bp.rename(columns={"personas_demo":"base"}) if not bp.empty else pd.DataFrame(columns=["perfil","base"])
        sp2 = sp.rename(columns={"personas_demo":"escenario"})
        pc = bp2.merge(sp2, on="perfil", how="outer").fillna(0)
        pc["delta"] = pc["escenario"] - pc["base"]
        p = pc.sort_values("delta", ascending=False).iloc[0]
        if p["delta"] > 0:
            horizon, edu_action, actors = education_action(p["perfil"])
            actions.append({
                "prioridad":"Alta" if p["delta"] >= 25 else "Media",
                "frente":"Capital humano",
                "evidencia":f"El perfil con mayor incremento equivalente es {p['perfil']}: {p['delta']:+,.0f} personas respecto de la base demostrativa.",
                "accion":f"{edu_action} Horizonte sugerido: {horizon}.",
                "actores":actors,
            })

    # 5) Riesgo de suministro: criticidad alta + baja captura local.
    risky = scenario_frame[
        (scenario_frame["criticidad"].astype(str).str.lower() == "alta") &
        (scenario_frame["participacion_catamarca_pct_demo"] < 30)
    ].copy()
    if not risky.empty:
        risky = risky.sort_values("gasto_fuera_catamarca_usd_demo", ascending=False)
        r = risky.iloc[0]
        actions.append({
            "prioridad":"Alta",
            "frente":"Seguridad de abastecimiento",
            "evidencia":f"{r['macrosector']} · {r['requerimiento_o_producto']} combina criticidad alta, captura local de {r['participacion_catamarca_pct_demo']:.0f}% y gasto externo relevante.",
            "accion":"No tratarlo sólo como sustitución de importaciones: evaluar riesgo de interrupción, stock crítico, proveedores alternativos, contratos marco, homologación y capacidad local/regional de respuesta.",
            "actores":"Minería + empresas + proveedores + logística + Producción",
        })

    # Si no hubo señales fuertes, mantener una agenda de monitoreo.
    if not actions:
        actions.append({
            "prioridad":"Seguimiento",
            "frente":"Monitoreo del escenario",
            "evidencia":"Los cambios aplicados no generan, con las reglas demostrativas actuales, una alteración estructural significativa de los indicadores agregados.",
            "accion":"Mantener seguimiento por sector, territorio y perfil; validar supuestos con empresas y actualizar la matriz antes de diseñar instrumentos específicos.",
            "actores":"Unidad SIPM + Minería + Producción",
        })

    return actions[:7]


def profile_delta_table(base_frame, scenario_frame):
    bp = estimate_profiles(base_frame)
    sp = estimate_profiles(scenario_frame)
    if bp.empty and sp.empty:
        return pd.DataFrame(columns=["perfil", "base", "escenario", "delta"])
    bp = bp.rename(columns={"personas_demo":"base"}) if not bp.empty else pd.DataFrame(columns=["perfil","base"])
    sp = sp.rename(columns={"personas_demo":"escenario"}) if not sp.empty else pd.DataFrame(columns=["perfil","escenario"])
    out = bp.merge(sp, on="perfil", how="outer").fillna(0)
    out["delta"] = out["escenario"] - out["base"]
    return out.sort_values("delta", ascending=False)

# ------------------------------------------------
# IDENTIDAD VISUAL
# ------------------------------------------------
st.markdown("""
<style>
:root{
    --navy:#102F46;
    --blue:#1E5A78;
    --cyan:#3A86A8;
    --gold:#C99A3B;
    --green:#417A5A;
    --soft:#F4F7F9;
    --border:#D9E2E7;
    --ink:#18313F;
}
html, body, [class*="css"] {font-family: Inter, system-ui, sans-serif;}
.block-container {padding-top:1rem; padding-bottom:2rem; max-width:1500px;}
h1,h2,h3 {color:var(--navy); letter-spacing:-0.025em;}
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0E2A3F 0%,#163A55 100%);
    border-right:none;
}
[data-testid="stSidebar"] * {color:#F8FBFD;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.16);}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="base-input"] {
    background:#FFFFFF !important;
    border-radius:10px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * ,
[data-testid="stSidebar"] input {color:#1C2E38 !important;}
[data-testid="stSidebar"] span[data-baseweb="tag"] {
    background:#DCEEF5 !important;
    color:#153D56 !important;
}
[data-testid="stMetric"] {
    background:#FFFFFF;
    border:1px solid var(--border);
    border-radius:14px;
    padding:13px 14px;
    box-shadow:0 3px 12px rgba(19,49,65,.05);
}
[data-testid="stMetricLabel"] {font-weight:700;}
[data-testid="stMetricValue"] {color:var(--navy); font-size:1.55rem;}
.sipm-hero{
    background:linear-gradient(110deg,#E9F3F7 0%,#F9F5E9 100%);
    border:1px solid #D6E3E8;
    border-radius:18px;
    padding:22px 24px;
    margin:4px 0 16px 0;
}
.sipm-kicker{
    color:#356A83;
    font-size:.78rem;
    font-weight:800;
    letter-spacing:.12em;
    text-transform:uppercase;
}
.sipm-hero-title{
    color:#102F46;
    font-size:1.55rem;
    font-weight:800;
    margin:.25rem 0 .3rem 0;
}
.sipm-hero-copy{color:#34505F; font-size:1rem;}
.pillar{
    background:#FFFFFF;
    border:1px solid var(--border);
    border-radius:15px;
    padding:17px 18px;
    min-height:150px;
    box-shadow:0 3px 12px rgba(19,49,65,.04);
}
.pillar b{color:#143F58;font-size:1.05rem;}
.sipm-note{
    background:#FFF8E8;
    border-left:5px solid var(--gold);
    border-radius:9px;
    padding:13px 16px;
}
.reco{
    background:#F7FAFB;
    border:1px solid var(--border);
    border-radius:13px;
    padding:15px 17px;
    margin-bottom:10px;
}
.reco strong{color:#153F58;}
.market{
    background:#F9F6ED;
    border-left:5px solid var(--gold);
    border-radius:10px;
    padding:14px 16px;
    margin-bottom:10px;
}
[data-testid="stExpander"] {
    background:#FFFFFF;
    border:1px solid var(--border);
    border-radius:12px;
}
[data-testid="stExpander"] summary {
    font-weight:700;
    color:#173E56;
}
.stTabs [data-baseweb="tab-list"] {gap:5px; flex-wrap:wrap;}
.stTabs [data-baseweb="tab"] {
    background:#F4F7F9;
    border-radius:9px 9px 0 0;
    padding:8px 11px;
}
.stTabs [aria-selected="true"] {
    background:#E7F0F4 !important;
    color:#123E57 !important;
}

.metric-grid{
    display:grid;
    grid-template-columns:repeat(6,minmax(0,1fr));
    gap:12px;
    margin:14px 0 8px 0;
}
.metric-card{
    background:#FFFFFF;
    border:1px solid var(--border);
    border-radius:15px;
    padding:14px 15px;
    box-shadow:0 3px 12px rgba(19,49,65,.05);
    min-width:0;
}
.metric-label{
    color:#304D5C;
    font-size:.82rem;
    font-weight:700;
    line-height:1.2;
    min-height:2.05em;
    white-space:normal;
    overflow:visible;
    text-overflow:clip;
}
.metric-value{
    color:var(--navy);
    font-size:1.45rem;
    font-weight:750;
    line-height:1.15;
    margin-top:6px;
    white-space:normal;
    overflow:visible;
    text-overflow:clip;
    word-break:break-word;
}
[data-baseweb="tag"]{
    background-color:#DCEEF5 !important;
    color:#153D56 !important;
}
[data-baseweb="tag"] span{
    color:#153D56 !important;
}
[data-baseweb="tag"] svg{
    fill:#1E5A78 !important;
}
div[role="slider"]{
    background-color:#2A7F9E !important;
}
div[data-baseweb="slider"] div[role="progressbar"]{
    background-color:#2A7F9E !important;
}
.stButton > button,
.stDownloadButton > button,
.stLinkButton > a{
    border-color:#2A7F9E !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover{
    color:#1E5A78 !important;
    border-color:#1E5A78 !important;
}
.chart-explain{
    background:#F5F9FB;
    border:1px solid #DCE6EB;
    border-radius:11px;
    padding:11px 14px;
    color:#375565;
    font-size:.92rem;
    line-height:1.45;
    margin:4px 0 12px 0;
}
.intro-copy{
    color:#294858;
    font-size:1rem;
    line-height:1.58;
    margin-bottom:10px;
}
@media (max-width:1100px){
    .metric-grid{grid-template-columns:repeat(3,minmax(0,1fr));}
}
@media (max-width:650px){
    .metric-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
}


.drill{
    background:#F7FAFB;
    border:1px solid #DCE6EB;
    border-radius:12px;
    padding:13px 15px;
    margin:8px 0 12px 0;
}
.drill b{color:#173E56;}
</style>

""", unsafe_allow_html=True)

# ------------------------------------------------
# BENCHMARKS / POLÍTICAS
# ------------------------------------------------
BENCHMARKS = {
    "Salta": {
        "titulo":"Compras anticipadas + seguimiento de contratación local",
        "hecho":"Salta instrumentó convenios con empresas mineras para anticipar información de compras, difundir oportunidades entre proveedores locales y hacer seguimiento de la participación provincial.",
        "copiar":"Incorporar al SIPM un módulo de demanda futura a 12–36 meses y un tablero de cumplimiento por empresa, rubro y etapa del proyecto.",
        "url":"https://www.salta.gob.ar/prensa/noticias/tres-medidas-estrategicas-del-gobierno-de-salta-para-impulsar-y-transparentar-la-contratacion-de-proveedores-mineros-103550"
    },
    "Jujuy": {
        "titulo":"Registro provincial con trazabilidad de proveedores y empleo",
        "hecho":"Jujuy creó un Registro Provincial de Proveedores Locales de Productores Mineros y exige información de radicación, actividades y trabajadores por provincia.",
        "copiar":"Cruzar registro de proveedores con la matriz: capacidad real, certificaciones, rubros abastecidos, empleo local y demanda minera a la que pueden responder.",
        "url":"https://proveedores.registrominero.jujuy.gob.ar/"
    },
    "La Rioja": {
        "titulo":"Plan de compras a 3 años + compras locales y no locales",
        "hecho":"La Rioja incorporó en su régimen de proveedores declaraciones de compras locales, compras no locales y un Plan de Compra a 3 Años para empresas mineras.",
        "copiar":"Transformar el SIPM en una herramienta prospectiva: anticipar demanda antes de la licitación para que empresas locales puedan invertir, asociarse o certificarse.",
        "url":"https://proveedoresmineros.larioja.gob.ar/normativa/"
    }
}

def recommended_actions(row, target):
    current = float(row["participacion_catamarca_pct_demo"])
    complexity = str(row["complejidad_tecnica"]).lower()
    linkage = row["tipo_eslabonamiento"]
    acts = []
    if current < 20:
        acts += [
            ("1. Medir la demanda real", "Solicitar cantidades, especificaciones técnicas, frecuencia, proveedor actual y horizonte de compra de esta categoría."),
            ("2. Identificar oferta cercana", "Mapear empresas catamarqueñas que ya tengan capacidades parciales y cuantificar qué les falta para homologarse."),
        ]
    elif current < 50:
        acts += [
            ("1. Escalar proveedores existentes", "Trabajar sobre financiamiento, certificaciones, consorcios y capacidad para competir en contratos de mayor tamaño."),
            ("2. Auditar barreras de compra", "Comparar precio, plazo, experiencia, garantía y requisitos de licitación entre proveedores locales y externos."),
        ]
    else:
        acts += [
            ("1. Consolidar la capacidad local", "Evitar retrocesos de participación y elevar estándares de calidad, productividad y escala."),
            ("2. Exportar la capacidad", "Buscar contratos en Salta, Jujuy, La Rioja y otros distritos mineros para que el proveedor no dependa de un solo proyecto."),
        ]
    if linkage == "Aguas abajo" or "muy alta" in complexity:
        acts.append(("3. Evaluar inversión estratégica", "No impulsar producción local por decreto: realizar prefactibilidad técnica, escala mínima, energía, logística, tecnología y demanda regional."))
    else:
        acts.append(("3. Fijar una meta verificable", f"Construir un plan gradual desde {current:.0f}% hasta {target}% y monitorearlo por año, empresa y tipo de compra."))
    return acts

def relevant_benchmarks(row):
    current=float(row["participacion_catamarca_pct_demo"])
    linkage=row["tipo_eslabonamiento"]
    if linkage=="Aguas abajo":
        return ["La Rioja","Salta","Jujuy"]
    if current < 30:
        return ["Salta","La Rioja","Jujuy"]
    return ["Salta","Jujuy","La Rioja"]

def regional_opportunities(row):
    mineral=row["mineral"]
    sector=str(row["macrosector"])
    out=[]
    if mineral=="Litio":
        out.append(("Salta","Mercado regional natural para servicios vinculados con litio: ingeniería, mantenimiento, ambiente, logística, energía y tecnología."))
        out.append(("Jujuy","La cadena de litio permite pensar proveedores NOA especializados que trabajen en más de una provincia."))
    elif mineral=="Cobre":
        out.append(("Salta","El desarrollo cuprífero amplía la demanda regional potencial en metalmecánica, energía, ingeniería, logística, ambiente y mantenimiento."))
        out.append(("La Rioja","Los proyectos metalíferos y su política de proveedores pueden ser un segundo mercado para capacidades catamarqueñas consolidadas."))
    else:
        out.append(("La Rioja","Existe complementariedad potencial en servicios de exploración, laboratorio, ambiente, logística e ingeniería para minería metalífera."))
        out.append(("Salta","Los servicios especializados pueden escalar regionalmente y reducir dependencia de un único proyecto provincial."))
    if any(x in sector.lower() for x in ["ingeniería","logística","mantenimiento","tecnología","ambiente","metalmecánica","laboratorio"]):
        out.append(("NOA","Este tipo de capacidad es especialmente exportable entre provincias porque el know-how y los equipos pueden atender varios proyectos."))
    return out[:3]


# ------------------------------------------------
# POLÍTICA PÚBLICA Y CAPITAL HUMANO
# ------------------------------------------------
# Los coeficientes siguientes son supuestos DEMO para traducir empleo potencial
# agregado en familias de perfiles. No representan vacantes reales de empresas.
PROFILE_RULES = {
    "Exploración y geociencias": [
        ("Geología / Geociencias",0.45),("Ingeniería de Minas",0.20),
        ("Técnicos de campo y muestreo",0.25),("Datos / GIS",0.10)
    ],
    "Laboratorios": [
        ("Química / Procesos",0.35),("Técnicos de laboratorio",0.45),
        ("Ambiente / Hidrología",0.10),("Datos / Calidad",0.10)
    ],
    "Construcción": [
        ("Ingeniería Civil / Industrial",0.20),("Técnicos y oficios industriales",0.55),
        ("Higiene y Seguridad",0.15),("Administración / Logística",0.10)
    ],
    "Agua": [
        ("Ambiente / Hidrología",0.30),("Ingeniería Mecánica / Electromecánica",0.25),
        ("Técnicos y oficios industriales",0.35),("Automatización / Electrónica",0.10)
    ],
    "Energía": [
        ("Ingeniería Eléctrica / Electrónica",0.30),("Energías Renovables",0.15),
        ("Técnicos y oficios industriales",0.40),("Automatización / Datos",0.15)
    ],
    "Logística": [
        ("Logística / Administración",0.25),("Conductores y operadores especializados",0.55),
        ("Mantenimiento",0.10),("Seguridad / Calidad",0.10)
    ],
    "Mantenimiento": [
        ("Ingeniería Mecánica / Electromecánica",0.25),("Técnicos y oficios industriales",0.60),
        ("Automatización / Electrónica",0.10),("Seguridad / Calidad",0.05)
    ],
    "Industria química": [
        ("Química / Procesos",0.35),("Ingeniería Industrial",0.15),
        ("Técnicos de planta",0.35),("Seguridad / Ambiente",0.15)
    ],
    "Tecnología": [
        ("Software / Datos / IA",0.45),("Automatización / Electrónica",0.35),
        ("Ciberseguridad",0.10),("Gestión tecnológica",0.10)
    ],
    "Ambiente": [
        ("Ambiente / Hidrología",0.45),("Biología / Ciencias Naturales",0.20),
        ("Técnicos ambientales",0.25),("Datos / GIS",0.10)
    ],
    "Metalmecánica": [
        ("Ingeniería Mecánica / Industrial",0.20),("Técnicos y oficios industriales",0.65),
        ("Calidad / Ensayos",0.10),("Diseño / CAD",0.05)
    ],
    "Equipamiento": [
        ("Ingeniería Mecánica / Electromecánica",0.20),("Técnicos y oficios industriales",0.55),
        ("Logística / Repuestos",0.15),("Automatización / Electrónica",0.10)
    ],
    "Procesamiento": [
        ("Ingeniería de Minas / Procesos",0.25),("Química / Metalurgia",0.25),
        ("Técnicos de planta",0.40),("Automatización / Datos",0.10)
    ],
    "Procesamiento mineral": [
        ("Ingeniería de Minas / Procesos",0.25),("Química / Metalurgia",0.30),
        ("Técnicos de planta",0.35),("Automatización / Datos",0.10)
    ],
    "Metalurgia": [
        ("Química / Metalurgia",0.30),("Ingeniería Industrial / Mecánica",0.20),
        ("Técnicos de planta",0.40),("Calidad / Ensayos",0.10)
    ],
    "Materiales avanzados": [
        ("Química / Materiales",0.35),("Ingeniería / I+D",0.25),
        ("Técnicos de laboratorio y planta",0.25),("Datos / Automatización",0.15)
    ],
    "Manufactura avanzada": [
        ("Ingeniería Industrial / Mecánica",0.25),("Automatización / Electrónica",0.20),
        ("Técnicos y oficios industriales",0.45),("Calidad / Datos",0.10)
    ],
    "Economía circular": [
        ("Ambiente / Química",0.25),("Ingeniería Industrial / Procesos",0.20),
        ("Técnicos de planta",0.45),("Logística / Calidad",0.10)
    ]
}

DEFAULT_PROFILES = [
    ("Técnicos y oficios especializados",0.45),
    ("Ingenierías / Profesionales",0.25),
    ("Administración / Logística",0.15),
    ("Seguridad / Calidad / Ambiente",0.15)
]

def estimate_profiles(frame):
    records=[]
    for _,row in frame.iterrows():
        rules=PROFILE_RULES.get(row["macrosector"],DEFAULT_PROFILES)
        base=float(row["empleo_local_potencial_demo"])
        for profile,share in rules:
            records.append({
                "perfil":profile,
                "personas_demo":base*share,
                "mineral":row["mineral"],
                "territorio":row["territorio_potencial"],
                "macrosector":row["macrosector"]
            })
    p=pd.DataFrame(records)
    if p.empty:
        return p
    return p.groupby("perfil",as_index=False)["personas_demo"].sum().sort_values("personas_demo",ascending=False)

def education_action(profile):
    p=profile.lower()
    if any(x in p for x in ["técnic","oficios","operadores","conductores"]):
        return (
            "Corto plazo",
            "Trayectos de 3–12 meses, certificación de competencias, prácticas profesionalizantes y formación dual con empresas.",
            "Escuelas técnicas + formación profesional + empresas"
        )
    if any(x in p for x in ["software","datos","automatización","electrónica","ciberseguridad"]):
        return (
            "Corto / medio plazo",
            "Diplomaturas, microcredenciales y especializaciones aplicadas a minería; laboratorios de automatización, datos e instrumentación.",
            "UNCA + institutos superiores + sector tecnológico"
        )
    if any(x in p for x in ["geología","ingeniería","química","metalurgia","ambiente","hidrología","biología","materiales"]):
        return (
            "Medio / largo plazo",
            "Fortalecer ingreso, permanencia y egreso en carreras existentes; orientaciones mineras, becas, prácticas y proyectos de investigación aplicada.",
            "UNCA + Gobierno + empresas mineras"
        )
    return (
        "Corto / medio plazo",
        "Formación específica por competencias y actualización de contenidos según demanda relevada por el SIPM.",
        "Educación + Universidad + sector productivo"
    )

PUBLIC_POLICY_PILLARS = [
    ("1. Desarrollo de proveedores","Usar la matriz para priorizar categorías con demanda alta y baja captura local; diseñar homologación, financiamiento, asociatividad y asistencia técnica."),
    ("2. Capital humano","Traducir demanda productiva en perfiles profesionales, técnicos y oficios; alinear cupos, becas, currículas y prácticas con las brechas detectadas."),
    ("3. Atracción de inversiones","Promover inversiones sólo donde exista demanda verificable, escala regional y una brecha productiva clara."),
    ("4. Compras anticipadas","Solicitar planes agregados de demanda a 12–36 meses por categorías, sin exigir información comercial sensible."),
    ("5. Desarrollo territorial","Asignar políticas distintas según dónde puedan localizarse capacidades: Puna, Belén, Andalgalá, Tinogasta–Fiambalá o Capital."),
    ("6. Innovación y universidad","Convertir problemas mineros recurrentes en líneas de I+D, servicios tecnológicos, laboratorios y desafíos para estudiantes e investigadores.")
]


# ------------------------------------------------
# ESCENARIO GLOBAL + SIDEBAR
# ------------------------------------------------
# Los controles del escenario siguen viviendo exclusivamente en la pestaña Simulador,
# pero una vez aplicado un escenario pasa a alimentar TODO el SIPM hasta restaurar la base.
if "sipm_scenario_df" not in st.session_state:
    st.session_state["sipm_scenario_df"] = prepare_scenario_data(df.copy())
if "sipm_scenario_source" not in st.session_state:
    st.session_state["sipm_scenario_source"] = "Base SIPM"
if "sipm_scenario_active" not in st.session_state:
    st.session_state["sipm_scenario_active"] = False

scenario_active = bool(st.session_state.get("sipm_scenario_active", False))
scenario_global_df = prepare_scenario_data(st.session_state["sipm_scenario_df"])
active_df = scenario_global_df.copy() if scenario_active else prepare_scenario_data(df.copy())

# Las opciones del filtro consideran base + escenario para no perder categorías
# cuando se edita mineral, etapa o territorio dentro del constructor.
filter_catalog = pd.concat([prepare_scenario_data(df.copy()), active_df], ignore_index=True)
mineral_options = sorted(filter_catalog["mineral"].dropna().astype(str).unique())
linkage_options = [x for x in ["Aguas arriba", "Aguas abajo"] if x in set(filter_catalog["tipo_eslabonamiento"].astype(str))]
stage_options = sorted(filter_catalog["etapa_proyecto"].dropna().astype(str).unique())
territory_options = sorted(filter_catalog["territorio_potencial"].dropna().astype(str).unique())

# Cuando se activa/cambia un escenario, incluimos automáticamente todas las categorías
# para que una modificación territorial o estructural no desaparezca por un filtro viejo.
if st.session_state.pop("sipm_reset_filters", False):
    st.session_state["sidebar_minerals"] = mineral_options
    st.session_state["sidebar_linkages"] = linkage_options
    st.session_state["sidebar_stages"] = stage_options
    st.session_state["sidebar_territories"] = territory_options

with st.sidebar:
    st.markdown("## ⛏️ SIPM")
    st.markdown("**Inteligencia Productiva Minera**")
    st.caption("PROTOTIPO INSTITUCIONAL · CATAMARCA")
    if scenario_active:
        st.markdown("🟠 **ESCENARIO ACTIVO**")
        st.caption(st.session_state.get("sipm_scenario_source", "Escenario modificado"))
    else:
        st.caption("🔵 Base SIPM activa")
    st.divider()
    st.markdown("### Filtros")
    minerals = st.multiselect("Mineral", mineral_options, default=mineral_options, key="sidebar_minerals")
    linkages = st.multiselect("Eslabonamiento", linkage_options, default=linkage_options, key="sidebar_linkages")
    stages = st.multiselect("Etapa del proyecto", stage_options, default=stage_options, key="sidebar_stages")
    territories = st.multiselect("Territorio potencial", territory_options, default=territory_options, key="sidebar_territories")
    st.divider()
    st.markdown("**Lectura rápida**")
    st.caption("Los filtros actualizan todo el tablero. Si hay un escenario activo, todas las pestañas se recalculan con ese escenario.")

f = active_df[
    active_df["mineral"].astype(str).isin(minerals) &
    active_df["tipo_eslabonamiento"].astype(str).isin(linkages) &
    active_df["etapa_proyecto"].astype(str).isin(stages) &
    active_df["territorio_potencial"].astype(str).isin(territories)
].copy()

# La misma selección aplicada a la base original permite medir los deltas del escenario.
base_f = df[
    df["mineral"].astype(str).isin(minerals) &
    df["tipo_eslabonamiento"].astype(str).isin(linkages) &
    df["etapa_proyecto"].astype(str).isin(stages) &
    df["territorio_potencial"].astype(str).isin(territories)
].copy()

if f.empty:
    st.info("No hay registros con esta combinación de filtros.")
    st.stop()

total=f["demanda_anual_usd_demo"].sum()
local=f["captura_local_usd_demo"].sum()
outside=f["gasto_fuera_catamarca_usd_demo"].sum()
jobs=int(f["empleo_local_potencial_demo"].sum())
local_pct=local/total if total else 0

# ------------------------------------------------
# HEADER
# ------------------------------------------------
st.markdown("""
<div class="sipm-hero">
  <div class="sipm-kicker">Sistema Provincial de Inteligencia Productiva para la Minería</div>
  <div class="sipm-hero-title">¿Cómo transformar la minería en más empresas, empleo, conocimiento y valor agregado dentro de Catamarca?</div>
  <div class="sipm-hero-copy">El SIPM conecta demanda minera, capacidades productivas, territorio, proveedores y oportunidades de industrialización en una sola herramienta de decisión.</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="metric-grid">
  <div class="metric-card"><div class="metric-label">Actividades mapeadas</div><div class="metric-value">{len(f)}</div></div>
  <div class="metric-card"><div class="metric-label">Mercado / demanda mapeada</div><div class="metric-value">US$ {total/1e6:,.0f} M</div></div>
  <div class="metric-card"><div class="metric-label">Captura local estimada</div><div class="metric-value">{local_pct:.0%}</div></div>
  <div class="metric-card"><div class="metric-label">Gasto fuera de Catamarca</div><div class="metric-value">US$ {outside/1e6:,.0f} M</div></div>
  <div class="metric-card"><div class="metric-label">Empleo potencial asociado</div><div class="metric-value">{jobs:,}</div></div>
  <div class="metric-card"><div class="metric-label">Sectores económicos alcanzados</div><div class="metric-value">{f["macrosector"].nunique()}</div></div>
</div>
""", unsafe_allow_html=True)

st.caption("⚠️ Todos los indicadores cuantitativos son demostrativos. El sistema final deberá alimentarse con información validada.")

if scenario_active:
    ctx_global = scenario_change_context(base_f, f)
    st.markdown(
        f'<div class="sipm-note"><b>🟠 ESCENARIO ACTIVO EN TODO EL SIPM.</b> '
        f'Las pestañas siguientes se recalculan con <b>{st.session_state.get("sipm_scenario_source", "escenario modificado")}</b>. '
        f'Respecto de la base visible: Δ demanda <b>US$ {ctx_global["delta_demanda"]/1e6:+,.1f} M</b> · '
        f'Δ captura local <b>{ctx_global["delta_captura_pp"]:+.1f} p.p.</b> · '
        f'Δ empleo potencial <b>{ctx_global["delta_empleo"]:+,.0f}</b>. '
        f'Podés volver a la base desde Simulador.</div>',
        unsafe_allow_html=True
    )

tabs=st.tabs([
    "🏠 Inicio","🌐 Ecosistema","⬅️ Aguas arriba","➡️ Aguas abajo",
    "🎯 Oportunidades","📍 Territorio","🧪 Simulador","🎓 Políticas y talento","📋 Matriz"
])

# ------------------------------------------------
# INICIO
# ------------------------------------------------
with tabs[0]:
    st.subheader("Una lectura simple del impacto minero")
    st.markdown("""
<div class="intro-copy">
El SIPM propone transformar información dispersa sobre compras, proveedores, capacidades productivas y cadenas de valor en una herramienta permanente de inteligencia económica. Su objetivo es mostrar <b>qué actividades moviliza la minería, cuánto valor puede quedar en Catamarca y dónde existen brechas concretas para desarrollar empresas, empleo, formación e inversión.</b>
</div>
<div class="intro-copy">
La necesidad surge porque producir más minerales no garantiza, por sí solo, mayor desarrollo provincial. Para convertir la expansión minera en una política de desarrollo productivo, Catamarca necesita identificar sus <b>eslabonamientos aguas arriba y aguas abajo</b>, medir el contenido local, anticipar demanda y priorizar las oportunidades con mayor impacto económico y territorial.
</div>
""", unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a:
        st.markdown('<div class="pillar"><b>⬅️ 1. Lo que la minería necesita</b><br><br>Bienes, servicios, tecnología, energía, construcción, logística, mantenimiento, ambiente, conocimiento y trabajadores.</div>',unsafe_allow_html=True)
    with b:
        st.markdown('<div class="pillar"><b>⛏️ 2. La actividad minera</b><br><br>El proyecto minero funciona como nodo central que moviliza demanda sobre decenas de sectores económicos.</div>',unsafe_allow_html=True)
    with c:
        st.markdown('<div class="pillar"><b>➡️ 3. Lo que puede generar después</b><br><br>Procesamiento, metalurgia, materiales avanzados, manufacturas, energía, reciclaje y nuevas industrias.</div>',unsafe_allow_html=True)

    st.markdown("### ¿Dónde aparece hoy el mayor espacio de política productiva?")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> ordena los sectores según el gasto que, en este escenario demostrativo, no estaría siendo capturado por empresas de Catamarca. Cuanto mayor es la barra, mayor es la oportunidad de estudiar desarrollo de proveedores, atracción de inversiones o sustitución competitiva.</div>', unsafe_allow_html=True)
    top=f.groupby("macrosector",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum"),
        empleo=("empleo_local_potencial_demo","sum")
    ).sort_values("gasto_fuera",ascending=False).head(10)

    fig=px.bar(
        top.sort_values("gasto_fuera"),
        x="gasto_fuera",y="macrosector",orientation="h",
        text_auto=".2s",
        labels={"gasto_fuera":"Gasto fuera de Catamarca · USD demo","macrosector":""}
    )
    fig.update_traces(marker_color="#2A6F8E")
    fig.update_layout(height=470,showlegend=False,margin=dict(t=15,l=0,r=10,b=10))
    st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------
# ECOSISTEMA
# ------------------------------------------------
with tabs[1]:
    st.subheader("¿Qué sectores económicos moviliza la minería?")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> una visión completa del ecosistema económico asociado a la minería. El tamaño de cada bloque representa la magnitud de la demanda y el tono indica la participación local estimada. Permite detectar rápidamente qué sectores son grandes y cuáles todavía tienen baja presencia catamarqueña.</div>', unsafe_allow_html=True)
    eco=f.groupby("macrosector",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        captura=("participacion_catamarca_pct_demo","mean"),
        empleo=("empleo_local_potencial_demo","sum")
    )
    fig=px.treemap(
        eco,path=["macrosector"],values="demanda",color="captura",
        color_continuous_scale=["#E8F0F3","#8DB8C9","#1E5A78"],
        hover_data={"empleo":True,"captura":":.1f","demanda":":,.0f"}
    )
    fig.update_layout(height=620,margin=dict(t=10,l=10,r=10,b=10),coloraxis_colorbar_title="% local demo")
    st.plotly_chart(fig,use_container_width=True)
    st.markdown('<div class="sipm-note"><b>Cómo leerlo:</b> cuanto mayor es el bloque, mayor es la demanda asociada. El tono indica cuánto de esa actividad se captura localmente en la simulación.</div>',unsafe_allow_html=True)

# ------------------------------------------------
# AGUAS ARRIBA
# ------------------------------------------------
with tabs[2]:
    st.subheader("Eslabonamientos aguas arriba")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> cómo la actividad minera genera demanda sobre construcción, energía, logística, metalmecánica, tecnología, ambiente, servicios y otros sectores. El ancho de cada flujo representa el peso económico de esa relación. Esta vista permite entender que el impacto minero comienza mucho antes de extraer el mineral.</div>', unsafe_allow_html=True)

    back=f[f["tipo_eslabonamiento"]=="Aguas arriba"].copy()
    if back.empty:
        st.info("Activá Aguas arriba en el filtro lateral.")
    else:
        agg=back.groupby("macrosector",as_index=False).agg(
            demanda=("demanda_anual_usd_demo","sum"),
            local=("participacion_catamarca_pct_demo","mean"),
            gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum"),
            actividades=("actividad","nunique")
        ).sort_values("demanda",ascending=False)

        labels=["MINERÍA"]+agg["macrosector"].tolist()
        fig=go.Figure(go.Sankey(
            node=dict(
                label=labels,pad=18,thickness=22,
                color=["#C99A3B"]+["#315E74"]*len(agg)
            ),
            link=dict(
                source=[0]*len(agg),
                target=list(range(1,len(agg)+1)),
                value=agg["demanda"],
                color="rgba(49,94,116,.30)",
                customdata=agg[["local","gasto_fuera","actividades"]].values,
                hovertemplate="%{target.label}<br>Demanda demo: US$ %{value:,.0f}<br>Captura local: %{customdata[0]:.1f}%<br>Gasto fuera: US$ %{customdata[1]:,.0f}<br>Actividades: %{customdata[2]}<extra></extra>"
            )
        ))
        fig.update_layout(height=640,margin=dict(t=10,l=10,r=10,b=10),font=dict(size=12))
        st.plotly_chart(fig,use_container_width=True)

        if scenario_active:
            st.markdown("### Impacto del escenario · Aguas arriba")
            base_back = base_f[base_f["tipo_eslabonamiento"]=="Aguas arriba"].copy()
            comp_back = group_scenario_delta(base_back, back, "macrosector")
            if not comp_back.empty:
                cb1, cb2, cb3 = st.columns(3)
                cb1.metric("Δ demanda aguas arriba", f"US$ {comp_back['delta_demanda'].sum()/1e6:+,.1f} M")
                cb2.metric("Δ gasto fuera", f"US$ {comp_back['delta_gasto_fuera'].sum()/1e6:+,.1f} M")
                cb3.metric("Δ empleo potencial", f"{comp_back['delta_empleo'].sum():+,.0f}")
                plot_back = comp_back[comp_back["delta_demanda"].abs() > 0].sort_values("delta_demanda")
                if not plot_back.empty:
                    fig_delta_back = px.bar(
                        plot_back, x="delta_demanda", y="macrosector", orientation="h",
                        labels={"delta_demanda":"Cambio de demanda vs base · USD","macrosector":""},
                        text_auto=".2s"
                    )
                    fig_delta_back.update_traces(marker_color="#C99A3B")
                    fig_delta_back.update_layout(height=max(320,55*len(plot_back)),showlegend=False,margin=dict(t=5,l=0,r=10,b=10))
                    st.plotly_chart(fig_delta_back,use_container_width=True)
                    st.caption("Las barras muestran qué sectores aguas arriba ganan o pierden peso económico respecto de la base. Esta lectura alimenta desarrollo de proveedores, compras anticipadas e infraestructura habilitante.")

        st.markdown("### Profundizar sin llegar a datos sensibles")
        st.markdown(
            '<div class="drill"><b>Nivel 1:</b> sector económico. '
            'El SIPM muestra cuánto moviliza la minería sobre ese sector y cuánto se captura localmente.<br>'
            '<b>Nivel 2:</b> familia de actividades. Se profundiza en tipos de capacidades requeridas, '
            'pero sin identificar contratos, proveedores individuales, precios ni datos comerciales reservados.</div>',
            unsafe_allow_html=True
        )

        sector_sel = st.selectbox(
            "Elegí un sector para profundizar",
            agg["macrosector"].tolist(),
            key="back_sector"
        )
        sec = back[back["macrosector"]==sector_sel].copy()
        activity_agg = sec.groupby("actividad",as_index=False).agg(
            demanda=("demanda_anual_usd_demo","sum"),
            captura=("participacion_catamarca_pct_demo","mean"),
            empleo=("empleo_local_potencial_demo","sum"),
            requerimientos=("requerimiento_o_producto","nunique")
        ).sort_values("demanda",ascending=False)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Demanda sectorial demo",f"US$ {sec['demanda_anual_usd_demo'].sum()/1e6:,.1f} M")
        c2.metric("Captura local media",f"{sec['participacion_catamarca_pct_demo'].mean():.0f}%")
        c3.metric("Actividades",sec["actividad"].nunique())
        c4.metric("Empleo potencial",int(sec["empleo_local_potencial_demo"].sum()))

        fig2=px.bar(
            activity_agg.sort_values("demanda"),
            x="demanda",y="actividad",orientation="h",
            color="captura",
            color_continuous_scale=["#DDE9EE","#2C6B89"],
            hover_data=["empleo","requerimientos"],
            labels={"demanda":"Demanda demo USD","actividad":"","captura":"% local"}
        )
        fig2.update_layout(height=max(330,70*len(activity_agg)),margin=dict(t=10,l=0,r=10,b=10))
        st.plotly_chart(fig2,use_container_width=True)

        activity_sel = st.selectbox(
            "Segundo nivel: elegí una familia de actividad",
            activity_agg["actividad"].tolist(),
            key="back_activity"
        )
        det = sec[sec["actividad"]==activity_sel].copy()

        st.markdown("#### Qué debería conocer el SIPM en este nivel")
        st.markdown(
            "- Tipo general de bien o servicio requerido.\n"
            "- Nivel de complejidad y criticidad.\n"
            "- Frecuencia aproximada de demanda.\n"
            "- Capacidad local existente o potencial.\n"
            "- Barreras de entrada: certificación, escala, capital, tecnología o experiencia.\n"
            "- Territorio donde tendría mayor sentido desarrollar esa capacidad."
        )

        with st.expander("Ver requerimientos demostrativos agrupados",expanded=False):
            for _,r in det.iterrows():
                st.markdown(
                    f"**{r['requerimiento_o_producto']}**  \n"
                    f"Complejidad: {r['complejidad_tecnica']} · Capacidad local: {r['capacidad_local_demo']} · "
                    f"Territorio: {r['territorio_potencial']}  \n"
                    f"Acción sugerida: {r['accion_sugerida']}"
                )
                st.divider()

        st.caption("El diseño deliberadamente evita bajar a empresa, proveedor, contrato, precio unitario o volumen confidencial. La unidad mínima es una categoría económica suficientemente agregada para orientar política pública.")

# ------------------------------------------------
# AGUAS ABAJO
# ------------------------------------------------
with tabs[3]:
    st.subheader("Eslabonamientos aguas abajo")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> las actividades que pueden desarrollarse después de la extracción: procesamiento, refinación, manufactura, materiales avanzados, energía o reciclaje. No implica que todas sean viables, sino que permite identificar cuáles merecen estudios de factibilidad y políticas de largo plazo.</div>', unsafe_allow_html=True)

    fw=f[f["tipo_eslabonamiento"]=="Aguas abajo"].copy()
    if fw.empty:
        st.info("Activá Aguas abajo en el filtro lateral.")
    else:
        mineral=st.selectbox("Nivel 1: elegí una cadena mineral",sorted(fw["mineral"].unique()),key="forward")
        chain=fw[fw["mineral"]==mineral].sort_values("id").copy()

        st.markdown(
            '<div class="drill"><b>Nivel 1:</b> cadena mineral completa. '
            'Permite visualizar qué familias de transformación existen después de la extracción.<br>'
            '<b>Nivel 2:</b> eslabón estratégico. Se analiza complejidad, capacidad local, barreras e impacto potencial, '
            'sin pretender construir un estudio industrial de detalle en esta etapa.</div>',
            unsafe_allow_html=True
        )

        # Visual chain
        labels=[mineral.upper()] + chain["actividad"].tolist()
        source=list(range(len(labels)-1))
        target=list(range(1,len(labels)))
        vals=[max(1,float(x)) for x in chain["demanda_anual_usd_demo"]]
        fig=go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels,
                pad=20,
                thickness=22,
                color=["#C99A3B"]+["#315E74"]*(len(labels)-1)
            ),
            link=dict(
                source=source,
                target=target,
                value=vals,
                color="rgba(49,94,116,.28)"
            )
        ))
        fig.update_layout(height=430,margin=dict(t=10,l=10,r=10,b=10),font=dict(size=12))
        st.plotly_chart(fig,use_container_width=True)

        if scenario_active:
            st.markdown(f"### Impacto del escenario · Aguas abajo · {mineral}")
            base_fw_m = base_f[(base_f["tipo_eslabonamiento"]=="Aguas abajo") & (base_f["mineral"]==mineral)].copy()
            comp_fw = group_scenario_delta(base_fw_m, chain, "actividad")
            if not comp_fw.empty:
                cf1,cf2,cf3 = st.columns(3)
                cf1.metric("Δ mercado / demanda", f"US$ {comp_fw['delta_demanda'].sum()/1e6:+,.1f} M")
                cf2.metric("Δ captura local", f"US$ {comp_fw['delta_captura'].sum()/1e6:+,.1f} M")
                cf3.metric("Δ empleo potencial", f"{comp_fw['delta_empleo'].sum():+,.0f}")
                plot_fw = comp_fw[comp_fw["delta_demanda"].abs() > 0].sort_values("delta_demanda")
                if not plot_fw.empty:
                    fig_delta_fw = px.bar(
                        plot_fw, x="delta_demanda", y="actividad", orientation="h",
                        labels={"delta_demanda":"Cambio de demanda vs base · USD","actividad":""},
                        text_auto=".2s"
                    )
                    fig_delta_fw.update_traces(marker_color="#C99A3B")
                    fig_delta_fw.update_layout(height=max(300,60*len(plot_fw)),showlegend=False,margin=dict(t=5,l=0,r=10,b=10))
                    st.plotly_chart(fig_delta_fw,use_container_width=True)
                    st.caption("Un aumento aguas abajo no se interpreta automáticamente como una industria viable: señala dónde conviene activar prefactibilidad, atracción de inversiones, I+D y evaluación de escala regional.")

        st.markdown("### Profundizar en un eslabón")
        link_sel = st.selectbox(
            "Nivel 2: elegí un eslabón estratégico",
            chain.index,
            format_func=lambda i:f"{chain.loc[i,'actividad']} → {chain.loc[i,'requerimiento_o_producto']}",
            key="forward_link"
        )
        r=chain.loc[link_sel]

        c1,c2,c3,c4=st.columns(4)
        c1.metric("Mercado / demanda demo",f"US$ {r['demanda_anual_usd_demo']/1e6:,.1f} M")
        c2.metric("Captura local demo",f"{r['participacion_catamarca_pct_demo']:.0f}%")
        c3.metric("Complejidad",r["complejidad_tecnica"])
        c4.metric("Empleo potencial",int(r["empleo_local_potencial_demo"]))

        st.markdown(
            f"**Qué representa este eslabón:** {r['cadena_valor']}  \n"
            f"**Capacidad local actual:** {r['capacidad_local_demo']}  \n"
            f"**Barrera principal:** {r['barrera_principal']}  \n"
            f"**Acción sugerida:** {r['accion_sugerida']}  \n"
            f"**Beneficio provincial:** {r['beneficio_provincial']}  \n"
            f"**Territorio potencial:** {r['territorio_potencial']}"
        )

        st.markdown("#### Qué debería analizarse antes de promover este eslabón")
        st.markdown(
            "- Existencia de demanda suficiente y estable.\n"
            "- Escala mínima eficiente.\n"
            "- Disponibilidad de energía, logística e infraestructura.\n"
            "- Tecnología y conocimiento requeridos.\n"
            "- Capacidad de vender también a otras provincias o mercados.\n"
            "- Conveniencia de desarrollar localmente, atraer inversión o integrarse regionalmente."
        )

        st.caption("El SIPM identifica y prioriza eslabones; no reemplaza los estudios de prefactibilidad industrial que sólo deberían realizarse sobre las oportunidades seleccionadas.")

# ------------------------------------------------
# OPORTUNIDADES
# ------------------------------------------------
with tabs[4]:
    st.subheader("¿Dónde conviene mirar primero?")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> cruza participación local, gasto externo y empleo potencial. Las oportunidades más relevantes son aquellas donde existe una demanda importante, baja participación catamarqueña y capacidad de generar actividad económica. El gráfico sirve para priorizar dónde investigar primero.</div>', unsafe_allow_html=True)
    op=f.copy()
    fig=px.scatter(
        op,x="participacion_catamarca_pct_demo",y="gasto_fuera_catamarca_usd_demo",
        size="empleo_local_potencial_demo",color="mineral",symbol="tipo_eslabonamiento",
        hover_name="requerimiento_o_producto",
        hover_data=["macrosector","actividad","territorio_potencial","puntaje_oportunidad_demo"],
        labels={
            "participacion_catamarca_pct_demo":"Participación de Catamarca (%) · demo",
            "gasto_fuera_catamarca_usd_demo":"Gasto fuera de Catamarca · USD demo"
        }
    )
    fig.update_layout(height=590)
    st.plotly_chart(fig,use_container_width=True)
    st.markdown('<div class="sipm-note"><b>Zona crítica:</b> las actividades ubicadas arriba y a la izquierda combinan alto gasto externo con baja captura local. Son candidatas a estudios de factibilidad y desarrollo de proveedores.</div>',unsafe_allow_html=True)

    if scenario_active:
        st.markdown("### Cómo cambió el mapa de oportunidades")
        base_high = int((base_f["prioridad_demo"]=="Alta").sum())
        sc_high = int((op["prioridad_demo"]=="Alta").sum())
        co1,co2,co3 = st.columns(3)
        co1.metric("Oportunidades de prioridad alta", sc_high, delta=sc_high-base_high)
        co2.metric("Δ gasto fuera", f"US$ {(op['gasto_fuera_catamarca_usd_demo'].sum()-base_f['gasto_fuera_catamarca_usd_demo'].sum())/1e6:+,.1f} M")
        co3.metric("Δ captura local", f"US$ {(op['captura_local_usd_demo'].sum()-base_f['captura_local_usd_demo'].sum())/1e6:+,.1f} M")
        sector_op = group_scenario_delta(base_f, op, "macrosector")
        sector_op["presion_oportunidad"] = sector_op["gasto_fuera_escenario"] - sector_op["gasto_fuera_base"]
        sector_op = sector_op[sector_op["presion_oportunidad"].abs()>0].sort_values("presion_oportunidad")
        if not sector_op.empty:
            fig_op_delta = px.bar(sector_op, x="presion_oportunidad", y="macrosector", orientation="h",
                                  labels={"presion_oportunidad":"Cambio del gasto fuera vs base · USD","macrosector":""}, text_auto=".2s")
            fig_op_delta.update_traces(marker_color="#C99A3B")
            fig_op_delta.update_layout(height=max(300,50*len(sector_op)),showlegend=False,margin=dict(t=5,l=0,r=10,b=10))
            st.plotly_chart(fig_op_delta,use_container_width=True)
            st.caption("Un aumento del gasto externo en un sector eleva la presión de política productiva; una caída puede reflejar mayor captura local o menor demanda. La causa debe leerse junto con los demás indicadores.")

    top=op.sort_values(["puntaje_oportunidad_demo","gasto_fuera_catamarca_usd_demo"],ascending=False).head(12)
    choice=st.selectbox(
        "Abrir ficha completa de una oportunidad",
        top.index,
        format_func=lambda i:f"{top.loc[i,'mineral']} · {top.loc[i,'macrosector']} · {top.loc[i,'requerimiento_o_producto']}"
    )
    rr=top.loc[choice]
    with st.expander("Ver ficha de oportunidad",expanded=True):
        c1,c2,c3=st.columns(3)
        c1.metric("Prioridad demo",rr["prioridad_demo"])
        c2.metric("Captura local",f"{rr['participacion_catamarca_pct_demo']:.0f}%")
        c3.metric("Gasto fuera",f"US$ {rr['gasto_fuera_catamarca_usd_demo']/1e6:,.2f} M")
        st.markdown(
            f"**Actividad:** {rr['actividad']}  \n"
            f"**Acción sugerida:** {rr['accion_sugerida']}  \n"
            f"**Barrera principal:** {rr['barrera_principal']}  \n"
            f"**Certificaciones / condiciones:** {rr['certificaciones_referenciales']}  \n"
            f"**Territorio:** {rr['territorio_potencial']}  \n"
            f"**Beneficio provincial:** {rr['beneficio_provincial']}"
        )

# ------------------------------------------------
# TERRITORIO
# ------------------------------------------------
with tabs[5]:
    st.subheader("Lectura territorial")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> cómo se distribuyen las oportunidades económicas según territorio potencial. Permite pasar de una política minera provincial genérica a estrategias diferenciadas para Belén, Andalgalá, Tinogasta–Fiambalá, Antofagasta de la Sierra y Capital.</div>', unsafe_allow_html=True)
    terr=f.groupby("territorio_potencial",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        captura=("captura_local_usd_demo","sum"),
        empleo=("empleo_local_potencial_demo","sum"),
        actividades=("id","count")
    )
    terr["captura_pct"]=terr["captura"]/terr["demanda"]*100
    fig=px.bar(
        terr.sort_values("demanda"),
        x="demanda",y="territorio_potencial",orientation="h",color="captura_pct",
        color_continuous_scale=["#DDE9EE","#2C6B89"],
        hover_data=["empleo","actividades"],
        labels={"demanda":"Demanda demo USD","territorio_potencial":"","captura_pct":"% local"}
    )
    fig.update_layout(height=520)
    st.plotly_chart(fig,use_container_width=True)

    if scenario_active:
        st.markdown("### Territorios más afectados por el escenario")
        terr_delta = group_scenario_delta(base_f, f, "territorio_potencial")
        terr_delta["impacto_abs"] = terr_delta["delta_demanda"].abs()/1e6 + terr_delta["delta_empleo"].abs()
        terr_delta = terr_delta.sort_values("impacto_abs", ascending=False)
        if not terr_delta.empty:
            td = terr_delta.iloc[0]
            tt1,tt2,tt3 = st.columns(3)
            tt1.metric("Mayor cambio territorial", str(td["territorio_potencial"]))
            tt2.metric("Δ demanda", f"US$ {td['delta_demanda']/1e6:+,.1f} M")
            tt3.metric("Δ empleo potencial", f"{td['delta_empleo']:+,.0f}")
            terr_long = terr_delta.melt(
                id_vars=["territorio_potencial"],
                value_vars=["delta_demanda","delta_captura"],
                var_name="variable", value_name="valor"
            )
            terr_long["variable"] = terr_long["variable"].map({"delta_demanda":"Δ Demanda","delta_captura":"Δ Captura local"})
            fig_td = px.bar(terr_long, x="valor", y="territorio_potencial", color="variable", orientation="h",
                            barmode="group", labels={"valor":"Cambio vs base · USD","territorio_potencial":"","variable":""})
            fig_td.update_layout(height=max(340,55*terr_delta["territorio_potencial"].nunique()),margin=dict(t=5,l=0,r=10,b=10))
            st.plotly_chart(fig_td,use_container_width=True)
            st.caption("Esta comparación sirve para anticipar dónde deberían concentrarse infraestructura, formación, servicios productivos y coordinación con municipios.")

    place=st.selectbox("Explorar territorio",sorted(f["territorio_potencial"].unique()))
    tp=f[f["territorio_potencial"]==place].sort_values("demanda_anual_usd_demo",ascending=False)
    st.markdown(f"### {place}")
    st.caption(f"{len(tp)} actividades asociadas en el filtro actual.")
    for _,r in tp.head(10).iterrows():
        with st.expander(f"{r['macrosector']} · {r['requerimiento_o_producto']}"):
            st.markdown(
                f"**Mineral:** {r['mineral']}  \n"
                f"**Actividad:** {r['actividad']}  \n"
                f"**Beneficio:** {r['beneficio_provincial']}  \n"
                f"**Acción sugerida:** {r['accion_sugerida']}"
            )

# ------------------------------------------------
# SIMULADOR
# ------------------------------------------------
with tabs[6]:
    st.subheader("Simulador de política productiva")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> permite ensayar escenarios de mayor participación local en una actividad y dimensionar cuánto gasto adicional podría permanecer en la provincia. Su función no es predecir resultados, sino ayudar a decidir si una oportunidad merece políticas específicas, inversión o estudios técnicos.</div>', unsafe_allow_html=True)

    sim=f.sort_values("gasto_fuera_catamarca_usd_demo",ascending=False)
    idx=st.selectbox(
        "Actividad a simular",
        sim.index,
        format_func=lambda i:f"{sim.loc[i,'mineral']} · {sim.loc[i,'macrosector']} · {sim.loc[i,'requerimiento_o_producto']}"
    )
    r=sim.loc[idx]
    current=float(r["participacion_catamarca_pct_demo"])
    target=st.slider(
        "Participación local objetivo · escenario",
        min_value=int(current),max_value=100,value=min(100,int(current)+20),step=1
    )
    incremental=r["demanda_anual_usd_demo"]*(target-current)/100
    extra_jobs=r["empleo_local_potencial_demo"]*((target-current)/100)

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Situación actual",f"{current:.0f}%")
    c2.metric("Objetivo",f"{target}%")
    c3.metric("Gasto adicional retenido",f"US$ {incremental/1e6:,.2f} M")
    c4.metric("Empleo asociado",f"+{extra_jobs:,.0f}")

    st.markdown("### Recomendación para Catamarca")
    for title,desc in recommended_actions(r,target):
        st.markdown(f'<div class="reco"><strong>{title}</strong><br>{desc}</div>',unsafe_allow_html=True)

    st.markdown("### Qué hicieron otras provincias y qué podemos copiar")
    for province in relevant_benchmarks(r):
        b=BENCHMARKS[province]
        with st.expander(f"{province} · {b['titulo']}"):
            st.markdown(b["hecho"])
            st.markdown(f"**Aplicación posible en Catamarca:** {b['copiar']}")
            st.link_button(f"Ver antecedente oficial de {province}",b["url"])

    st.markdown("### Oportunidades fuera de Catamarca")
    for province,text in regional_opportunities(r):
        st.markdown(f'<div class="market"><strong>{province}</strong><br>{text}</div>',unsafe_allow_html=True)

    st.markdown(
        '<div class="sipm-note"><b>Importante:</b> el escenario no predice causalidad ni garantiza empleo. '
        'Sirve para dimensionar una oportunidad y decidir si amerita estudios técnicos, comerciales o de inversión.</div>',
        unsafe_allow_html=True
    )

    st.divider()
    st.markdown("## Constructor avanzado de escenarios")
    st.markdown(
        '<div class="chart-explain"><b>Qué permite:</b> construir escenarios completos sin modificar la base SIPM. '
        'Podés partir de la matriz actual, cargar un CSV/Excel previamente editado, aplicar cambios masivos combinables '
        'o editar registros individuales. Al aplicarlo, <b>el escenario pasa a alimentar todo el SIPM</b>: indicadores, Aguas arriba, Aguas abajo, '
        'oportunidades, territorio, matriz y Políticas y talento.</div>',
        unsafe_allow_html=True
    )

    st.markdown("### 1. Elegir la base del escenario")
    src1, src2 = st.columns([1.4, 1])
    with src1:
        uploaded_scenario = st.file_uploader(
            "Cargar matriz modificada · CSV o Excel (.xlsx)",
            type=["csv", "xlsx"],
            key="scenario_file_uploader",
            help="El archivo debe conservar las columnas de la matriz SIPM. Las columnas calculadas se regeneran automáticamente."
        )
        if uploaded_scenario is not None:
            try:
                if uploaded_scenario.name.lower().endswith(".csv"):
                    uploaded_df = pd.read_csv(uploaded_scenario)
                else:
                    uploaded_df = pd.read_excel(uploaded_scenario)
                ok, missing = validate_scenario_file(uploaded_df)
                if not ok:
                    st.error("El archivo no tiene todas las columnas necesarias: " + ", ".join(missing))
                else:
                    st.success(f"Archivo válido: {len(uploaded_df)} registros detectados.")
                    if st.button("Usar archivo cargado como escenario", type="primary", key="use_uploaded_scenario"):
                        st.session_state["sipm_scenario_df"] = prepare_scenario_data(uploaded_df)
                        st.session_state["sipm_scenario_source"] = f"Archivo: {uploaded_scenario.name}"
                        st.session_state["sipm_scenario_active"] = True
                        st.session_state["sipm_reset_filters"] = True
                        st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")

    with src2:
        st.markdown(f"**Fuente actual del escenario:**  \n{st.session_state['sipm_scenario_source']}")
        st.caption("Los cambios quedan en la sesión de la app hasta que se restaure la base o se reinicie la aplicación.")
        if st.button("↺ Restaurar escenario base", key="restore_scenario"):
            st.session_state["sipm_scenario_df"] = prepare_scenario_data(df.copy())
            st.session_state["sipm_scenario_source"] = "Base SIPM"
            st.session_state["sipm_scenario_active"] = False
            st.session_state["sipm_reset_filters"] = True
            st.rerun()

    scenario_df = prepare_scenario_data(st.session_state["sipm_scenario_df"])

    st.markdown("### 2. Definir a qué registros aplicar cambios")
    st.caption("El alcance toma como punto de partida los filtros laterales actuales, pero puede reducirse aún más dentro del escenario.")

    visible_for_scope = filter_like_sidebar(scenario_df)
    if visible_for_scope.empty:
        st.warning("El escenario actual no tiene registros compatibles con los filtros laterales seleccionados.")
    else:
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            scope_mode = st.selectbox(
                "Alcance",
                [
                    "Toda la selección actual",
                    "Un mineral",
                    "Un macrosector",
                    "Una actividad",
                    "Un territorio",
                    "Un eslabonamiento",
                    "Registros individuales",
                ],
                key="scenario_scope_mode"
            )
        scope_indices = visible_for_scope.index

        if scope_mode == "Un mineral":
            with sc2:
                val = st.selectbox("Mineral", sorted(visible_for_scope["mineral"].dropna().unique()), key="scenario_scope_mineral")
            scope_indices = visible_for_scope[visible_for_scope["mineral"] == val].index
        elif scope_mode == "Un macrosector":
            with sc2:
                val = st.selectbox("Macrosector", sorted(visible_for_scope["macrosector"].dropna().unique()), key="scenario_scope_sector")
            scope_indices = visible_for_scope[visible_for_scope["macrosector"] == val].index
        elif scope_mode == "Una actividad":
            with sc2:
                val = st.selectbox("Actividad", sorted(visible_for_scope["actividad"].dropna().unique()), key="scenario_scope_activity")
            scope_indices = visible_for_scope[visible_for_scope["actividad"] == val].index
        elif scope_mode == "Un territorio":
            with sc2:
                val = st.selectbox("Territorio", sorted(visible_for_scope["territorio_potencial"].dropna().unique()), key="scenario_scope_territory")
            scope_indices = visible_for_scope[visible_for_scope["territorio_potencial"] == val].index
        elif scope_mode == "Un eslabonamiento":
            with sc2:
                val = st.selectbox("Eslabonamiento", sorted(visible_for_scope["tipo_eslabonamiento"].dropna().unique()), key="scenario_scope_linkage")
            scope_indices = visible_for_scope[visible_for_scope["tipo_eslabonamiento"] == val].index
        elif scope_mode == "Registros individuales":
            choices = visible_for_scope.index.tolist()
            with sc2:
                selected_rows = st.multiselect(
                    "Registros",
                    choices,
                    default=choices[:1],
                    format_func=lambda i: f"{visible_for_scope.loc[i,'mineral']} · {visible_for_scope.loc[i,'macrosector']} · {visible_for_scope.loc[i,'requerimiento_o_producto']}",
                    key="scenario_scope_rows"
                )
            scope_indices = pd.Index(selected_rows)

        with sc3:
            st.metric("Registros alcanzados", len(scope_indices))

        st.markdown("### 3. Ajustes rápidos y combinables")
        st.caption("Cada modificación es opcional. Podés activar una sola o combinar varias en la misma simulación.")

        q1, q2, q3 = st.columns(3)
        with q1:
            change_demand = st.checkbox("Modificar demanda", key="scenario_change_demand")
            demand_pct = st.number_input(
                "Variación de demanda (%)",
                min_value=-100.0, max_value=1000.0, value=0.0, step=5.0,
                disabled=not change_demand, key="scenario_demand_pct"
            )
            change_jobs = st.checkbox("Modificar empleo potencial", key="scenario_change_jobs")
            jobs_pct = st.number_input(
                "Variación de empleo (%)",
                min_value=-100.0, max_value=1000.0, value=0.0, step=5.0,
                disabled=not change_jobs, key="scenario_jobs_pct"
            )

        with q2:
            change_local = st.checkbox("Modificar participación Catamarca", key="scenario_change_local")
            local_pp = st.number_input(
                "Cambio Catamarca (puntos porcentuales)",
                min_value=-100.0, max_value=100.0, value=0.0, step=5.0,
                disabled=not change_local, key="scenario_local_pp"
            )
            change_rest = st.checkbox("Modificar participación resto Argentina", key="scenario_change_rest")
            rest_pp = st.number_input(
                "Cambio resto Argentina (p.p.)",
                min_value=-100.0, max_value=100.0, value=0.0, step=5.0,
                disabled=not change_rest, key="scenario_rest_pp"
            )

        with q3:
            change_imported = st.checkbox("Modificar participación importada", key="scenario_change_imported")
            imported_pp = st.number_input(
                "Cambio importado (p.p.)",
                min_value=-100.0, max_value=100.0, value=0.0, step=5.0,
                disabled=not change_imported, key="scenario_imported_pp"
            )
            auto_rebalance = st.checkbox(
                "Reequilibrar participaciones a 100%",
                value=True,
                help="Si se modifican porcentajes, reescala Catamarca / resto Argentina / importado para que la suma final sea 100%.",
                key="scenario_rebalance"
            )

        st.markdown("#### Cambios cualitativos masivos · opcionales")
        cq1, cq2, cq3, cq4 = st.columns(4)
        with cq1:
            override_criticality = st.checkbox("Cambiar criticidad", key="scenario_override_crit")
            criticality_value = st.selectbox(
                "Nueva criticidad",
                sorted(df["criticidad"].dropna().astype(str).unique()),
                disabled=not override_criticality,
                key="scenario_crit_value"
            )
        with cq2:
            override_complexity = st.checkbox("Cambiar complejidad", key="scenario_override_complex")
            complexity_value = st.selectbox(
                "Nueva complejidad",
                sorted(df["complejidad_tecnica"].dropna().astype(str).unique()),
                disabled=not override_complexity,
                key="scenario_complex_value"
            )
        with cq3:
            override_capacity = st.checkbox("Cambiar capacidad local", key="scenario_override_capacity")
            capacity_value = st.selectbox(
                "Nueva capacidad",
                sorted(df["capacidad_local_demo"].dropna().astype(str).unique()),
                disabled=not override_capacity,
                key="scenario_capacity_value"
            )
        with cq4:
            override_frequency = st.checkbox("Cambiar frecuencia", key="scenario_override_frequency")
            frequency_value = st.selectbox(
                "Nueva frecuencia",
                sorted(df["frecuencia"].dropna().astype(str).unique()),
                disabled=not override_frequency,
                key="scenario_frequency_value"
            )

        apply_col, info_col = st.columns([1, 2.2])
        with apply_col:
            apply_quick = st.button("Aplicar ajustes al escenario", type="primary", key="apply_scenario_changes")
        with info_col:
            st.caption("Los ajustes se acumulan. Podés aplicar una combinación, cambiar el alcance y volver a aplicar otra. 'Restaurar escenario base' elimina todos los cambios.")

        if apply_quick:
            if len(scope_indices) == 0:
                st.warning("No hay registros seleccionados para modificar.")
            else:
                work = scenario_df.copy()
                if change_demand:
                    work.loc[scope_indices, "demanda_anual_usd_demo"] = (
                        work.loc[scope_indices, "demanda_anual_usd_demo"] * (1 + demand_pct / 100)
                    ).clip(lower=0)
                if change_jobs:
                    work.loc[scope_indices, "empleo_local_potencial_demo"] = (
                        work.loc[scope_indices, "empleo_local_potencial_demo"] * (1 + jobs_pct / 100)
                    ).clip(lower=0)
                if change_local:
                    work.loc[scope_indices, "participacion_catamarca_pct_demo"] = (
                        work.loc[scope_indices, "participacion_catamarca_pct_demo"] + local_pp
                    ).clip(lower=0, upper=100)
                if change_rest:
                    work.loc[scope_indices, "participacion_resto_arg_pct_demo"] = (
                        work.loc[scope_indices, "participacion_resto_arg_pct_demo"] + rest_pp
                    ).clip(lower=0, upper=100)
                if change_imported:
                    work.loc[scope_indices, "participacion_importada_pct_demo"] = (
                        work.loc[scope_indices, "participacion_importada_pct_demo"] + imported_pp
                    ).clip(lower=0, upper=100)
                if (change_local or change_rest or change_imported) and auto_rebalance:
                    work = rebalance_participations(work, scope_indices)
                if override_criticality:
                    work.loc[scope_indices, "criticidad"] = criticality_value
                if override_complexity:
                    work.loc[scope_indices, "complejidad_tecnica"] = complexity_value
                if override_capacity:
                    work.loc[scope_indices, "capacidad_local_demo"] = capacity_value
                if override_frequency:
                    work.loc[scope_indices, "frecuencia"] = frequency_value

                st.session_state["sipm_scenario_df"] = prepare_scenario_data(work)
                st.session_state["sipm_scenario_source"] = st.session_state.get("sipm_scenario_source", "Base SIPM") + " · modificado"
                st.session_state["sipm_scenario_active"] = True
                st.session_state["sipm_reset_filters"] = True
                st.rerun()

        st.markdown("### 4. Edición detallada · todas las variables")
        st.markdown(
            '<div class="drill"><b>Para máxima flexibilidad:</b> esta tabla permite modificar directamente cualquier variable original de los registros seleccionados: '
            'mineral, eslabonamiento, etapa, sector, actividad, requerimiento, frecuencia, demanda, participaciones, empleo, criticidad, complejidad, '
            'capacidad, territorio, acciones, barreras, beneficios, certificaciones, cadena de valor, fuente y notas. '
            'Las variables calculadas se regeneran al guardar.</div>',
            unsafe_allow_html=True
        )

        raw_edit_cols = [c for c in SCENARIO_REQUIRED_COLUMNS if c in scenario_df.columns]
        edit_frame = scenario_df.loc[scope_indices, raw_edit_cols].copy()

        edited_frame = st.data_editor(
            edit_frame,
            use_container_width=True,
            hide_index=False,
            num_rows="fixed",
            height=min(520, max(220, 38 * (len(edit_frame) + 1))),
            key="scenario_detail_editor",
            disabled=["id"] if "id" in raw_edit_cols else False,
            column_config={
                "demanda_anual_usd_demo": st.column_config.NumberColumn("Demanda anual USD", min_value=0.0, format="$ %.0f"),
                "participacion_catamarca_pct_demo": st.column_config.NumberColumn("% Catamarca", min_value=0.0, max_value=100.0, format="%.1f"),
                "participacion_resto_arg_pct_demo": st.column_config.NumberColumn("% resto Argentina", min_value=0.0, max_value=100.0, format="%.1f"),
                "participacion_importada_pct_demo": st.column_config.NumberColumn("% importado", min_value=0.0, max_value=100.0, format="%.1f"),
                "empleo_local_potencial_demo": st.column_config.NumberColumn("Empleo potencial", min_value=0.0, format="%.0f"),
            }
        )

        de1, de2 = st.columns([1, 2.2])
        with de1:
            save_detail = st.button("Guardar edición detallada", key="save_scenario_detail")
        with de2:
            rebalance_detail = st.checkbox(
                "Al guardar, reequilibrar automáticamente los tres porcentajes a 100%",
                value=True,
                key="scenario_detail_rebalance"
            )

        if save_detail:
            work = scenario_df.copy()
            # Conserva el índice original para reemplazar exactamente los registros editados.
            for col in raw_edit_cols:
                work.loc[edited_frame.index, col] = edited_frame[col]
            if rebalance_detail and len(edited_frame.index) > 0:
                work = rebalance_participations(work, edited_frame.index)
            st.session_state["sipm_scenario_df"] = prepare_scenario_data(work)
            st.session_state["sipm_scenario_source"] = st.session_state.get("sipm_scenario_source", "Base SIPM") + " · edición detallada"
            st.session_state["sipm_scenario_active"] = True
            st.session_state["sipm_reset_filters"] = True
            st.rerun()

        st.markdown("### 5. Resultado del escenario · comparación con la base")
        scenario_df = prepare_scenario_data(st.session_state["sipm_scenario_df"])
        scenario_visible = filter_like_sidebar(scenario_df)
        base_visible = base_f.copy()

        base_kpi = scenario_kpis(base_visible)
        sc_kpi = scenario_kpis(scenario_visible)

        st.markdown(
            '<div class="sipm-note"><b>ESCENARIO SIMULADO Y ACTIVO:</b> los resultados pueden contener datos cargados o modificaciones realizadas durante la sesión. '
            'Mientras el escenario esté activo, <b>todas las pestañas del SIPM</b> se calculan con estos valores. No reemplazan la base SIPM ni deben interpretarse como resultados observados.</div>',
            unsafe_allow_html=True
        )

        rk1, rk2, rk3, rk4 = st.columns(4)
        rk1.metric(
            "Demanda mapeada",
            f"US$ {sc_kpi['demanda']/1e6:,.1f} M",
            f"{(sc_kpi['demanda']-base_kpi['demanda'])/1e6:+,.1f} M vs base"
        )
        rk2.metric(
            "Captura local",
            f"{sc_kpi['captura_pct']:.1%}",
            f"{(sc_kpi['captura_pct']-base_kpi['captura_pct'])*100:+.1f} p.p."
        )
        rk3.metric(
            "Gasto fuera de Catamarca",
            f"US$ {sc_kpi['gasto_fuera']/1e6:,.1f} M",
            f"{(sc_kpi['gasto_fuera']-base_kpi['gasto_fuera'])/1e6:+,.1f} M vs base",
            delta_color="inverse"
        )
        rk4.metric(
            "Empleo potencial",
            f"{sc_kpi['empleo']:,.0f}",
            f"{sc_kpi['empleo']-base_kpi['empleo']:+,.0f} vs base"
        )

        comparison = pd.DataFrame({
            "Indicador": ["Demanda", "Captura local USD", "Gasto fuera", "Empleo potencial"],
            "Base": [base_kpi["demanda"], base_kpi["captura_valor"], base_kpi["gasto_fuera"], base_kpi["empleo"]],
            "Escenario": [sc_kpi["demanda"], sc_kpi["captura_valor"], sc_kpi["gasto_fuera"], sc_kpi["empleo"]],
        })
        comparison_long = comparison.melt(id_vars="Indicador", var_name="Situación", value_name="Valor")
        fig_sc = px.bar(
            comparison_long,
            x="Indicador", y="Valor", color="Situación", barmode="group",
            color_discrete_map={"Base":"#AEBCC4", "Escenario":"#2A6F8E"},
            labels={"Valor":"Valor comparativo", "Indicador":""}
        )
        fig_sc.update_layout(height=420, margin=dict(t=15,l=0,r=10,b=10))
        st.plotly_chart(fig_sc, use_container_width=True)
        st.caption("El gráfico compara magnitudes de distinta unidad sólo para visualizar dirección y tamaño relativo del cambio. Los indicadores superiores son la lectura principal.")

        # Cambios por registro usando ID cuando está disponible.
        if "id" in df.columns and "id" in scenario_df.columns:
            base_compare = df.set_index("id")
            sc_compare = scenario_df.set_index("id")
            common_ids = base_compare.index.intersection(sc_compare.index)
            changes = pd.DataFrame(index=common_ids)
            changes["mineral"] = sc_compare.loc[common_ids, "mineral"]
            changes["macrosector"] = sc_compare.loc[common_ids, "macrosector"]
            changes["actividad"] = sc_compare.loc[common_ids, "actividad"]
            changes["requerimiento"] = sc_compare.loc[common_ids, "requerimiento_o_producto"]
            changes["Δ demanda USD"] = sc_compare.loc[common_ids, "demanda_anual_usd_demo"] - base_compare.loc[common_ids, "demanda_anual_usd_demo"]
            changes["Δ Catamarca p.p."] = sc_compare.loc[common_ids, "participacion_catamarca_pct_demo"] - base_compare.loc[common_ids, "participacion_catamarca_pct_demo"]
            changes["Δ empleo"] = sc_compare.loc[common_ids, "empleo_local_potencial_demo"] - base_compare.loc[common_ids, "empleo_local_potencial_demo"]
            changes["magnitud_cambio"] = (
                changes["Δ demanda USD"].abs() / 1e6
                + changes["Δ Catamarca p.p."].abs()
                + changes["Δ empleo"].abs()
            )
            changed = changes[changes["magnitud_cambio"] > 0].sort_values("magnitud_cambio", ascending=False).drop(columns="magnitud_cambio")
            if not changed.empty:
                st.markdown("#### Registros con mayores cambios cuantitativos")
                st.dataframe(changed.head(20), use_container_width=True)
            else:
                st.caption("Todavía no hay cambios cuantitativos respecto de la base SIPM.")

        st.markdown("### 6. Guardar el escenario para reutilizarlo")
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "Descargar escenario CSV",
                scenario_df.to_csv(index=False).encode("utf-8-sig"),
                "sipm_escenario.csv",
                "text/csv",
                key="download_scenario_csv"
            )
        with dl2:
            excel_buffer = BytesIO()
            try:
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    scenario_df.to_excel(writer, index=False, sheet_name="Escenario SIPM")
                st.download_button(
                    "Descargar escenario Excel",
                    excel_buffer.getvalue(),
                    "sipm_escenario.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_scenario_xlsx"
                )
            except Exception:
                st.caption("Para exportar Excel, agregá openpyxl a requirements.txt. La descarga CSV funciona igualmente.")


# ------------------------------------------------
# POLÍTICAS PÚBLICAS Y CAPITAL HUMANO
# ------------------------------------------------
with tabs[7]:
    st.subheader("De la matriz a la política pública")
    st.markdown(
        '<div class="chart-explain"><b>Qué muestra:</b> transforma las brechas productivas de la matriz en decisiones accionables. '
        'El objetivo es responder tres preguntas: <b>qué debería hacer el Estado, qué perfiles de capital humano deberían fortalecerse '
        'y cómo debería reaccionar el sistema educativo.</b> Las cantidades son escenarios demostrativos agregados, no vacantes reales.</div>',
        unsafe_allow_html=True
    )

    if scenario_active:
        st.markdown("### Lectura automática del escenario → agenda de decisión")
        st.markdown(
            '<div class="sipm-note"><b>Esta es la función central del SIPM:</b> no sólo mostrar qué cambió, sino traducir los cambios de demanda, captura local, complejidad, territorio y empleo en una agenda inicial de acción pública. '
            'Las recomendaciones son reglas demostrativas y deben validarse con información real antes de transformarse en política.</div>',
            unsafe_allow_html=True
        )
        ctx_policy = scenario_change_context(base_f, f)
        pp1,pp2,pp3,pp4 = st.columns(4)
        pp1.metric("Δ demanda", f"US$ {ctx_policy['delta_demanda']/1e6:+,.1f} M")
        pp2.metric("Δ captura local", f"{ctx_policy['delta_captura_pp']:+.1f} p.p.")
        pp3.metric("Δ gasto fuera", f"US$ {ctx_policy['delta_gasto_fuera']/1e6:+,.1f} M")
        pp4.metric("Δ empleo potencial", f"{ctx_policy['delta_empleo']:+,.0f}")

        policy_actions = dynamic_policy_actions(base_f, f)
        for i,pa in enumerate(policy_actions,1):
            st.markdown(
                f'<div class="reco"><strong>{i}. {pa["frente"]} · prioridad {pa["prioridad"]}</strong><br>'
                f'<b>Señal del escenario:</b> {pa["evidencia"]}<br>'
                f'<b>Acción sugerida:</b> {pa["accion"]}<br>'
                f'<b>Actores:</b> {pa["actores"]}</div>',
                unsafe_allow_html=True
            )

        st.markdown("### Impacto del escenario sobre capital humano")
        pdeltas = profile_delta_table(base_f, f)
        pdeltas_nonzero = pdeltas[pdeltas["delta"].abs() > 0].copy()
        if not pdeltas_nonzero.empty:
            fig_prof_delta = px.bar(
                pdeltas_nonzero.head(12).sort_values("delta"),
                x="delta", y="perfil", orientation="h", text="delta",
                labels={"delta":"Cambio de personas equivalentes vs base","perfil":""}
            )
            fig_prof_delta.update_traces(marker_color="#C99A3B", texttemplate="%{text:+.0f}")
            fig_prof_delta.update_layout(height=500,showlegend=False,margin=dict(t=5,l=0,r=30,b=10))
            st.plotly_chart(fig_prof_delta,use_container_width=True)
            top_profiles = pdeltas_nonzero.sort_values("delta",ascending=False).head(5)
            st.markdown("#### Respuesta educativa prioritaria ante este escenario")
            for _,pr in top_profiles.iterrows():
                if pr["delta"] <= 0:
                    continue
                horizon, action, actors = education_action(pr["perfil"])
                st.markdown(
                    f'<div class="drill"><b>{pr["perfil"]}</b> · Δ {pr["delta"]:+,.0f} personas equivalentes<br>'
                    f'<b>Horizonte:</b> {horizon}<br><b>Respuesta:</b> {action}<br><b>Actores:</b> {actors}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("El escenario actual no modifica el empleo potencial ni la composición sectorial suficiente para alterar la estimación de perfiles respecto de la base visible.")

        st.markdown("### Agenda estructural de política pública")
    else:
        st.markdown("### 1. Agenda de política pública")

    pc1,pc2=st.columns(2)
    for i,(title,desc) in enumerate(PUBLIC_POLICY_PILLARS):
        target_col=pc1 if i%2==0 else pc2
        with target_col:
            st.markdown(f'<div class="reco"><strong>{title}</strong><br>{desc}</div>',unsafe_allow_html=True)

    st.markdown("### Capital humano asociado a la selección actual")
    profiles=estimate_profiles(f)
    if not profiles.empty:
        profiles["personas_demo"]=profiles["personas_demo"].round().astype(int)
        figp=px.bar(
            profiles.head(12).sort_values("personas_demo"),
            x="personas_demo",y="perfil",orientation="h",
            text="personas_demo",
            labels={"personas_demo":"Personas equivalentes · escenario demo","perfil":""}
        )
        figp.update_traces(marker_color="#2A6F8E",textposition="outside")
        figp.update_layout(height=520,showlegend=False,margin=dict(t=10,l=0,r=30,b=10))
        st.plotly_chart(figp,use_container_width=True)
        st.markdown(
            '<div class="sipm-note"><b>Cómo leerlo:</b> no significa que existan hoy estas vacantes. '
            'Es una traducción demostrativa del empleo potencial de las actividades seleccionadas hacia familias de perfiles. '
            'En el proyecto real, estos coeficientes deberían calibrarse con encuestas laborales, empresas, cámaras y datos educativos.</div>',
            unsafe_allow_html=True
        )

        st.markdown("### ¿Qué debería hacer Universidad y Educación?")
        selected_profile=st.selectbox(
            "Elegí un perfil para ver una respuesta educativa",
            profiles["perfil"].tolist(),
            key="education_profile"
        )
        prow=profiles[profiles["perfil"]==selected_profile].iloc[0]
        horizon,action,actors=education_action(selected_profile)

        e1,e2,e3=st.columns([1,1.4,1.2])
        e1.metric("Demanda equivalente demo",f"{int(prow['personas_demo']):,}")
        e2.markdown(f"**Horizonte sugerido**  \n{horizon}")
        e3.markdown(f"**Actores**  \n{actors}")
        st.markdown(f'<div class="reco"><strong>Respuesta recomendada</strong><br>{action}</div>',unsafe_allow_html=True)

        st.markdown("#### Acciones educativas estructurales")
        st.markdown(
            "- **Observatorio de perfiles mineros:** actualizar anualmente qué profesionales, técnicos y oficios aparecen como cuellos de botella.\n"
            "- **Becas orientadas por demanda:** priorizar carreras y tecnicaturas donde la matriz detecte déficit futuro.\n"
            "- **Microcredenciales y diplomaturas:** responder rápidamente a automatización, mantenimiento, ambiente, datos, calidad y procesos.\n"
            "- **Prácticas profesionalizantes:** vincular estudiantes con empresas y proveedores antes del egreso.\n"
            "- **Formación territorial:** llevar trayectos técnicos a Belén, Tinogasta–Fiambalá, Andalgalá y Antofagasta cuando la demanda lo justifique.\n"
            "- **Investigación aplicada:** convertir brechas de proveedores o procesos en proyectos de laboratorio, tesis, innovación y transferencia tecnológica."
        )

        st.markdown("### La ventaja de Catamarca: no parte de cero")
        st.markdown(
            "La UNCA ya cuenta con carreras directamente vinculadas al ecosistema minero —como **Ingeniería de Minas, Geología, "
            "Ingeniería Electrónica, Informática y Procesamiento de Salmuera de Litio**— y también con nuevas capacidades en "
            "**Ciencia de Datos y Energías Renovables**. El SIPM permitiría conectar esa oferta académica con la demanda futura, "
            "detectar faltantes y decidir dónde conviene ampliar, especializar o crear trayectos más cortos."
        )
        u1,u2=st.columns(2)
        with u1:
            st.link_button("Oferta académica UNCA","https://www.unca.edu.ar/carreras")
        with u2:
            st.link_button("Facultad de Tecnología y Ciencias Aplicadas","https://www.unca.edu.ar/tecno")

        st.markdown("### Antecedentes que muestran que esto es posible")
        with st.expander("Salta · educación alineada con demanda minera e industrial"):
            st.markdown(
                "En 2026 Salta presentó un Plan de Especialización para el Sector Minero e Industrial dirigido a estudiantes "
                "de escuelas técnicas y nivel superior, articulado con cámaras, proveedores y sector académico."
            )
            st.markdown("**Aplicación SIPM:** usar la matriz para decidir qué especializaciones ofrecer, en qué territorio y con qué prioridad.")
            st.link_button("Ver antecedente oficial","https://www.salta.gob.ar/prensa/noticias/estudiantes-saltenios-se-formaran-en-competencias-que-demandan-los-sectores-minero-e-industrial-107830")
        with st.expander("Jujuy · modificación curricular vinculada a la matriz productiva"):
            st.markdown(
                "Jujuy desarrolló formación docente en minería e industria del litio y planteó adaptar diseños curriculares "
                "para acompañar la matriz productiva provincial."
            )
            st.markdown("**Aplicación SIPM:** convertir las brechas detectadas por la matriz en insumos periódicos para la planificación educativa.")
            st.link_button("Ver antecedente oficial","https://educacion.jujuy.gob.ar/2023/05/18/formacion-en-mineria-e-industria-de-litio-docentes-preparados-para-la-matriz-productiva-de-jujuy/")

        st.markdown(
            '<div class="sipm-note"><b>Principio metodológico:</b> el SIPM debería orientar educación con información agregada. '
            'No necesita conocer el plan de contratación individual de cada minera; necesita identificar tendencias por perfil, '
            'sector, territorio y horizonte temporal.</div>',
            unsafe_allow_html=True
        )


# ------------------------------------------------
# MATRIZ
# ------------------------------------------------
with tabs[8]:
    st.subheader("Matriz integral")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> el detalle que alimenta todo el SIPM. Cada registro conecta mineral, etapa, actividad, requerimiento, demanda, participación local, complejidad, territorio, barreras y acción sugerida. El dashboard resume; la matriz explica por qué.</div>', unsafe_allow_html=True)
    q=st.text_input("Buscar actividad, sector, producto, territorio o barrera")
    show=f.copy()
    if q:
        mask=show.astype(str).apply(lambda c:c.str.contains(q,case=False,na=False)).any(axis=1)
        show=show[mask]

    st.caption(f"{len(show)} registros visibles.")
    st.dataframe(
        show[
            ["mineral","tipo_eslabonamiento","etapa_proyecto","macrosector","actividad",
             "requerimiento_o_producto","demanda_anual_usd_demo","participacion_catamarca_pct_demo",
             "empleo_local_potencial_demo","criticidad","complejidad_tecnica","capacidad_local_demo",
             "territorio_potencial","accion_sugerida"]
        ],
        use_container_width=True,hide_index=True,height=540,
        column_config={
            "demanda_anual_usd_demo":st.column_config.NumberColumn("Demanda demo",format="$ %.0f"),
            "participacion_catamarca_pct_demo":st.column_config.ProgressColumn("% Catamarca",min_value=0,max_value=100),
            "empleo_local_potencial_demo":st.column_config.NumberColumn("Empleo potencial")
        }
    )
    st.download_button(
        "Descargar selección CSV",
        show.to_csv(index=False).encode("utf-8-sig"),
        "sipm_seleccion.csv",
        "text/csv"
    )

st.divider()
st.caption("SIPM · Demo institucional. Las actividades y cadenas son una estructura de demostración; los valores cuantitativos deben reemplazarse por información relevada y validada.")
