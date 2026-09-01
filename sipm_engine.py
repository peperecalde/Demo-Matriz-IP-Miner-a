from __future__ import annotations

import math
from typing import Iterable, Mapping, Optional, Sequence, Tuple, List, Dict

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# SIPM · Motor matemático de escenarios (DEMO calibrable)
# -----------------------------------------------------------------------------
# Las identidades contables son exactas. Los coeficientes económicos
# (elasticidad laboral y escalas cualitativas) son demostrativos y deben
# calibrarse con evidencia real antes de interpretar los resultados como
# estimaciones causales.

PARTICIPATION_COLS = [
    "participacion_catamarca_pct_demo",
    "participacion_resto_arg_pct_demo",
    "participacion_importada_pct_demo",
]

DERIVED_COLUMNS = [
    "captura_local_usd_demo",
    "gasto_fuera_catamarca_usd_demo",
    "puntaje_oportunidad_demo",
    "prioridad_demo",
    "indice_factibilidad_demo",
    "indice_presion_politica_demo",
    "crecimiento_demanda_pct_demo",
    "delta_empleo_demo",
    "tipo_respuesta_demo",
]

CAPACITY_SCORE = {
    "Incipiente": 0.30,
    "Parcial": 0.60,
    "Consolidada": 0.90,
}

COMPLEXITY_SCORE = {
    "Baja": 0.20,
    "Media": 0.45,
    "Alta": 0.70,
    "Muy alta": 0.90,
}

CRITICALITY_SCORE = {
    "Baja": 0.25,
    "Media": 0.60,
    "Alta": 1.00,
}

FREQUENCY_MULTIPLIER = {
    "Mercado potencial": 0.50,
    "Por campaña": 0.65,
    "Por proyecto": 0.75,
    "Mensual": 1.00,
}

# Elasticidad empleo/captura local. 1 implica proporcionalidad perfecta;
# valores menores representan ganancias de productividad/capacidad ociosa.
LABOR_ELASTICITY = {
    "Construcción": 0.95,
    "Campamentos": 0.95,
    "Servicios generales": 0.95,
    "Seguridad y salud": 0.92,
    "Mantenimiento": 0.90,
    "Logística": 0.88,
    "Exploración y geociencias": 0.88,
    "Ambiente": 0.88,
    "Educación y formación": 0.90,
    "Servicios profesionales": 0.86,
    "Metalmecánica": 0.82,
    "Laboratorios": 0.82,
    "Agua": 0.80,
    "Energía": 0.78,
    "Telecomunicaciones": 0.78,
    "Servicios financieros": 0.76,
    "Tecnología": 0.76,
    "Equipamiento": 0.70,
    "Procesamiento mineral": 0.70,
    "Industria química": 0.68,
    "Metalurgia": 0.68,
    "Manufactura avanzada": 0.66,
    "Materiales avanzados": 0.64,
    "Industria eléctrica": 0.68,
    "Economía circular": 0.78,
    "Joyería y diseño": 0.85,
    "Combustibles y lubricantes": 0.68,
}
DEFAULT_LABOR_ELASTICITY = 0.80


