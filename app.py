import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
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
    if linkage == "Hacia adelante" or "muy alta" in complexity:
        acts.append(("3. Evaluar inversión estratégica", "No impulsar producción local por decreto: realizar prefactibilidad técnica, escala mínima, energía, logística, tecnología y demanda regional."))
    else:
        acts.append(("3. Fijar una meta verificable", f"Construir un plan gradual desde {current:.0f}% hasta {target}% y monitorearlo por año, empresa y tipo de compra."))
    return acts

def relevant_benchmarks(row):
    current=float(row["participacion_catamarca_pct_demo"])
    linkage=row["tipo_eslabonamiento"]
    if linkage=="Hacia adelante":
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
    linkages = st.multiselect("Eslabonamiento", sorted(df["tipo_eslabonamiento"].unique()), default=sorted(df["tipo_eslabonamiento"].unique()))
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
    "🏠 Inicio","🌐 Ecosistema","⬅️ Hacia atrás","➡️ Hacia adelante",
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
La necesidad surge porque producir más minerales no garantiza, por sí solo, mayor desarrollo provincial. Para convertir la expansión minera en una política de desarrollo productivo, Catamarca necesita identificar sus <b>eslabonamientos hacia atrás y hacia adelante</b>, medir el contenido local, anticipar demanda y priorizar las oportunidades con mayor impacto económico y territorial.
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
# HACIA ATRAS
# ------------------------------------------------
with tabs[2]:
    st.subheader("Eslabonamientos hacia atrás")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> cómo la actividad minera genera demanda sobre construcción, energía, logística, metalmecánica, tecnología, ambiente, servicios y otros sectores. El ancho de cada flujo representa el peso económico de esa relación. Esta vista permite entender que el impacto minero comienza mucho antes de extraer el mineral.</div>', unsafe_allow_html=True)

    back=f[f["tipo_eslabonamiento"]=="Hacia atrás"].copy()
    if back.empty:
        st.info("Activá Hacia atrás en el filtro lateral.")
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
# HACIA ADELANTE
# ------------------------------------------------
with tabs[3]:
    st.subheader("Eslabonamientos hacia adelante")
    st.markdown('<div class="chart-explain"><b>Qué muestra:</b> las actividades que pueden desarrollarse después de la extracción: procesamiento, refinación, manufactura, materiales avanzados, energía o reciclaje. No implica que todas sean viables, sino que permite identificar cuáles merecen estudios de factibilidad y políticas de largo plazo.</div>', unsafe_allow_html=True)

    fw=f[f["tipo_eslabonamiento"]=="Hacia adelante"].copy()
    if fw.empty:
        st.info("Activá Hacia adelante en el filtro lateral.")
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
