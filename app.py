
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="SIPM Catamarca — Demo institucional", page_icon="⛏️", layout="wide")

DATA = Path(__file__).with_name("matriz_sipm_v2_demo.csv")

@st.cache_data
def load_data():
    df = pd.read_csv(DATA)
    df["captura_local_usd_demo"] = df["demanda_anual_usd_demo"] * df["participacion_catamarca_pct_demo"] / 100
    df["gasto_fuera_catamarca_usd_demo"] = df["demanda_anual_usd_demo"] - df["captura_local_usd_demo"]
    df["puntaje_oportunidad_demo"] = (
        (1-df["participacion_catamarca_pct_demo"]/100)*45
        + (df["gasto_fuera_catamarca_usd_demo"].clip(lower=10).apply(lambda x:min(1, __import__("math").log10(x)/8)))*35
        + (df["empleo_local_potencial_demo"]/250).clip(upper=1)*20
    ).round()
    df["prioridad_demo"] = pd.cut(
        df["puntaje_oportunidad_demo"],
        bins=[-1,49,69,101],
        labels=["Consolidar / Baja","Media","Alta"]
    ).astype(str)
    return df

df = load_data()

st.markdown("""
<style>
.block-container {padding-top: 1.25rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.22); padding:12px 14px; border-radius:12px;}
[data-testid="stMetricValue"] {font-size:1.6rem;}
.hero {padding:18px 20px; border-radius:14px; background:rgba(80,120,160,.08); border:1px solid rgba(100,120,140,.18);}
.flowbox {padding:14px; border-radius:12px; border:1px solid rgba(128,128,128,.22); min-height:115px;}
.small {font-size:.86rem; opacity:.75;}
</style>
""", unsafe_allow_html=True)

st.title("SIPM | Sistema Provincial de Inteligencia Productiva para la Minería")
st.caption("Demo institucional — Provincia de Catamarca")
st.warning("**Demo conceptual:** montos, participaciones, empleos y puntajes son simulados. La app demuestra qué podría hacer el SIPM con datos relevados y validados.")

with st.sidebar:
    st.header("Explorar")
    minerals = st.multiselect("Mineral", sorted(df["mineral"].unique()), default=sorted(df["mineral"].unique()))
    linkages = st.multiselect("Eslabonamiento", sorted(df["tipo_eslabonamiento"].unique()), default=sorted(df["tipo_eslabonamiento"].unique()))
    stages = st.multiselect("Etapa", sorted(df["etapa_proyecto"].unique()), default=sorted(df["etapa_proyecto"].unique()))
    territories = st.multiselect("Territorio", sorted(df["territorio_potencial"].unique()), default=sorted(df["territorio_potencial"].unique()))
    st.divider()
    st.caption("La navegación está pensada para personas no economistas: cada vista responde una pregunta concreta.")

f = df[
    df["mineral"].isin(minerals) &
    df["tipo_eslabonamiento"].isin(linkages) &
    df["etapa_proyecto"].isin(stages) &
    df["territorio_potencial"].isin(territories)
].copy()

if f.empty:
    st.info("No hay registros para esta combinación de filtros.")
    st.stop()

total = f["demanda_anual_usd_demo"].sum()
local = f["captura_local_usd_demo"].sum()
outside = f["gasto_fuera_catamarca_usd_demo"].sum()
jobs = int(f["empleo_local_potencial_demo"].sum())
local_pct = local/total if total else 0

st.markdown('<div class="hero"><b>Pregunta central:</b> ¿cómo convertir el crecimiento minero en más empresas, empleo, conocimiento y valor agregado dentro de Catamarca?</div>', unsafe_allow_html=True)
st.write("")

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("Actividades mapeadas", f"{len(f)}")
m2.metric("Demanda / mercado demo", f"US$ {total/1e6:,.0f} M")
m3.metric("Captura Catamarca", f"{local_pct:.0%}")
m4.metric("Gasto fuera", f"US$ {outside/1e6:,.0f} M")
m5.metric("Empleo potencial", f"{jobs:,}")
m6.metric("Sectores", f"{f['macrosector'].nunique()}")