def normalize_linkages(series: pd.Series) -> pd.Series:
    return (
        series.astype(str).str.strip().replace({
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


def _numeric(series: pd.Series, *, fill: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(fill).astype(float)


def _align_base(frame: pd.DataFrame, base_reference: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la base alineada fila a fila por id, nunca por posición."""
    if "id" not in frame.columns or "id" not in base_reference.columns:
        raise ValueError("La matriz y la Base SIPM deben contener la columna 'id'.")
    if frame["id"].duplicated().any():
        raise ValueError("El escenario contiene IDs duplicados.")
    if base_reference["id"].duplicated().any():
        raise ValueError("La Base SIPM contiene IDs duplicados.")

    base_idx = base_reference.set_index("id", drop=False)
    missing_ids = [x for x in frame["id"].tolist() if x not in base_idx.index]
    if missing_ids:
        raise ValueError(f"El escenario contiene IDs que no existen en la Base SIPM: {missing_ids[:10]}")
    aligned = base_idx.loc[frame["id"].tolist()].copy()
    aligned.index = frame.index
    return aligned


def prepare_scenario(
    frame: pd.DataFrame,
    base_reference: pd.DataFrame,
    manual_employment_ids: Optional[Iterable] = None,
) -> pd.DataFrame:
    """Recalcula un escenario completo preservando identidades matemáticas.

    Reglas:
    - Demanda y participaciones son supuestos de entrada.
    - Captura local y gasto fuera son identidades contables exactas.
    - Empleo se deriva de la captura local con elasticidad sectorial DEMO,
      salvo IDs marcados explícitamente como override manual.
    - Factibilidad, presión de política y tipología se derivan de la matriz.
    """
    out = frame.copy()
    base = _align_base(out, base_reference)
    manual_ids = set(manual_employment_ids or [])

    if "tipo_eslabonamiento" in out.columns:
        out["tipo_eslabonamiento"] = normalize_linkages(out["tipo_eslabonamiento"])
    if "tipo_eslabonamiento" in base.columns:
        base["tipo_eslabonamiento"] = normalize_linkages(base["tipo_eslabonamiento"])

    numeric_cols = [
        "demanda_anual_usd_demo",
        *PARTICIPATION_COLS,
        "empleo_local_potencial_demo",
    ]
    for c in numeric_cols:
        if c not in out.columns:
            raise ValueError(f"Falta la columna obligatoria: {c}")
        out[c] = _numeric(out[c])
        base[c] = _numeric(base[c])

    out["demanda_anual_usd_demo"] = out["demanda_anual_usd_demo"].clip(lower=0)
    for c in PARTICIPATION_COLS:
        out[c] = out[c].clip(lower=0, upper=100)

    # Identidades contables.
    out["captura_local_usd_demo"] = (
        out["demanda_anual_usd_demo"] * out["participacion_catamarca_pct_demo"] / 100.0
    )
    out["gasto_fuera_catamarca_usd_demo"] = (
        out["demanda_anual_usd_demo"] - out["captura_local_usd_demo"]
    )

    base_capture = base["demanda_anual_usd_demo"] * base["participacion_catamarca_pct_demo"] / 100.0
    base_demand = base["demanda_anual_usd_demo"].replace(0, np.nan)
    scenario_capture = out["captura_local_usd_demo"]

    # Crecimiento de demanda relativo a Base SIPM.
    demand_ratio = (out["demanda_anual_usd_demo"] / base_demand).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    out["crecimiento_demanda_pct_demo"] = (demand_ratio - 1.0) * 100.0

    # Empleo automático: calibrado para reproducir exactamente la base cuando no hay cambios.
    capture_ratio = pd.Series(1.0, index=out.index, dtype=float)
    positive_base_capture = base_capture > 0
    capture_ratio.loc[positive_base_capture] = (
        scenario_capture.loc[positive_base_capture] / base_capture.loc[positive_base_capture]
    )
    # Si la base no tenía captura local, usamos la variación de demanda como fallback.
    capture_ratio.loc[~positive_base_capture] = demand_ratio.loc[~positive_base_capture]
    capture_ratio = capture_ratio.clip(lower=0)

    elasticity = out["macrosector"].astype(str).map(LABOR_ELASTICITY).fillna(DEFAULT_LABOR_ELASTICITY).astype(float)
    new_freq = out["frecuencia"].astype(str).map(FREQUENCY_MULTIPLIER).fillna(0.75).astype(float)
    base_freq = base["frecuencia"].astype(str).map(FREQUENCY_MULTIPLIER).fillna(0.75).astype(float)
    freq_ratio = (new_freq / base_freq.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    auto_employment = base["empleo_local_potencial_demo"] * np.power(capture_ratio, elasticity) * freq_ratio
    auto_employment = auto_employment.clip(lower=0)

    if manual_ids:
        manual_mask = out["id"].isin(manual_ids)
        original_manual = out["empleo_local_potencial_demo"].copy()
        out["empleo_local_potencial_demo"] = auto_employment
        out.loc[manual_mask, "empleo_local_potencial_demo"] = original_manual.loc[manual_mask].clip(lower=0)
    else:
        out["empleo_local_potencial_demo"] = auto_employment

    out["delta_empleo_demo"] = out["empleo_local_potencial_demo"] - base["empleo_local_potencial_demo"]

    # Factibilidad productiva (índice DEMO, 0–100).
    cap = out["capacidad_local_demo"].astype(str).map(CAPACITY_SCORE).fillna(0.45).astype(float)
    complexity = out["complejidad_tecnica"].astype(str).map(COMPLEXITY_SCORE).fillna(0.55).astype(float)
    complexity_factor = 1.0 - 0.55 * complexity
    out["indice_factibilidad_demo"] = (100.0 * cap * complexity_factor).clip(lower=0, upper=100)

    # Puntaje de oportunidad histórica del SIPM: mantenemos la identidad conceptual,
    # pero ahora el empleo se recalcula automáticamente.
    out["puntaje_oportunidad_demo"] = (
        (1 - out["participacion_catamarca_pct_demo"] / 100.0) * 45
        + out["gasto_fuera_catamarca_usd_demo"].clip(lower=10).apply(lambda x: min(1.0, math.log10(x) / 8.0)) * 35
        + (out["empleo_local_potencial_demo"] / 250.0).clip(upper=1) * 20
    ).round()
    out["prioridad_demo"] = pd.cut(
        out["puntaje_oportunidad_demo"], bins=[-1, 49, 69, 101], labels=["Consolidar", "Media", "Alta"]
    ).astype(str)

    # Presión de política: combina las demás dimensiones para que capacidad,
    # complejidad, criticidad e importaciones también propaguen sus cambios.
    market_gap = (out["gasto_fuera_catamarca_usd_demo"] / out["demanda_anual_usd_demo"].replace(0, np.nan)).fillna(0).clip(0, 1)
    growth_pressure = (out["crecimiento_demanda_pct_demo"].clip(lower=0, upper=100) / 100.0)
    capacity_gap = (1.0 - cap).clip(0, 1)
    criticality = out["criticidad"].astype(str).map(CRITICALITY_SCORE).fillna(0.50).astype(float)
    import_dep = (out["participacion_importada_pct_demo"] / 100.0).clip(0, 1)
    base_emp = base["empleo_local_potencial_demo"].replace(0, np.nan)
    employment_pressure = ((out["empleo_local_potencial_demo"] - base["empleo_local_potencial_demo"]) / base_emp)
    employment_pressure = employment_pressure.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0, upper=1)

    out["indice_presion_politica_demo"] = (
        market_gap * 25
        + growth_pressure * 15
        + capacity_gap * 15
        + complexity * 10
        + criticality * 10
        + import_dep * 15
        + employment_pressure * 10
    ).clip(0, 100).round(1)

    def response(row) -> str:
        cap_name = str(row.get("capacidad_local_demo", ""))
        comp = str(row.get("complejidad_tecnica", ""))
        crit = str(row.get("criticidad", ""))
        imp = float(row.get("participacion_importada_pct_demo", 0) or 0)
        local = float(row.get("participacion_catamarca_pct_demo", 0) or 0)
        linkage = str(row.get("tipo_eslabonamiento", ""))
        growth = float(row.get("crecimiento_demanda_pct_demo", 0) or 0)
        jobs_delta = float(row.get("delta_empleo_demo", 0) or 0)
        if linkage == "Aguas abajo" and comp in {"Alta", "Muy alta"}:
            return "Prefactibilidad industrial / atracción de inversión"
        if crit == "Alta" and imp >= 40:
            return "Seguridad de abastecimiento / sustitución estratégica"
        if cap_name == "Consolidada" and local < 50 and growth >= 0:
            return "Escalamiento de proveedores locales"
        if cap_name == "Incipiente" and comp in {"Alta", "Muy alta"}:
            return "Atracción de inversión + tecnología + formación"
        if jobs_delta > 0:
            return "Capital humano + desarrollo de proveedores"
        return "Monitoreo / consolidación"

    out["tipo_respuesta_demo"] = out.apply(response, axis=1)
    return out


def apply_participation_deltas(
    frame: pd.DataFrame,
    indices: Sequence,
    deltas: Mapping[str, float],
    changed_columns: Sequence[str],
    auto_balance: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """Aplica cambios en p.p. con cierre exacto al 100% y trazabilidad.

    Los valores explícitos se respetan hasta los límites [0,100]. Si quedan
    columnas sin modificar, absorben el residual proporcionalmente a su peso
    previo. Si las tres columnas fueron modificadas y no suman 100, se rechaza.
    """
    out = frame.copy()
    idx = out.index.intersection(pd.Index(indices))
    notes: List[str] = []
    changed = [c for c in changed_columns if c in PARTICIPATION_COLS]
    untouched = [c for c in PARTICIPATION_COLS if c not in changed]

    if len(idx) == 0 or not changed:
        return out, notes

    for c in PARTICIPATION_COLS:
        out[c] = _numeric(out[c])

    for i in idx:
        before = out.loc[i, PARTICIPATION_COLS].astype(float).copy()
        vals = before.copy()
        for c in changed:
            raw = vals[c] + float(deltas.get(c, 0.0))
            clipped = min(100.0, max(0.0, raw))
            if abs(clipped - raw) > 1e-9:
                notes.append(f"ID {out.at[i,'id']}: {c} alcanzó el límite {'0%' if raw < 0 else '100%'}.")
            vals[c] = clipped

        if not auto_balance:
            if abs(vals.sum() - 100.0) > 1e-7:
                raise ValueError(
                    f"ID {out.at[i,'id']}: las participaciones suman {vals.sum():.4f}% y deben sumar 100%."
                )
        else:
            explicit_sum = float(vals[changed].sum())
            residual = 100.0 - explicit_sum
            if residual < -1e-7:
                raise ValueError(
                    f"ID {out.at[i,'id']}: las participaciones modificadas por sí solas superan 100%."
                )
            if untouched:
                old_untouched = before[untouched].clip(lower=0)
                denom = float(old_untouched.sum())
                if denom > 0:
                    vals[untouched] = old_untouched / denom * max(0.0, residual)
                else:
                    vals[untouched] = max(0.0, residual) / len(untouched)
            elif abs(residual) > 1e-7:
                raise ValueError(
                    f"ID {out.at[i,'id']}: modificaste las tres participaciones y el resultado suma {explicit_sum:.4f}%. "
                    "Ajustá los cambios para que sumen exactamente 100%."
                )

        # Corrección de redondeo en la última columna no explícita (o en resto Argentina si todas son explícitas).
        diff = 100.0 - float(vals.sum())
        target_col = untouched[-1] if untouched else "participacion_resto_arg_pct_demo"
        vals[target_col] += diff
        if (vals < -1e-7).any() or (vals > 100.0000001).any():
            raise ValueError(f"ID {out.at[i,'id']}: el reequilibrio genera una participación fuera de rango.")
        out.loc[i, PARTICIPATION_COLS] = vals.values.astype(float)

    return out, notes


def validate_scenario_math(frame: pd.DataFrame, tolerance: float = 1e-6) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    required = ["demanda_anual_usd_demo", "empleo_local_potencial_demo", *PARTICIPATION_COLS,
                "captura_local_usd_demo", "gasto_fuera_catamarca_usd_demo"]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        return False, ["Faltan columnas calculadas/obligatorias: " + ", ".join(missing)]

    nums = frame[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(nums.to_numpy(dtype=float)).all():
        errors.append("Existen valores NaN o infinitos en variables numéricas críticas.")
    if (nums["demanda_anual_usd_demo"] < -tolerance).any():
        errors.append("Existe demanda negativa.")
    if (nums["empleo_local_potencial_demo"] < -tolerance).any():
        errors.append("Existe empleo negativo.")
    for c in PARTICIPATION_COLS:
        if ((nums[c] < -tolerance) | (nums[c] > 100 + tolerance)).any():
            errors.append(f"{c} contiene valores fuera de 0–100%.")
    sums = nums[PARTICIPATION_COLS].sum(axis=1)
    if not np.allclose(sums, 100.0, atol=tolerance, rtol=0):
        bad = frame.loc[(sums - 100).abs() > tolerance, "id"].tolist()[:10] if "id" in frame.columns else []
        errors.append(f"Las participaciones no suman 100% en todos los registros. IDs: {bad}")
    capture_expected = nums["demanda_anual_usd_demo"] * nums["participacion_catamarca_pct_demo"] / 100.0
    if not np.allclose(nums["captura_local_usd_demo"], capture_expected, atol=max(tolerance, 0.01), rtol=1e-10):
        errors.append("La identidad Captura local = Demanda × % Catamarca no se cumple.")
    outside_expected = nums["demanda_anual_usd_demo"] - nums["captura_local_usd_demo"]
    if not np.allclose(nums["gasto_fuera_catamarca_usd_demo"], outside_expected, atol=max(tolerance, 0.01), rtol=1e-10):
        errors.append("La identidad Gasto fuera = Demanda − Captura local no se cumple.")
    return len(errors) == 0, errors


def baseline_invariance_check(base_reference: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Comprueba que un escenario sin cambios reproduzca exactamente la base en los KPIs esenciales."""
    modeled = prepare_scenario(base_reference.copy(), base_reference)
    errors: List[str] = []
    for c in ["demanda_anual_usd_demo", *PARTICIPATION_COLS, "empleo_local_potencial_demo"]:
        a = pd.to_numeric(base_reference[c], errors="coerce").astype(float)
        b = pd.to_numeric(modeled[c], errors="coerce").astype(float)
        if not np.allclose(a, b, atol=1e-8, rtol=1e-10):
            errors.append(f"La Base SIPM no se reproduce exactamente en {c}.")
    ok_math, math_errors = validate_scenario_math(modeled)
    errors.extend(math_errors)
    return len(errors) == 0 and ok_math, errors


def exact_demand_change_check(base_reference: pd.DataFrame, ids: Sequence, pct: float) -> Tuple[bool, str]:
    """Test unitario: aplicar x% desde base debe generar exactamente x% en la demanda seleccionada."""
    work = base_reference.copy()
    mask = work["id"].isin(ids)
    before = float(work.loc[mask, "demanda_anual_usd_demo"].sum())
    work.loc[mask, "demanda_anual_usd_demo"] = pd.to_numeric(work.loc[mask, "demanda_anual_usd_demo"], errors="coerce") * (1 + pct / 100.0)
    modeled = prepare_scenario(work, base_reference)
    after = float(modeled.loc[mask, "demanda_anual_usd_demo"].sum())
    expected = before * (1 + pct / 100.0)
    ok = math.isclose(after, expected, rel_tol=1e-12, abs_tol=0.01)
    return ok, f"Base={before:.6f}; esperado={expected:.6f}; obtenido={after:.6f}"
