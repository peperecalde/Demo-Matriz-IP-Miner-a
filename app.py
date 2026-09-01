import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
import math
from sipm_engine import (
    DERIVED_COLUMNS as ENGINE_DERIVED_COLUMNS,
    PARTICIPATION_COLS,
    prepare_scenario as engine_prepare_scenario,
    apply_participation_deltas,
    validate_scenario_math,
    baseline_invariance_check,
    exact_demand_change_check,
)

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
# UTILIDADES PARA ESCENARIOS · MOTOR MATEMÁTICO v2.9
# ------------------------------------------------
# La Base SIPM permanece inalterada. El motor de escenarios recalcula las
# variables derivadas y valida todas las identidades antes de mostrar resultados.
SCENARIO_DERIVED_COLUMNS = list(dict.fromkeys([
    "captura_local_usd_demo",
    "gasto_fuera_catamarca_usd_demo",
    "puntaje_oportunidad_demo",
    "prioridad_demo",
    *ENGINE_DERIVED_COLUMNS,
]))
SCENARIO_REQUIRED_COLUMNS = [c for c in df.columns if c not in SCENARIO_DERIVED_COLUMNS]


def prepare_scenario_data(frame):
    manual_ids = st.session_state.get("sipm_manual_employment_ids", [])
    return engine_prepare_scenario(frame, df, manual_employment_ids=manual_ids)


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
    """Compatibilidad interna. En v2.9 los cambios rápidos usan cierre explícito al 100%."""
    out = frame.copy()
    idx = out.index.intersection(pd.Index(indices))
    if len(idx) == 0:
        return out
    sums = out.loc[idx, PARTICIPATION_COLS].sum(axis=1)
    if not ((sums - 100).abs() <= 1e-6).all():
        raise ValueError("Las participaciones deben sumar exactamente 100%.")
    return out

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
# SIDEBAR
# ------------------------------------------------
with st.sidebar:
    st.markdown("## ⛏️ SIPM")
    st.markdown("**Inteligencia Productiva Minera**")
    st.caption("PROTOTIPO INSTITUCIONAL · CATAMARCA")
    st.divider()
    st.markdown("### Filtros")
    minerals = st.multiselect("Mineral", sorted(df["mineral"].unique()), default=sorted(df["mineral"].unique()))
    linkage_options = ["Aguas arriba", "Aguas abajo"]
    linkages = st.multiselect(
        "Eslabonamiento",
        linkage_options,
        default=linkage_options
    )
    stages = st.multiselect("Etapa del proyecto", sorted(df["etapa_proyecto"].unique()), default=sorted(df["etapa_proyecto"].unique()))
    territories = st.multiselect("Territorio potencial", sorted(df["territorio_potencial"].unique()), default=sorted(df["territorio_potencial"].unique()))
    st.divider()
    st.markdown("**Lectura rápida**")
    st.caption("Los filtros actualizan todo el tablero. Los valores económicos y de empleo son simulados para demostrar la metodología.")