tabs = st.tabs([
    "🏠 Inicio",
    "🌐 Ecosistema",
    "⬅️ Hacia atrás",
    "➡️ Hacia adelante",
    "🎯 Oportunidades",
    "📍 Territorio",
    "🧪 Simulador",
    "📋 Matriz"
])

with tabs[0]:
    st.subheader("La minería vista como ecosistema")
    a,b,c = st.columns(3)
    with a:
        st.markdown('<div class="flowbox"><b>⬅️ ¿Qué necesita la minería?</b><br><br>Construcción, energía, logística, química, mantenimiento, tecnología, ambiente, servicios y formación.</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="flowbox"><b>⛏️ Minería en Catamarca</b><br><br>El SIPM conecta cada proyecto y mineral con los sectores económicos que moviliza.</div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="flowbox"><b>➡️ ¿Qué puede generar después?</b><br><br>Procesamiento, manufactura, materiales avanzados, energía, metalurgia y economía circular.</div>', unsafe_allow_html=True)
    st.write("")
    st.info("La herramienta cambia la conversación: de “queremos más proveedores locales” a **qué capacidades concretas necesitamos desarrollar, dónde y con qué prioridad**.")

    top = f.groupby("macrosector",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum"),
        empleo=("empleo_local_potencial_demo","sum")
    ).sort_values("gasto_fuera",ascending=False).head(8)
    fig = px.bar(top, x="gasto_fuera", y="macrosector", orientation="h",
                 labels={"gasto_fuera":"Gasto fuera de Catamarca — demo USD","macrosector":""},
                 title="¿En qué sectores aparece mayor espacio para investigar oportunidades?")
    fig.update_layout(yaxis={"categoryorder":"total ascending"},height=430)
    st.plotly_chart(fig,use_container_width=True)

with tabs[1]:
    st.subheader("¿Qué sectores económicos moviliza la minería?")
    eco=f.groupby("macrosector",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        captura=("participacion_catamarca_pct_demo","mean"),
        empleo=("empleo_local_potencial_demo","sum")
    )
    fig=px.treemap(eco,path=["macrosector"],values="demanda",color="captura",
                   color_continuous_scale="Blues",
                   hover_data={"empleo":True,"captura":":.1f","demanda":":,.0f"})
    fig.update_layout(height=600,margin=dict(t=10,l=10,r=10,b=10),coloraxis_colorbar_title="% local demo")
    st.plotly_chart(fig,use_container_width=True)
    st.caption("Tamaño = magnitud económica demo. Tono = participación catamarqueña demo. El objetivo es visualizar el ecosistema, no sólo la mina.")

with tabs[2]:
    st.subheader("Eslabonamientos hacia atrás: lo que la minería necesita para funcionar")
    back=f[f["tipo_eslabonamiento"]=="Hacia atrás"].copy()
    if back.empty:
        st.info("Activá 'Hacia atrás' en los filtros.")
    else:
        agg=back.groupby("macrosector",as_index=False).agg(
            demanda=("demanda_anual_usd_demo","sum"),
            local=("participacion_catamarca_pct_demo","mean"),
            gasto_fuera=("gasto_fuera_catamarca_usd_demo","sum")
        ).sort_values("demanda",ascending=False)
        labels=["MINERÍA"]+agg["macrosector"].tolist()
        fig=go.Figure(go.Sankey(
            node=dict(label=labels,pad=16,thickness=20),
            link=dict(
                source=[0]*len(agg),
                target=list(range(1,len(agg)+1)),
                value=agg["demanda"],
                customdata=agg[["local","gasto_fuera"]].values,
                hovertemplate="%{target.label}<br>Demanda demo: US$ %{value:,.0f}<br>Participación local: %{customdata[0]:.1f}%<br>Gasto fuera: US$ %{customdata[1]:,.0f}<extra></extra>"
            )
        ))
        fig.update_layout(height=650,margin=dict(t=10,l=10,r=10,b=10))
        st.plotly_chart(fig,use_container_width=True)
        st.success("El ancho del flujo muestra la magnitud de la relación económica. Una participación local baja no implica que deba sustituirse: indica dónde conviene estudiar capacidades, certificaciones, escala e inversión.")

