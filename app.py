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

m1,m2,m3,m4,m5,m6=st.columns(6)
m1.metric("Actividades",len(f))
m2.metric("Mercado mapeado",f"US$ {total/1e6:,.0f} M")
m3.metric("Captura local",f"{local_pct:.0%}")
m4.metric("Gasto fuera",f"US$ {outside/1e6:,.0f} M")
m5.metric("Empleo potencial",f"{jobs:,}")
m6.metric("Sectores",f["macrosector"].nunique())

st.caption("⚠️ Todos los indicadores cuantitativos son demostrativos. El sistema final deberá alimentarse con información validada.")

tabs=st.tabs([
    "🏠 Inicio","🌐 Ecosistema","⬅️ Hacia atrás","➡️ Hacia adelante",
    "🎯 Oportunidades","📍 Territorio","🧪 Simulador","📋 Matriz"
])

# ------------------------------------------------
# INICIO
# ------------------------------------------------
with tabs[0]:
    st.subheader("Una lectura simple del impacto minero")
    a,b,c=st.columns(3)
    with a:
        st.markdown('<div class="pillar"><b>⬅️ 1. Lo que la minería necesita</b><br><br>Bienes, servicios, tecnología, energía, construcción, logística, mantenimiento, ambiente, conocimiento y trabajadores.</div>',unsafe_allow_html=True)
    with b:
        st.markdown('<div class="pillar"><b>⛏️ 2. La actividad minera</b><br><br>El proyecto minero funciona como nodo central que moviliza demanda sobre decenas de sectores económicos.</div>',unsafe_allow_html=True)
    with c:
        st.markdown('<div class="pillar"><b>➡️ 3. Lo que puede generar después</b><br><br>Procesamiento, metalurgia, materiales avanzados, manufacturas, energía, reciclaje y nuevas industrias.</div>',unsafe_allow_html=True)

    st.markdown("### ¿Dónde aparece hoy el mayor espacio de política productiva?")
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
    st.caption("Todo lo que debe existir antes y durante la operación para que la minería funcione.")
    back=f[f["tipo_eslabonamiento"]=="Hacia atrás"].copy()
    if back.empty:
        st.info("Activá Hacia atrás en el filtro lateral.")
    else:
        agg=back.groupby("macrosector",as_index=False).agg(
            demanda=("demanda_anual_usd_demo","sum"),
            local=("participacion_catamarca_pct_demo","mean"),
            gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum")
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
                customdata=agg[["local","gasto_fuera"]].values,
                hovertemplate="%{target.label}<br>Demanda demo: US$ %{value:,.0f}<br>Captura local: %{customdata[0]:.1f}%<br>Gasto fuera: US$ %{customdata[1]:,.0f}<extra></extra>"
            )
        ))
        fig.update_layout(height=670,margin=dict(t=10,l=10,r=10,b=10),font=dict(size=12))
        st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------
# HACIA ADELANTE
# ------------------------------------------------
with tabs[3]:
    st.subheader("Eslabonamientos hacia adelante")
    st.caption("No muestran sólo qué compra la mina, sino qué nuevas actividades podrían surgir a partir del mineral.")
    fw=f[f["tipo_eslabonamiento"]=="Hacia adelante"].copy()
    if fw.empty:
        st.info("Activá Hacia adelante en el filtro lateral.")
    else:
        mineral=st.selectbox("Elegí una cadena",sorted(fw["mineral"].unique()),key="forward")
        chain=fw[fw["mineral"]==mineral].sort_values("id")
        for _,r in chain.iterrows():
            title=f"{r['actividad']} → {r['requerimiento_o_producto']}"
            with st.expander(title,expanded=False):
                c1,c2,c3=st.columns([1.6,1,1])
                c1.markdown(f"**Acción sugerida**  \n{r['accion_sugerida']}")
                c2.metric("Captura local demo",f"{r['participacion_catamarca_pct_demo']:.0f}%")
                c3.metric("Empleo potencial",int(r["empleo_local_potencial_demo"]))
                st.markdown(
                    f"**Complejidad técnica:** {r['complejidad_tecnica']}  \n"
                    f"**Capacidad local actual:** {r['capacidad_local_demo']}  \n"
                    f"**Barrera principal:** {r['barrera_principal']}  \n"
                    f"**Beneficio provincial:** {r['beneficio_provincial']}  \n"
                    f"**Territorio potencial:** {r['territorio_potencial']}  \n"
                    f"**Cadena de valor:** {r['cadena_valor']}"
                )

# ------------------------------------------------
# OPORTUNIDADES
# ------------------------------------------------
with tabs[4]:
    st.subheader("¿Dónde conviene mirar primero?")
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
    st.caption("Elegí una actividad y probá un escenario de mayor participación local.")

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
    c3.metric("Gasto retenido adicional",f"US$ {incremental/1e6:,.2f} M")
    c4.metric("Empleo asociado demo",f"+{extra_jobs:,.0f}")

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
# MATRIZ
# ------------------------------------------------
with tabs[7]:
    st.subheader("Matriz integral")
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