f = df[
    df["mineral"].isin(minerals) &
    df["tipo_eslabonamiento"].isin(linkages) &
    df["etapa_proyecto"].isin(stages) &
    df["territorio_potencial"].isin(territories)
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

tabs=st.tabs([
    "🏠 Inicio","🌐 Ecosistema","⬅️ Aguas arriba","➡️ Aguas abajo",
    "🎯 Oportunidades","📍 Territorio","🧪 Simulador","🧭 Escenarios",
    "🎓 Políticas y talento","📋 Matriz"
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

    st.markdown(
        '<div class="sipm-note"><b>El Simulador permanece deliberadamente simple:</b> '
        'sirve para analizar una oportunidad puntual. Para construir y comparar escenarios integrales '
        'utilizá la pestaña <b>Escenarios</b>, donde la Base SIPM permanece siempre intacta.</div>',
        unsafe_allow_html=True
    )


# ------------------------------------------------
# ESCENARIOS · COMPARACIÓN ESTÁTICA
# ------------------------------------------------
with tabs[7]:
    st.subheader("Escenarios · comparación integral contra la Base SIPM")
    st.markdown(
        '<div class="chart-explain"><b>Principio de lectura:</b> esta pestaña nunca reemplaza ni modifica la Base SIPM. '
        'El escenario es una copia de trabajo. Cada resultado se presenta en formato <b>Base SIPM vs. Escenario</b> '
        'para que pueda verse qué cambió, cuánto cambió y qué decisiones de política pública podrían derivarse.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sipm-note"><b>Importante:</b> las demás pestañas continúan mostrando exclusivamente la información original. '
        'Todo el análisis contrafactual queda contenido aquí, aun cuando la pantalla sea extensa.</div>',
        unsafe_allow_html=True
    )

    # El escenario vive sólo dentro del Simulador y no altera las demás pestañas.
    if "sipm_manual_employment_ids" not in st.session_state:
        st.session_state["sipm_manual_employment_ids"] = []
    if "sipm_scenario_audit" not in st.session_state:
        st.session_state["sipm_scenario_audit"] = {
            "base_calculo": "Base SIPM original",
            "universo": "Sin modificaciones",
            "registros": 0,
            "supuestos": [],
            "ajustes_modelo": [],
        }
    if "sipm_scenario_df" not in st.session_state:
        st.session_state["sipm_scenario_df"] = prepare_scenario_data(df.copy())
        st.session_state["sipm_scenario_source"] = "Base SIPM"

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
                    use_file_jobs = st.checkbox(
                        "Usar el empleo del archivo como override manual",
                        value=False,
                        key="scenario_file_jobs_override",
                        help="Desactivado por defecto: el motor recalcula empleo a partir de captura local y estructura sectorial. Activarlo sólo si el archivo contiene una estimación externa de empleo que se desea imponer."
                    )
                    if st.button("Usar archivo cargado como escenario", type="primary", key="use_uploaded_scenario"):
                        try:
                            # Antes de modelar exigimos que el archivo respete la identidad de participaciones.
                            p_sums = uploaded_df[PARTICIPATION_COLS].apply(pd.to_numeric, errors="coerce").sum(axis=1)
                            if not ((p_sums - 100).abs() <= 1e-6).all():
                                bad = uploaded_df.loc[(p_sums - 100).abs() > 1e-6, "id"].tolist()[:10]
                                st.error(f"Archivo rechazado: Catamarca + resto Argentina + importado debe sumar 100% en cada fila. IDs: {bad}")
                            else:
                                st.session_state["sipm_manual_employment_ids"] = uploaded_df["id"].tolist() if use_file_jobs else []
                                modeled = engine_prepare_scenario(uploaded_df, df, st.session_state["sipm_manual_employment_ids"])
                                valid_math, math_errors = validate_scenario_math(modeled)
                                if not valid_math:
                                    st.error("Archivo rechazado por inconsistencias matemáticas: " + " | ".join(math_errors))
                                else:
                                    st.session_state["sipm_scenario_df"] = modeled
                                    st.session_state["sipm_scenario_source"] = f"Archivo: {uploaded_scenario.name}"
                                    st.session_state["sipm_scenario_audit"] = {
                                        "base_calculo": "Archivo externo comparado contra Base SIPM original",
                                        "universo": "Matriz cargada",
                                        "registros": len(modeled),
                                        "supuestos": ["Valores de entrada tomados del archivo cargado"],
                                        "ajustes_modelo": ["Empleo manual del archivo" if use_file_jobs else "Empleo recalculado automáticamente"],
                                    }
                                    st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo construir el escenario: {e}")
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")

    with src2:
        st.markdown(f"**Fuente actual del escenario:**  \n{st.session_state['sipm_scenario_source']}")
        st.caption("El escenario queda en la sesión. Por defecto cada ajuste nuevo parte de la Base SIPM original; la acumulación sólo ocurre si se selecciona expresamente.")
        if st.button("↺ Restaurar escenario base", key="restore_scenario"):
            st.session_state["sipm_manual_employment_ids"] = []
            st.session_state["sipm_scenario_df"] = engine_prepare_scenario(df.copy(), df, [])
            st.session_state["sipm_scenario_source"] = "Base SIPM"
            st.session_state["sipm_scenario_audit"] = {
                "base_calculo": "Base SIPM original",
                "universo": "Sin modificaciones",
                "registros": 0,
                "supuestos": [],
                "ajustes_modelo": [],
            }
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
        st.caption("Cada cambio es un supuesto de entrada. El motor recalcula automáticamente captura, gasto fuera, empleo, oportunidades, presión de política y capital humano.")

        base_mode = st.radio(
            "¿Sobre qué base aplicar este ajuste?",
            ["Base SIPM original", "Escenario actual (acumular deliberadamente)"],
            index=0,
            horizontal=True,
            key="scenario_application_base",
            help="Por seguridad, cada nuevo ajuste parte de la Base SIPM original. Elegí acumular sólo cuando quieras construir un escenario por etapas."
        )

        q1, q2, q3 = st.columns(3)
        with q1:
            change_demand = st.checkbox("Modificar demanda", key="scenario_change_demand")
            demand_pct = st.number_input(
                "Variación de demanda (%)", min_value=-100.0, max_value=1000.0,
                value=0.0, step=5.0, disabled=not change_demand, key="scenario_demand_pct"
            )
            manual_jobs = st.checkbox(
                "Sobrescribir empleo manualmente (avanzado)",
                value=False,
                key="scenario_change_jobs",
                help="Por defecto el empleo es una variable derivada. Activá esto sólo si tenés una estimación externa que deba prevalecer sobre el modelo."
            )
            jobs_pct = st.number_input(
                "Variación manual de empleo (%)", min_value=-100.0, max_value=1000.0,
                value=0.0, step=5.0, disabled=not manual_jobs, key="scenario_jobs_pct"
            )

        with q2:
            change_local = st.checkbox("Modificar participación Catamarca", key="scenario_change_local")
            local_pp = st.number_input(
                "Cambio Catamarca (puntos porcentuales)", min_value=-100.0, max_value=100.0,
                value=0.0, step=5.0, disabled=not change_local, key="scenario_local_pp"
            )
            change_rest = st.checkbox("Modificar participación resto Argentina", key="scenario_change_rest")
            rest_pp = st.number_input(
                "Cambio resto Argentina (p.p.)", min_value=-100.0, max_value=100.0,
                value=0.0, step=5.0, disabled=not change_rest, key="scenario_rest_pp"
            )

        with q3:
            change_imported = st.checkbox("Modificar participación importada", key="scenario_change_imported")
            imported_pp = st.number_input(
                "Cambio importado (p.p.)", min_value=-100.0, max_value=100.0,
                value=0.0, step=5.0, disabled=not change_imported, key="scenario_imported_pp"
            )
            auto_rebalance = st.checkbox(
                "Cerrar participaciones automáticamente a 100%", value=True,
                help="Respeta los porcentajes que modificaste y hace que las columnas no modificadas absorban el residual. Nunca reescala silenciosamente los valores explícitos.",
                key="scenario_rebalance"
            )

        st.markdown("#### Cambios cualitativos masivos · opcionales")
        cq1, cq2, cq3, cq4 = st.columns(4)
        with cq1:
            override_criticality = st.checkbox("Cambiar criticidad", key="scenario_override_crit")
            criticality_value = st.selectbox("Nueva criticidad", sorted(df["criticidad"].dropna().astype(str).unique()), disabled=not override_criticality, key="scenario_crit_value")
        with cq2:
            override_complexity = st.checkbox("Cambiar complejidad", key="scenario_override_complex")
            complexity_value = st.selectbox("Nueva complejidad", sorted(df["complejidad_tecnica"].dropna().astype(str).unique()), disabled=not override_complexity, key="scenario_complex_value")
        with cq3:
            override_capacity = st.checkbox("Cambiar capacidad local", key="scenario_override_capacity")
            capacity_value = st.selectbox("Nueva capacidad", sorted(df["capacidad_local_demo"].dropna().astype(str).unique()), disabled=not override_capacity, key="scenario_capacity_value")
        with cq4:
            override_frequency = st.checkbox("Cambiar frecuencia", key="scenario_override_frequency")
            frequency_value = st.selectbox("Nueva frecuencia", sorted(df["frecuencia"].dropna().astype(str).unique()), disabled=not override_frequency, key="scenario_frequency_value")

        apply_col, info_col = st.columns([1, 2.2])
        with apply_col:
            apply_quick = st.button("Aplicar y validar escenario", type="primary", key="apply_scenario_changes")
        with info_col:
            st.caption("El resultado sólo se guarda si supera las validaciones matemáticas. La opción por defecto vuelve siempre a la Base SIPM original.")

        if apply_quick:
            if len(scope_indices) == 0:
                st.warning("No hay registros seleccionados para modificar.")
            else:
                try:
                    # IDs, no posiciones: evita errores si un archivo fue reordenado.
                    selected_ids = scenario_df.loc[scope_indices, "id"].tolist()
                    if base_mode == "Base SIPM original":
                        work = df.copy()
                        work_indices = work.index[work["id"].isin(selected_ids)]
                        manual_ids = set()
                    else:
                        work = scenario_df.copy()
                        work_indices = work.index[work["id"].isin(selected_ids)]
                        manual_ids = set(st.session_state.get("sipm_manual_employment_ids", []))

                    assumptions = []
                    model_notes = []

                    if change_demand:
                        before_demand = float(work.loc[work_indices, "demanda_anual_usd_demo"].sum())
                        work.loc[work_indices, "demanda_anual_usd_demo"] = (
                            pd.to_numeric(work.loc[work_indices, "demanda_anual_usd_demo"], errors="coerce") * (1 + demand_pct / 100.0)
                        )
                        after_input_demand = float(work.loc[work_indices, "demanda_anual_usd_demo"].sum())
                        expected = before_demand * (1 + demand_pct / 100.0)
                        if not math.isclose(after_input_demand, expected, rel_tol=1e-12, abs_tol=0.01):
                            raise ValueError("Falló el control exacto de variación de demanda antes de modelar.")
                        assumptions.append(f"Demanda: {demand_pct:+.2f}%")

                    deltas = {}
                    changed_cols = []
                    if change_local:
                        deltas["participacion_catamarca_pct_demo"] = local_pp
                        changed_cols.append("participacion_catamarca_pct_demo")
                        assumptions.append(f"Participación Catamarca: {local_pp:+.2f} p.p.")
                    if change_rest:
                        deltas["participacion_resto_arg_pct_demo"] = rest_pp
                        changed_cols.append("participacion_resto_arg_pct_demo")
                        assumptions.append(f"Participación resto Argentina: {rest_pp:+.2f} p.p.")
                    if change_imported:
                        deltas["participacion_importada_pct_demo"] = imported_pp
                        changed_cols.append("participacion_importada_pct_demo")
                        assumptions.append(f"Participación importada: {imported_pp:+.2f} p.p.")
                    if changed_cols:
                        work, participation_notes = apply_participation_deltas(
                            work, work_indices, deltas, changed_cols, auto_balance=auto_rebalance
                        )
                        model_notes.extend(participation_notes)
                        if auto_rebalance:
                            untouched = [c for c in PARTICIPATION_COLS if c not in changed_cols]
                            if untouched:
                                model_notes.append("El residual para cerrar 100% fue absorbido por: " + ", ".join(untouched))

                    if override_criticality:
                        work.loc[work_indices, "criticidad"] = criticality_value
                        assumptions.append(f"Criticidad → {criticality_value}")
                    if override_complexity:
                        work.loc[work_indices, "complejidad_tecnica"] = complexity_value
                        assumptions.append(f"Complejidad → {complexity_value}")
                    if override_capacity:
                        work.loc[work_indices, "capacidad_local_demo"] = capacity_value
                        assumptions.append(f"Capacidad local → {capacity_value}")
                    if override_frequency:
                        work.loc[work_indices, "frecuencia"] = frequency_value
                        assumptions.append(f"Frecuencia → {frequency_value}")

                    if manual_jobs:
                        # Primero marcamos IDs como override y luego imponemos el valor manual.
                        manual_ids.update(selected_ids)
                        work.loc[work_indices, "empleo_local_potencial_demo"] = (
                            pd.to_numeric(work.loc[work_indices, "empleo_local_potencial_demo"], errors="coerce") * (1 + jobs_pct / 100.0)
                        ).clip(lower=0)
                        assumptions.append(f"OVERRIDE manual de empleo: {jobs_pct:+.2f}%")
                        model_notes.append("El empleo de los registros seleccionados NO fue calculado por el motor porque se activó un override manual.")
                    else:
                        # Si partimos de Base, los IDs vuelven al cálculo automático.
                        if base_mode == "Base SIPM original":
                            manual_ids.difference_update(selected_ids)
                        model_notes.append("Empleo recalculado automáticamente desde captura local, elasticidad sectorial y frecuencia.")

                    modeled = engine_prepare_scenario(work, df, manual_ids)
                    valid_math, math_errors = validate_scenario_math(modeled)
                    if not valid_math:
                        raise ValueError(" | ".join(math_errors))

                    # Test adicional del +x% desde base para evitar acumulaciones invisibles.
                    if change_demand and base_mode == "Base SIPM original":
                        ok_change, change_detail = exact_demand_change_check(df, selected_ids, demand_pct)
                        if not ok_change:
                            raise ValueError("Falló el test de variación exacta de demanda: " + change_detail)
                        model_notes.append("Control de demanda superado: el % aplicado coincide exactamente con la Base SIPM original.")

                    st.session_state["sipm_manual_employment_ids"] = sorted(manual_ids)
                    st.session_state["sipm_scenario_df"] = modeled
                    st.session_state["sipm_scenario_source"] = "Ajuste interno · " + base_mode
                    scope_text = scope_mode
                    if scope_mode != "Toda la selección actual":
                        scope_text += f" · {val if 'val' in locals() else ''}"
                    st.session_state["sipm_scenario_audit"] = {
                        "base_calculo": base_mode,
                        "universo": scope_text,
                        "registros": len(work_indices),
                        "supuestos": assumptions if assumptions else ["Sin cambios cuantitativos; sólo cambios cualitativos"],
                        "ajustes_modelo": model_notes,
                    }
                    st.rerun()
                except Exception as e:
                    st.error(f"🔴 ESCENARIO INVÁLIDO — no se guardaron cambios. {e}")

        st.markdown("### 4. Edición detallada · todas las variables")
        st.markdown(
            '<div class="drill"><b>Edición avanzada:</b> podés editar los supuestos originales de los registros. '
            '<b>Captura local, gasto fuera, puntaje, prioridad y demás salidas nunca se editan:</b> se recalculan. '
            'El empleo también se calcula automáticamente salvo que actives expresamente el override manual.</div>',
            unsafe_allow_html=True
        )
        allow_detail_jobs = st.checkbox(
            "Permitir override manual de empleo en la tabla",
            value=False,
            key="scenario_detail_job_override",
            help="Usar sólo cuando exista una estimación externa de empleo. Si está desactivado, empleo es una salida del modelo."
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
            disabled=(["id"] + ([] if allow_detail_jobs else ["empleo_local_potencial_demo"])) if "id" in raw_edit_cols else ([] if allow_detail_jobs else ["empleo_local_potencial_demo"]),
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
            save_detail = st.button("Validar y guardar edición detallada", key="save_scenario_detail")
        with de2:
            st.caption("En edición detallada las tres participaciones deben sumar exactamente 100%. Si no cierran, el sistema rechaza el escenario en lugar de corregirlo silenciosamente.")

        if save_detail:
            try:
                work = scenario_df.copy()
                for col in raw_edit_cols:
                    work.loc[edited_frame.index, col] = edited_frame[col]
                p_sums = work.loc[edited_frame.index, PARTICIPATION_COLS].apply(pd.to_numeric, errors="coerce").sum(axis=1)
                if not ((p_sums - 100).abs() <= 1e-6).all():
                    bad = work.loc[edited_frame.index].loc[(p_sums - 100).abs() > 1e-6, "id"].tolist()[:10]
                    raise ValueError(f"Las participaciones deben sumar 100%. Revisá IDs: {bad}")

                manual_ids = set(st.session_state.get("sipm_manual_employment_ids", []))
                selected_ids_detail = work.loc[edited_frame.index, "id"].tolist()
                if allow_detail_jobs:
                    manual_ids.update(selected_ids_detail)
                else:
                    manual_ids.difference_update(selected_ids_detail)
                modeled = engine_prepare_scenario(work, df, manual_ids)
                valid_math, math_errors = validate_scenario_math(modeled)
                if not valid_math:
                    raise ValueError(" | ".join(math_errors))
                st.session_state["sipm_manual_employment_ids"] = sorted(manual_ids)
                st.session_state["sipm_scenario_df"] = modeled
                st.session_state["sipm_scenario_source"] = "Edición detallada validada"
                st.session_state["sipm_scenario_audit"] = {
                    "base_calculo": "Escenario actual · edición detallada",
                    "universo": f"{len(edited_frame)} registros editados",
                    "registros": len(edited_frame),
                    "supuestos": ["Edición fila por fila de variables de entrada"],
                    "ajustes_modelo": ["Empleo manual" if allow_detail_jobs else "Empleo recalculado automáticamente", "Participaciones verificadas al 100%"],
                }
                st.rerun()
            except Exception as e:
                st.error(f"🔴 EDICIÓN INVÁLIDA — no se guardaron cambios. {e}")

        st.markdown("### 5. Lectura comparativa integral · Base SIPM vs. Escenario")
        scenario_df = prepare_scenario_data(st.session_state["sipm_scenario_df"])
        scenario_visible = filter_like_sidebar(scenario_df)
        base_visible = f.copy()

        st.markdown(
            '<div class="sipm-note"><b>ESCENARIO SIMULADO:</b> la columna <b>Base SIPM</b> muestra siempre la situación original '
            'bajo los mismos filtros laterales. La columna <b>Escenario</b> muestra únicamente las modificaciones realizadas aquí. '
            'Nada de lo que ocurra en esta pestaña altera las demás vistas del SIPM.</div>',
            unsafe_allow_html=True
        )

        base_kpi = scenario_kpis(base_visible)
        sc_kpi = scenario_kpis(scenario_visible)

        # Auditoría matemática y trazabilidad
        valid_math, math_errors = validate_scenario_math(scenario_df)
        base_ok, base_errors = baseline_invariance_check(df)
        audit = st.session_state.get("sipm_scenario_audit", {})
        st.markdown("#### Auditoría del escenario")
        a1,a2,a3 = st.columns(3)
        a1.metric("Base de cálculo", audit.get("base_calculo", "Base SIPM original"))
        a2.metric("Registros modificados", audit.get("registros", 0))
        a3.metric("Control matemático", "✓ SUPERADO" if (valid_math and base_ok) else "✕ ERROR")
        st.markdown(f"**Universo:** {audit.get('universo','Sin modificaciones')}")
        if audit.get("supuestos"):
            st.markdown("**Supuestos ingresados:** " + " · ".join(audit["supuestos"]))
        if audit.get("ajustes_modelo"):
            st.markdown("**Ajustes/derivaciones del motor:** " + " · ".join(audit["ajustes_modelo"]))
        if not valid_math or not base_ok:
            st.error("🔴 ESCENARIO INVÁLIDO. " + " | ".join(math_errors + base_errors))
            st.stop()
        else:
            st.success("✓ Identidades verificadas: participaciones = 100%; captura = demanda × % Catamarca; gasto fuera = demanda − captura; Base SIPM invariante; sin negativos ni valores no finitos.")

        # -----------------------------
        # 5.1 Resumen ejecutivo
        # -----------------------------
        st.markdown("#### 5.1 Resumen ejecutivo")
        summary_rows = [
            ["Demanda mapeada (US$ M)", base_kpi["demanda"]/1e6, sc_kpi["demanda"]/1e6, (sc_kpi["demanda"]-base_kpi["demanda"])/1e6],
            ["Captura local (US$ M)", base_kpi["captura_valor"]/1e6, sc_kpi["captura_valor"]/1e6, (sc_kpi["captura_valor"]-base_kpi["captura_valor"])/1e6],
            ["Captura local (%)", base_kpi["captura_pct"]*100, sc_kpi["captura_pct"]*100, (sc_kpi["captura_pct"]-base_kpi["captura_pct"])*100],
            ["Gasto fuera de Catamarca (US$ M)", base_kpi["gasto_fuera"]/1e6, sc_kpi["gasto_fuera"]/1e6, (sc_kpi["gasto_fuera"]-base_kpi["gasto_fuera"])/1e6],
            ["Empleo potencial", base_kpi["empleo"], sc_kpi["empleo"], sc_kpi["empleo"]-base_kpi["empleo"]],
        ]
        summary_df = pd.DataFrame(summary_rows, columns=["Indicador","Base SIPM","Escenario","Variación"])
        st.dataframe(
            summary_df.style.format({
                "Base SIPM":"{:,.1f}",
                "Escenario":"{:,.1f}",
                "Variación":"{:+,.1f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Δ demanda", f"US$ {(sc_kpi['demanda']-base_kpi['demanda'])/1e6:+,.1f} M")
        k2.metric("Δ captura local", f"{(sc_kpi['captura_pct']-base_kpi['captura_pct'])*100:+.1f} p.p.")
        k3.metric("Δ gasto fuera", f"US$ {(sc_kpi['gasto_fuera']-base_kpi['gasto_fuera'])/1e6:+,.1f} M", delta_color="inverse")
        k4.metric("Δ empleo potencial", f"{sc_kpi['empleo']-base_kpi['empleo']:+,.0f}")

        # Señales derivadas del motor interdependiente
        if "indice_presion_politica_demo" in scenario_visible.columns:
            base_modeled_visible = filter_like_sidebar(engine_prepare_scenario(df.copy(), df, []))
            bp = float(base_modeled_visible["indice_presion_politica_demo"].mean()) if not base_modeled_visible.empty else 0.0
            sp = float(scenario_visible["indice_presion_politica_demo"].mean()) if not scenario_visible.empty else 0.0
            bf = float(base_modeled_visible["indice_factibilidad_demo"].mean()) if not base_modeled_visible.empty else 0.0
            sf = float(scenario_visible["indice_factibilidad_demo"].mean()) if not scenario_visible.empty else 0.0
            d1,d2 = st.columns(2)
            d1.metric("Presión de política · promedio", f"{sp:.1f}/100", delta=f"{sp-bp:+.1f}")
            d2.metric("Factibilidad productiva · promedio", f"{sf:.1f}/100", delta=f"{sf-bf:+.1f}")
            st.caption("Índices DEMO calibrables: integran demanda, brecha no capturada, capacidad, complejidad, criticidad, importaciones y presión laboral. No son estimaciones causales reales hasta calibrar coeficientes con evidencia.")

        # Helper local para comparaciones agregadas.
        def _aggregate_compare(base_frame, scenario_frame, group_col):
            def _agg(frame):
                if frame.empty:
                    return pd.DataFrame(columns=[group_col,"demanda","captura_local","gasto_fuera","empleo"])
                return (
                    frame.groupby(group_col, dropna=False)
                    .agg(
                        demanda=("demanda_anual_usd_demo","sum"),
                        captura_local=("captura_local_usd_demo","sum"),
                        gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum"),
                        empleo=("empleo_local_potencial_demo","sum"),
                    )
                    .reset_index()
                )
            b = _agg(base_frame).rename(columns={
                "demanda":"demanda_base","captura_local":"captura_base",
                "gasto_fuera":"fuera_base","empleo":"empleo_base"
            })
            s = _agg(scenario_frame).rename(columns={
                "demanda":"demanda_esc","captura_local":"captura_esc",
                "gasto_fuera":"fuera_esc","empleo":"empleo_esc"
            })
            c = b.merge(s, on=group_col, how="outer").fillna(0)
            for stem in ["demanda","captura","fuera","empleo"]:
                c[f"delta_{stem}"] = c[f"{stem}_esc"] - c[f"{stem}_base"]
            c["captura_pct_base"] = c.apply(lambda x: x["captura_base"]/x["demanda_base"]*100 if x["demanda_base"] else 0, axis=1)
            c["captura_pct_esc"] = c.apply(lambda x: x["captura_esc"]/x["demanda_esc"]*100 if x["demanda_esc"] else 0, axis=1)
            c["delta_captura_pp"] = c["captura_pct_esc"] - c["captura_pct_base"]
            return c

        def _comparison_chart(comp, group_col, base_col, esc_col, title, value_label):
            plot = comp[[group_col, base_col, esc_col]].copy()
            plot = plot.rename(columns={base_col:"Base SIPM", esc_col:"Escenario"})
            long = plot.melt(id_vars=group_col, var_name="Situación", value_name="Valor")
            fig = px.bar(
                long, x="Valor", y=group_col, color="Situación",
                barmode="group", orientation="h",
                color_discrete_map={"Base SIPM":"#AEBCC4","Escenario":"#2A6F8E"},
                labels={"Valor":value_label, group_col:""},
                title=title
            )
            fig.update_layout(height=max(400, 46*len(comp)), margin=dict(t=50,l=0,r=20,b=10))
            st.plotly_chart(fig, use_container_width=True)

        # -----------------------------
        # 5.2 Aguas arriba
        # -----------------------------
        st.markdown("#### 5.2 Aguas arriba · estructura productiva")
        b_up = base_visible[base_visible["tipo_eslabonamiento"]=="Aguas arriba"].copy()
        s_up = scenario_visible[scenario_visible["tipo_eslabonamiento"]=="Aguas arriba"].copy()
        up_cmp = _aggregate_compare(b_up, s_up, "macrosector").sort_values("demanda_esc", ascending=False)

        if not up_cmp.empty:
            _comparison_chart(
                up_cmp, "macrosector", "demanda_base", "demanda_esc",
                "Demanda por sector · Aguas arriba", "Demanda anual demo USD"
            )
            up_table = up_cmp[[
                "macrosector","demanda_base","demanda_esc","delta_demanda",
                "captura_pct_base","captura_pct_esc","delta_captura_pp",
                "fuera_base","fuera_esc","delta_fuera",
                "empleo_base","empleo_esc","delta_empleo"
            ]].rename(columns={
                "macrosector":"Sector",
                "demanda_base":"Demanda base","demanda_esc":"Demanda escenario","delta_demanda":"Δ demanda",
                "captura_pct_base":"Captura base %","captura_pct_esc":"Captura escenario %","delta_captura_pp":"Δ captura p.p.",
                "fuera_base":"Gasto fuera base","fuera_esc":"Gasto fuera escenario","delta_fuera":"Δ gasto fuera",
                "empleo_base":"Empleo base","empleo_esc":"Empleo escenario","delta_empleo":"Δ empleo"
            })
            st.dataframe(up_table, use_container_width=True, hide_index=True)

            pressure_up = up_cmp.sort_values(["delta_fuera","fuera_esc"], ascending=False).head(5)
            if not pressure_up.empty:
                st.markdown("**Sectores aguas arriba que más cambian la presión de política productiva**")
                for _, rr in pressure_up.iterrows():
                    st.markdown(
                        f"- **{rr['macrosector']}** · Δ demanda US$ {rr['delta_demanda']/1e6:+,.1f} M · "
                        f"Δ captura {rr['delta_captura_pp']:+.1f} p.p. · "
                        f"Δ gasto fuera US$ {rr['delta_fuera']/1e6:+,.1f} M · "
                        f"Δ empleo {rr['delta_empleo']:+,.0f}"
                    )
        else:
            st.caption("No hay registros de Aguas arriba bajo los filtros seleccionados.")

        # -----------------------------
        # 5.3 Aguas abajo
        # -----------------------------
        st.markdown("#### 5.3 Aguas abajo · industrialización y agregación de valor")
        b_down = base_visible[base_visible["tipo_eslabonamiento"]=="Aguas abajo"].copy()
        s_down = scenario_visible[scenario_visible["tipo_eslabonamiento"]=="Aguas abajo"].copy()

        down_group = "cadena_valor" if "cadena_valor" in base_visible.columns else "macrosector"
        down_cmp = _aggregate_compare(b_down, s_down, down_group).sort_values("demanda_esc", ascending=False)

        if not down_cmp.empty:
            _comparison_chart(
                down_cmp, down_group, "demanda_base", "demanda_esc",
                "Demanda por eslabón · Aguas abajo", "Demanda anual demo USD"
            )
            down_table = down_cmp[[
                down_group,"demanda_base","demanda_esc","delta_demanda",
                "captura_pct_base","captura_pct_esc","delta_captura_pp",
                "fuera_base","fuera_esc","delta_fuera",
                "empleo_base","empleo_esc","delta_empleo"
            ]].rename(columns={
                down_group:"Cadena / eslabón",
                "demanda_base":"Demanda base","demanda_esc":"Demanda escenario","delta_demanda":"Δ demanda",
                "captura_pct_base":"Captura base %","captura_pct_esc":"Captura escenario %","delta_captura_pp":"Δ captura p.p.",
                "fuera_base":"Gasto fuera base","fuera_esc":"Gasto fuera escenario","delta_fuera":"Δ gasto fuera",
                "empleo_base":"Empleo base","empleo_esc":"Empleo escenario","delta_empleo":"Δ empleo"
            })
            st.dataframe(down_table, use_container_width=True, hide_index=True)

            st.markdown(
                '<div class="sipm-note"><b>Lectura de política:</b> un aumento aguas abajo no implica automáticamente instalar una industria. '
                'Debe evaluarse escala mínima eficiente, energía, logística, tecnología, CAPEX, mercado regional y posibilidad de atraer inversión '
                'o construir capacidades locales.</div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("No hay registros de Aguas abajo bajo los filtros seleccionados.")

        # -----------------------------
        # 5.4 Oportunidades
        # -----------------------------
        st.markdown("#### 5.4 Oportunidades · qué cambia en la priorización")
        priority_order = ["Alta","Media","Consolidar"]
        b_pr = base_visible["prioridad_demo"].value_counts().reindex(priority_order, fill_value=0)
        s_pr = scenario_visible["prioridad_demo"].value_counts().reindex(priority_order, fill_value=0)
        pr_df = pd.DataFrame({
            "Prioridad": priority_order,
            "Base SIPM": [int(b_pr[x]) for x in priority_order],
            "Escenario": [int(s_pr[x]) for x in priority_order],
        })
        pr_df["Variación"] = pr_df["Escenario"] - pr_df["Base SIPM"]
        st.dataframe(pr_df, use_container_width=True, hide_index=True)

        if "id" in base_visible.columns and "id" in scenario_visible.columns:
            b_id = base_visible.set_index("id")
            s_id = scenario_visible.set_index("id")
            common = b_id.index.intersection(s_id.index)
            opp = pd.DataFrame(index=common)
            opp["Mineral"] = s_id.loc[common,"mineral"]
            opp["Sector"] = s_id.loc[common,"macrosector"]
            opp["Actividad"] = s_id.loc[common,"requerimiento_o_producto"]
            opp["Puntaje base"] = b_id.loc[common,"puntaje_oportunidad_demo"]
            opp["Puntaje escenario"] = s_id.loc[common,"puntaje_oportunidad_demo"]
            opp["Δ puntaje"] = opp["Puntaje escenario"] - opp["Puntaje base"]
            opp["Prioridad base"] = b_id.loc[common,"prioridad_demo"]
            opp["Prioridad escenario"] = s_id.loc[common,"prioridad_demo"]
            opp["Δ gasto fuera USD"] = (
                s_id.loc[common,"gasto_fuera_catamarca_usd_demo"]
                - b_id.loc[common,"gasto_fuera_catamarca_usd_demo"]
            )
            opp["Δ empleo"] = (
                s_id.loc[common,"empleo_local_potencial_demo"]
                - b_id.loc[common,"empleo_local_potencial_demo"]
            )
            opp = opp.sort_values(["Δ puntaje","Δ gasto fuera USD"], ascending=False)
            st.markdown("**Actividades cuya oportunidad cambia más respecto de la base**")
            st.dataframe(opp.head(15), use_container_width=True)

        # -----------------------------
        # 5.5 Territorio
        # -----------------------------
        st.markdown("#### 5.5 Territorio · dónde se concentra el impacto")
        terr_cmp = _aggregate_compare(base_visible, scenario_visible, "territorio_potencial").sort_values("demanda_esc", ascending=False)
        if not terr_cmp.empty:
            _comparison_chart(
                terr_cmp, "territorio_potencial", "demanda_base", "demanda_esc",
                "Demanda territorial · Base vs. Escenario", "Demanda anual demo USD"
            )
            terr_table = terr_cmp[[
                "territorio_potencial","demanda_base","demanda_esc","delta_demanda",
                "captura_pct_base","captura_pct_esc","delta_captura_pp",
                "fuera_base","fuera_esc","delta_fuera",
                "empleo_base","empleo_esc","delta_empleo"
            ]].rename(columns={
                "territorio_potencial":"Territorio",
                "demanda_base":"Demanda base","demanda_esc":"Demanda escenario","delta_demanda":"Δ demanda",
                "captura_pct_base":"Captura base %","captura_pct_esc":"Captura escenario %","delta_captura_pp":"Δ captura p.p.",
                "fuera_base":"Gasto fuera base","fuera_esc":"Gasto fuera escenario","delta_fuera":"Δ gasto fuera",
                "empleo_base":"Empleo base","empleo_esc":"Empleo escenario","delta_empleo":"Δ empleo"
            })
            st.dataframe(terr_table, use_container_width=True, hide_index=True)

        # -----------------------------
        # 5.6 Políticas públicas
        # -----------------------------
        st.markdown("#### 5.6 Política pública · qué debería cambiar frente al escenario")
        st.markdown(
            '<div class="chart-explain"><b>Esta es la salida central del SIPM:</b> no sólo identificar que un indicador cambió, '
            'sino traducir esa diferencia en una agenda de intervención. Las siguientes reglas son demostrativas y deben calibrarse '
            'con evidencia real, responsables institucionales, presupuesto y horizonte temporal.</div>',
            unsafe_allow_html=True
        )

        policy_rows = []

        # Compras anticipadas / proveedores desde Aguas arriba.
        if not up_cmp.empty:
            top_demand = up_cmp.sort_values("delta_demanda", ascending=False).iloc[0]
            top_out = up_cmp.sort_values("delta_fuera", ascending=False).iloc[0]
            if top_demand["delta_demanda"] > 0:
                policy_rows.append({
                    "Prioridad":"Alta",
                    "Eje":"Compras anticipadas",
                    "Señal del escenario":f"{top_demand['macrosector']} aumenta su demanda en US$ {top_demand['delta_demanda']/1e6:,.1f} M.",
                    "Acción sugerida":"Solicitar y consolidar planes de compra a 12–36 meses por categoría, publicar cronogramas agregados y preparar oferta local antes de que la demanda se materialice.",
                    "Actores":"Minería + Producción + empresas + cámaras"
                })
            if top_out["delta_fuera"] > 0 or top_out["fuera_esc"] > 0:
                policy_rows.append({
                    "Prioridad":"Alta" if top_out["delta_fuera"] > 0 else "Media",
                    "Eje":"Desarrollo de proveedores",
                    "Señal del escenario":f"{top_out['macrosector']} presenta US$ {top_out['fuera_esc']/1e6:,.1f} M de gasto fuera y una variación de US$ {top_out['delta_fuera']/1e6:+,.1f} M.",
                    "Acción sugerida":"Mapear proveedores, homologaciones, capacidad instalada, financiamiento, asociatividad y barreras de contratación; fijar metas verificables de desarrollo local.",
                    "Actores":"Producción + Minería + cámaras + banca/agencias"
                })

        # Aguas abajo / inversiones.
        if not down_cmp.empty:
            top_down = down_cmp.sort_values("delta_demanda", ascending=False).iloc[0]
            if top_down["delta_demanda"] > 0 or top_down["demanda_esc"] > 0:
                policy_rows.append({
                    "Prioridad":"Estratégica",
                    "Eje":"Industrialización / atracción de inversiones",
                    "Señal del escenario":f"{top_down[down_group]} alcanza US$ {top_down['demanda_esc']/1e6:,.1f} M en el escenario y varía US$ {top_down['delta_demanda']/1e6:+,.1f} M.",
                    "Acción sugerida":"Seleccionar oportunidades para prefactibilidad: escala, energía, logística, tecnología, CAPEX, mercado regional, socios tecnológicos y modalidad de inversión.",
                    "Actores":"Producción + Minería + Inversiones + UNCA + privados"
                })

        # Desarrollo territorial.
        if not terr_cmp.empty:
            top_terr = terr_cmp.assign(
                impacto=terr_cmp["delta_demanda"].abs()/1e6 + terr_cmp["delta_empleo"].abs()
            ).sort_values("impacto", ascending=False).iloc[0]
            if top_terr["impacto"] > 0:
                policy_rows.append({
                    "Prioridad":"Alta",
                    "Eje":"Desarrollo territorial",
                    "Señal del escenario":f"{top_terr['territorio_potencial']} concentra Δ demanda US$ {top_terr['delta_demanda']/1e6:+,.1f} M y Δ empleo {top_terr['delta_empleo']:+,.0f}.",
                    "Acción sugerida":"Revisar infraestructura, logística, suelo industrial, servicios, vivienda, formación local y capacidad institucional del territorio antes del crecimiento.",
                    "Actores":"Provincia + municipios + organismos sectoriales"
                })

        # Innovación por complejidad/capacidad.
        changed_scope = scenario_visible.copy()
        if not changed_scope.empty:
            low_cap = changed_scope[
                changed_scope["capacidad_local_demo"].astype(str).str.lower().isin(["baja","incipiente"])
            ]
            high_complex = changed_scope[
                changed_scope["complejidad_tecnica"].astype(str).str.lower().isin(["alta","muy alta"])
            ]
            if len(low_cap) + len(high_complex) > 0:
                policy_rows.append({
                    "Prioridad":"Media / Alta",
                    "Eje":"Innovación y capacidades tecnológicas",
                    "Señal del escenario":f"Se detectan {len(low_cap)} registros con capacidad local baja/incipiente y {len(high_complex)} con complejidad alta/muy alta.",
                    "Acción sugerida":"Convertir brechas recurrentes en proyectos de I+D, laboratorios, asistencia tecnológica, transferencia, certificaciones y desafíos universidad–empresa.",
                    "Actores":"UNCA + INTI + sistema científico + empresas"
                })

        if not policy_rows:
            policy_rows.append({
                "Prioridad":"Seguimiento",
                "Eje":"Monitoreo",
                "Señal del escenario":"El escenario no genera variaciones materiales respecto de la Base SIPM bajo los filtros seleccionados.",
                "Acción sugerida":"Mantener monitoreo periódico y actualizar supuestos cuando aparezcan nuevos proyectos, compras, inversiones o requerimientos.",
                "Actores":"Unidad SIPM"
            })

        policy_df = pd.DataFrame(policy_rows)
        st.dataframe(policy_df, use_container_width=True, hide_index=True)

        # -----------------------------
        # 5.7 Capital humano
        # -----------------------------
        st.markdown("#### 5.7 Capital humano · Base vs. Escenario")
        base_profiles = estimate_profiles(base_visible)
        sc_profiles = estimate_profiles(scenario_visible)

        if not base_profiles.empty or not sc_profiles.empty:
            bp = base_profiles.rename(columns={"personas_demo":"Base SIPM"}) if not base_profiles.empty else pd.DataFrame(columns=["perfil","Base SIPM"])
            sp = sc_profiles.rename(columns={"personas_demo":"Escenario"}) if not sc_profiles.empty else pd.DataFrame(columns=["perfil","Escenario"])
            prof_cmp = bp.merge(sp, on="perfil", how="outer").fillna(0)
            prof_cmp["Variación"] = prof_cmp["Escenario"] - prof_cmp["Base SIPM"]
            prof_cmp = prof_cmp.sort_values(["Variación","Escenario"], ascending=False)

            top_profiles = prof_cmp.head(15).copy()
            prof_long = top_profiles.melt(id_vars="perfil", value_vars=["Base SIPM","Escenario"], var_name="Situación", value_name="Personas")
            fig_prof = px.bar(
                prof_long, x="Personas", y="perfil", color="Situación",
                barmode="group", orientation="h",
                color_discrete_map={"Base SIPM":"#AEBCC4","Escenario":"#2A6F8E"},
                labels={"perfil":"","Personas":"Personas equivalentes · demo"},
                title="Perfiles de capital humano · comparación"
            )
            fig_prof.update_layout(height=max(480, 42*len(top_profiles)), margin=dict(t=50,l=0,r=20,b=10))
            st.plotly_chart(fig_prof, use_container_width=True)

            edu_rows = []
            for _, pr in prof_cmp.head(12).iterrows():
                horizon, action, actors = education_action(pr["perfil"])
                edu_rows.append({
                    "Perfil":pr["perfil"],
                    "Base SIPM":round(pr["Base SIPM"]),
                    "Escenario":round(pr["Escenario"]),
                    "Variación":round(pr["Variación"]),
                    "Horizonte":horizon,
                    "Respuesta educativa sugerida":action,
                    "Actores":actors
                })
            st.dataframe(pd.DataFrame(edu_rows), use_container_width=True, hide_index=True)

            positive_profiles = prof_cmp[prof_cmp["Variación"] > 0]
            if not positive_profiles.empty:
                lead = positive_profiles.iloc[0]
                horizon, action, actors = education_action(lead["perfil"])
                st.markdown(
                    f'<div class="reco"><strong>Señal principal de talento:</strong> '
                    f'{lead["perfil"]} aumenta en aproximadamente <b>{lead["Variación"]:+,.0f}</b> personas equivalentes frente a la base.<br>'
                    f'<b>Respuesta:</b> {action}<br><b>Actores:</b> {actors}</div>',
                    unsafe_allow_html=True
                )

        # -----------------------------
        # 5.8 Síntesis de decisión
        # -----------------------------
        st.markdown("#### 5.8 Síntesis · de la variación a la acción")
        st.markdown(
            f"""
            <div class="drill">
            <b>Lectura integral del escenario:</b><br>
            La demanda cambia <b>US$ {(sc_kpi['demanda']-base_kpi['demanda'])/1e6:+,.1f} M</b>,
            la captura local cambia <b>{(sc_kpi['captura_pct']-base_kpi['captura_pct'])*100:+.1f} p.p.</b>,
            el gasto fuera de Catamarca cambia <b>US$ {(sc_kpi['gasto_fuera']-base_kpi['gasto_fuera'])/1e6:+,.1f} M</b>
            y el empleo potencial cambia <b>{sc_kpi['empleo']-base_kpi['empleo']:+,.0f}</b> personas equivalentes.
            <br><br>
            La decisión pública no surge de un único indicador: debe combinar <b>Aguas arriba + Aguas abajo + oportunidades +
            territorio + capacidades empresariales + capital humano</b> y traducirse en prioridades, responsables,
            instrumentos y horizonte temporal.
            </div>
            """,
            unsafe_allow_html=True
        )

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
with tabs[8]:
    st.subheader("De la matriz a la política pública")
    st.markdown(
        '<div class="chart-explain"><b>Qué muestra:</b> transforma las brechas productivas de la matriz en decisiones accionables. '
        'El objetivo es responder tres preguntas: <b>qué debería hacer el Estado, qué perfiles de capital humano deberían fortalecerse '
        'y cómo debería reaccionar el sistema educativo.</b> Las cantidades son escenarios demostrativos agregados, no vacantes reales.</div>',
        unsafe_allow_html=True
    )

    st.markdown("### 1. Agenda de política pública")
    pc1,pc2=st.columns(2)
    for i,(title,desc) in enumerate(PUBLIC_POLICY_PILLARS):
        target_col=pc1 if i%2==0 else pc2
        with target_col:
            st.markdown(f'<div class="reco"><strong>{title}</strong><br>{desc}</div>',unsafe_allow_html=True)

    st.markdown("### 2. ¿Qué capital humano podría demandar este ecosistema?")
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

        st.markdown("### 3. ¿Qué debería hacer Universidad y Educación?")
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

        st.markdown("### 4. La ventaja de Catamarca: no parte de cero")
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

        st.markdown("### 5. Antecedentes que muestran que esto es posible")
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
with tabs[9]:
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