with tabs[3]:
    st.subheader("Eslabonamientos hacia adelante: qué actividades pueden aparecer después de la extracción")
    fw=f[f["tipo_eslabonamiento"]=="Hacia adelante"].copy()
    if fw.empty:
        st.info("Activá 'Hacia adelante' en los filtros.")
    else:
        mineral=st.selectbox("Elegí una cadena",sorted(fw["mineral"].unique()),key="forward_mineral")
        chain=fw[fw["mineral"]==mineral].copy()
        for _,r in chain.iterrows():
            with st.container(border=True):
                c1,c2,c3=st.columns([2.2,1,1])
                c1.markdown(f"**{r['actividad']} → {r['requerimiento_o_producto']}**  \n{r['accion_sugerida']}")
                c2.metric("Captura local demo",f"{r['participacion_catamarca_pct_demo']:.0f}%")
                c3.metric("Empleo potencial",f"{int(r['empleo_local_potencial_demo'])}")
                st.caption(f"Complejidad: {r['complejidad_tecnica']} · Barrera: {r['barrera_principal']} · Beneficio: {r['beneficio_provincial']}")
        st.info("Esta vista no afirma que cada eslabón sea económicamente viable. El SIPM sirve precisamente para decidir **cuáles merecen un estudio de factibilidad**.")

with tabs[4]:
    st.subheader("Mapa de oportunidades productivas")
    op=f.copy()
    fig=px.scatter(
        op,
        x="participacion_catamarca_pct_demo",
        y="gasto_fuera_catamarca_usd_demo",
        size="empleo_local_potencial_demo",
        color="mineral",
        symbol="tipo_eslabonamiento",
        hover_name="requerimiento_o_producto",
        hover_data=["macrosector","actividad","accion_sugerida","territorio_potencial","puntaje_oportunidad_demo"],
        labels={
            "participacion_catamarca_pct_demo":"Participación Catamarca (%) — demo",
            "gasto_fuera_catamarca_usd_demo":"Gasto fuera de Catamarca (USD demo)"
        }
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig,use_container_width=True)
    st.caption("Arriba a la izquierda aparecen, en términos conceptuales, los casos con mayor gasto externo y menor captura local.")

    top=op.sort_values(["puntaje_oportunidad_demo","gasto_fuera_catamarca_usd_demo"],ascending=False).head(12)
    st.dataframe(
        top[["mineral","macrosector","requerimiento_o_producto","participacion_catamarca_pct_demo",
             "gasto_fuera_catamarca_usd_demo","empleo_local_potencial_demo","prioridad_demo","accion_sugerida"]],
        use_container_width=True,hide_index=True,
        column_config={
            "participacion_catamarca_pct_demo":st.column_config.ProgressColumn("% local demo",min_value=0,max_value=100),
            "gasto_fuera_catamarca_usd_demo":st.column_config.NumberColumn("Gasto fuera demo",format="$ %.0f"),
            "empleo_local_potencial_demo":"Empleo potencial",
            "prioridad_demo":"Prioridad demo"
        }
    )

with tabs[5]:
    st.subheader("¿Dónde puede sentirse el impacto?")
    terr=f.groupby("territorio_potencial",as_index=False).agg(
        demanda=("demanda_anual_usd_demo","sum"),
        local=("captura_local_usd_demo","sum"),
        empleo=("empleo_local_potencial_demo","sum"),
        actividades=("id","count")
    )
    terr["captura_pct"]=terr["local"]/terr["demanda"]*100
    fig=px.bar(terr.sort_values("demanda"),x="demanda",y="territorio_potencial",orientation="h",
               color="captura_pct",
               hover_data=["empleo","actividades"],
               labels={"demanda":"Demanda demo USD","territorio_potencial":"","captura_pct":"% local"})
    fig.update_layout(height=500)
    st.plotly_chart(fig,use_container_width=True)
    place=st.selectbox("Explorá un territorio",sorted(f["territorio_potencial"].unique()))
    tp=f[f["territorio_potencial"]==place].sort_values("demanda_anual_usd_demo",ascending=False)
    st.markdown(f"**{place}** concentra {len(tp)} actividades en el filtro actual.")
    st.dataframe(tp[["mineral","macrosector","actividad","requerimiento_o_producto","beneficio_provincial"]].head(15),
                 use_container_width=True,hide_index=True)

with tabs[6]:
    st.subheader("Simulador: ¿qué pasa si Catamarca captura una mayor proporción de una actividad?")
    sim=f.sort_values("gasto_fuera_catamarca_usd_demo",ascending=False).copy()
    label=st.selectbox(
        "Elegí una actividad",
        sim.index,
        format_func=lambda i:f"{sim.loc[i,'mineral']} · {sim.loc[i,'macrosector']} · {sim.loc[i,'requerimiento_o_producto']}"
    )
    r=sim.loc[label]
    current=float(r["participacion_catamarca_pct_demo"])
    target=st.slider("Participación local objetivo — escenario",min_value=int(current),max_value=100,value=min(100,int(current)+20),step=1)
    incremental=r["demanda_anual_usd_demo"]*(target-current)/100
    # Simple proportional employment scenario, explicitly demo
    extra_jobs=r["empleo_local_potencial_demo"]*((target-current)/100)

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Participación actual demo",f"{current:.0f}%")
    c2.metric("Escenario",f"{target}%")
    c3.metric("Gasto adicional retenido",f"US$ {incremental/1e6:,.2f} M")
    c4.metric("Empleo asociado demo",f"+{extra_jobs:,.0f}")
    st.markdown(f"**Acción sugerida:** {r['accion_sugerida']}")
    st.markdown(f"**Barrera principal:** {r['barrera_principal']}")
    st.warning("El simulador es ilustrativo. No estima causalidad ni garantiza empleo o inversión: permite visualizar el tamaño económico de un escenario para luego decidir si corresponde realizar un estudio de factibilidad.")

with tabs[7]:
    st.subheader("Matriz integral")
    q=st.text_input("Buscar actividad, producto, sector, territorio u oportunidad")
    show=f.copy()
    if q:
        mask=show.astype(str).apply(lambda c:c.str.contains(q,case=False,na=False)).any(axis=1)
        show=show[mask]
    columns=[
        "mineral","tipo_eslabonamiento","etapa_proyecto","macrosector","actividad",
        "requerimiento_o_producto","frecuencia","demanda_anual_usd_demo",
        "participacion_catamarca_pct_demo","participacion_resto_arg_pct_demo",
        "participacion_importada_pct_demo","empleo_local_potencial_demo",
        "criticidad","complejidad_tecnica","capacidad_local_demo","territorio_potencial",
        "accion_sugerida","barrera_principal","beneficio_provincial","certificaciones_referenciales"
    ]
    st.dataframe(show[columns],use_container_width=True,hide_index=True,
        column_config={
            "demanda_anual_usd_demo":st.column_config.NumberColumn("Demanda demo",format="$ %.0f"),
            "participacion_catamarca_pct_demo":st.column_config.ProgressColumn("% Catamarca demo",min_value=0,max_value=100),
            "participacion_resto_arg_pct_demo":st.column_config.NumberColumn("% resto Arg.",format="%.0f%%"),
            "participacion_importada_pct_demo":st.column_config.NumberColumn("% importado",format="%.0f%%")
        })
    st.download_button("Descargar filtro CSV",show.to_csv(index=False).encode("utf-8-sig"),"sipm_filtro.csv","text/csv")

st.divider()
st.markdown("**Qué vende esta demo:** una infraestructura de inteligencia que conecta minería, proveedores, industria, territorio, universidad y política pública; no un simple dashboard.")
st.caption("Todos los indicadores cuantitativos de esta demostración deben sustituirse por información relevada, validada y trazable en la implementación real.")
