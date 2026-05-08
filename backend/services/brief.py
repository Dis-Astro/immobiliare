"""
Servizio Brief Mattutino: aggrega dati operativi (rate/APE/contratti/interventi),
chiama AI per la sintesi e prepara il body HTML/testo per l'email.
"""
import logging
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from services.ai_provider import send_chat_message

logger = logging.getLogger(__name__)


BRIEF_CONFIG_KEY = "brief_config"


async def get_brief_config(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Recupera la configurazione brief mattutino, con default."""
    config = await db.config.find_one({"key": BRIEF_CONFIG_KEY}, {"_id": 0})
    if not config:
        return {
            "key": BRIEF_CONFIG_KEY,
            "enabled": False,
            "cron_hour": 8,
            "cron_minute": 0,
            "recipients": [],
            "include_rate": True,
            "include_ape": True,
            "include_contratti": True,
            "include_interventi": True,
            "last_sent_at": None,
            "last_status": None,
            "last_error": None,
        }
    return config


async def aggregate_brief_data(db: AsyncIOMotorDatabase, config: Dict[str, Any]) -> Dict[str, Any]:
    """Raccoglie i dati operativi da includere nel brief secondo i toggle in config."""
    today = date.today()
    target_30 = (today + relativedelta(days=30)).isoformat()
    target_90 = (today + relativedelta(days=90)).isoformat()

    data: Dict[str, Any] = {
        "data_brief": today.isoformat(),
        "rate_in_ritardo": [],
        "ape_in_scadenza": [],
        "contratti_in_scadenza": [],
        "interventi_aperti": [],
    }

    if config.get("include_rate", True):
        rate = await db.rate.find(
            {"stato": "in_ritardo"},
            {"_id": 0}
        ).sort("data_scadenza", 1).limit(50).to_list(50)
        for r in rate:
            contratto = await db.contratti.find_one(
                {"id": r["contratto_id"]},
                {"_id": 0, "codice_contratto": 1, "affittuario_id": 1}
            )
            if contratto:
                r["contratto_codice"] = contratto.get("codice_contratto")
                soggetto = await db.soggetti.find_one(
                    {"id": contratto.get("affittuario_id")},
                    {"_id": 0, "nome": 1}
                )
                r["affittuario"] = soggetto["nome"] if soggetto else "—"
        data["rate_in_ritardo"] = rate

    if config.get("include_ape", True):
        ape = await db.ape.find(
            {"scadenza": {"$lte": target_90, "$gte": today.isoformat()}, "stato": {"$ne": "sostituito"}},
            {"_id": 0}
        ).sort("scadenza", 1).limit(50).to_list(50)
        for a in ape:
            unita = await db.unita.find_one(
                {"id": a.get("unita_id")},
                {"_id": 0, "codice_unita": 1, "immobile_id": 1}
            )
            if unita:
                a["unita_codice"] = unita.get("codice_unita")
                immobile = await db.immobili.find_one(
                    {"id": unita.get("immobile_id")},
                    {"_id": 0, "titolo": 1}
                )
                a["immobile"] = immobile["titolo"] if immobile else "—"
        data["ape_in_scadenza"] = ape

    if config.get("include_contratti", True):
        contratti = await db.contratti.find(
            {"stato": "attivo", "data_scadenza": {"$lte": target_30}},
            {"_id": 0}
        ).sort("data_scadenza", 1).limit(50).to_list(50)
        for c in contratti:
            soggetto = await db.soggetti.find_one(
                {"id": c.get("affittuario_id")},
                {"_id": 0, "nome": 1}
            )
            c["affittuario"] = soggetto["nome"] if soggetto else "—"
            unita = await db.unita.find_one(
                {"id": c.get("unita_id")},
                {"_id": 0, "codice_unita": 1, "immobile_id": 1}
            )
            if unita:
                immobile = await db.immobili.find_one(
                    {"id": unita.get("immobile_id")},
                    {"_id": 0, "titolo": 1}
                )
                c["immobile"] = immobile["titolo"] if immobile else "—"
        data["contratti_in_scadenza"] = contratti

    if config.get("include_interventi", True):
        interventi = await db.interventi.find(
            {"stato": {"$in": ["aperto", "in_lavorazione"]}},
            {"_id": 0}
        ).sort("data_apertura", -1).limit(30).to_list(30)
        data["interventi_aperti"] = interventi

    return data


def _build_data_summary_text(data: Dict[str, Any]) -> str:
    """Sintesi testuale dei dati operativi per il prompt AI."""
    parts = [f"== Brief operativo del {data['data_brief']} ==\n"]

    rate = data.get("rate_in_ritardo", [])
    parts.append(f"\n[RATE IN RITARDO: {len(rate)}]")
    for r in rate[:20]:
        parts.append(
            f"- {r.get('contratto_codice', '?')} | {r.get('affittuario', '—')} | "
            f"periodo {r.get('periodo')} | € {r.get('importo', 0):.2f} | scadenza {r.get('data_scadenza', '—')}"
        )

    ape = data.get("ape_in_scadenza", [])
    parts.append(f"\n[APE IN SCADENZA (90gg): {len(ape)}]")
    for a in ape[:20]:
        parts.append(
            f"- {a.get('immobile', '—')} / {a.get('unita_codice', '—')} | "
            f"classe {a.get('classe_energetica', '?')} | scadenza {a.get('scadenza', '—')}"
        )

    contratti = data.get("contratti_in_scadenza", [])
    parts.append(f"\n[CONTRATTI IN SCADENZA (30gg): {len(contratti)}]")
    for c in contratti[:20]:
        parts.append(
            f"- {c.get('codice_contratto', '?')} | {c.get('affittuario', '—')} | "
            f"{c.get('immobile', '—')} | scadenza {c.get('data_scadenza', '—')}"
        )

    interventi = data.get("interventi_aperti", [])
    parts.append(f"\n[INTERVENTI APERTI: {len(interventi)}]")
    for i in interventi[:20]:
        parts.append(
            f"- {i.get('tipo', '?')} | priorità {i.get('priorita', '—')} | "
            f"stato {i.get('stato', '—')} | apertura {i.get('data_apertura', '—')}"
        )

    return "\n".join(parts)


async def generate_ai_summary(db: AsyncIOMotorDatabase, data: Dict[str, Any]) -> str:
    """Genera la sintesi AI del brief. Restituisce testo plain. In caso di errore, fallback a sintesi statica."""
    raw_text = _build_data_summary_text(data)
    user_msg = (
        "Sei l'assistente di un property manager. Sintetizza il brief operativo qui sotto in italiano, "
        "con tono professionale e azioni concrete. Massimo 250 parole. Struttura:\n"
        "1. Apertura (1 frase) sullo stato generale.\n"
        "2. PRIORITÀ ALTE: cosa va affrontato OGGI (rate in forte ritardo, APE già scadenze imminenti, contratti che scadono entro 7gg).\n"
        "3. Da pianificare questa settimana.\n"
        "4. Una raccomandazione operativa specifica (es. inviare X solleciti, pianificare sopralluogo Y).\n\n"
        f"DATI:\n{raw_text}"
    )
    try:
        result = await send_chat_message(
            db=db,
            session_id="brief-mattutino",
            user_message=user_msg,
        )
        return result.get("content", "").strip() or _fallback_summary(data)
    except Exception as e:
        logger.warning(f"AI summary failed, using fallback: {e}")
        return _fallback_summary(data)


def _fallback_summary(data: Dict[str, Any]) -> str:
    """Sintesi statica usata se l'AI non risponde."""
    n_rate = len(data.get("rate_in_ritardo", []))
    n_ape = len(data.get("ape_in_scadenza", []))
    n_contratti = len(data.get("contratti_in_scadenza", []))
    n_interventi = len(data.get("interventi_aperti", []))
    if n_rate == n_ape == n_contratti == n_interventi == 0:
        return "Tutto in ordine: nessuna criticità da segnalare oggi."
    parts = ["Sintesi automatica (AI non disponibile):"]
    if n_rate:
        parts.append(f"• {n_rate} rate in ritardo da incassare.")
    if n_ape:
        parts.append(f"• {n_ape} APE in scadenza nei prossimi 90 giorni.")
    if n_contratti:
        parts.append(f"• {n_contratti} contratti in scadenza nei prossimi 30 giorni.")
    if n_interventi:
        parts.append(f"• {n_interventi} interventi di manutenzione aperti.")
    return "\n".join(parts)


def render_brief_html(data: Dict[str, Any], ai_summary: str) -> str:
    """Costruisce l'HTML dell'email del brief."""
    def section(title: str, items: List[Dict[str, Any]], render_row) -> str:
        if not items:
            return ""
        rows = "".join(render_row(it) for it in items[:20])
        more = f"<p style='color:#64748b;font-size:12px;margin:4px 0;'>...e altri {len(items) - 20} elementi</p>" if len(items) > 20 else ""
        return f"""
        <h3 style="color:#0F172A;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-top:24px;">{title}</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">{rows}</table>
        {more}
        """

    rate_html = section(
        f"💸 Rate in ritardo ({len(data.get('rate_in_ritardo', []))})",
        data.get("rate_in_ritardo", []),
        lambda r: f"<tr><td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{r.get('contratto_codice', '?')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{r.get('affittuario', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{r.get('periodo', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:#dc2626;font-weight:600;'>€ {r.get('importo', 0):.2f}</td></tr>"
    )

    ape_html = section(
        f"🏷️ APE in scadenza ({len(data.get('ape_in_scadenza', []))})",
        data.get("ape_in_scadenza", []),
        lambda a: f"<tr><td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{a.get('immobile', '—')} / {a.get('unita_codice', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>Classe {a.get('classe_energetica', '?')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;'>{a.get('scadenza', '—')}</td></tr>"
    )

    contratti_html = section(
        f"📄 Contratti in scadenza ({len(data.get('contratti_in_scadenza', []))})",
        data.get("contratti_in_scadenza", []),
        lambda c: f"<tr><td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{c.get('codice_contratto', '?')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{c.get('affittuario', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{c.get('immobile', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;'>{c.get('data_scadenza', '—')}</td></tr>"
    )

    interventi_html = section(
        f"🔧 Interventi aperti ({len(data.get('interventi_aperti', []))})",
        data.get("interventi_aperti", []),
        lambda i: f"<tr><td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{i.get('tipo', '?')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{i.get('priorita', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;'>{i.get('stato', '—')}</td>"
                  f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;'>{i.get('data_apertura', '—')}</td></tr>"
    )

    ai_html = ai_summary.replace("\n", "<br/>")

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f8fafc;margin:0;padding:24px;">
  <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h1 style="color:#0F172A;margin:0 0 8px 0;font-size:24px;">☀️ Brief mattutino — EstateWise</h1>
    <p style="color:#64748b;margin:0 0 24px 0;font-size:14px;">Riepilogo del {data['data_brief']}</p>

    <div style="background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);border-left:4px solid #0284c7;padding:16px;border-radius:6px;margin-bottom:16px;">
      <p style="margin:0;color:#0c4a6e;line-height:1.6;font-size:14px;">{ai_html}</p>
    </div>

    {rate_html}
    {ape_html}
    {contratti_html}
    {interventi_html}

    <hr style="margin:32px 0 16px 0;border:none;border-top:1px solid #e2e8f0;"/>
    <p style="color:#94a3b8;font-size:12px;text-align:center;margin:0;">
      Brief generato automaticamente da EstateWise. Per modificare i destinatari o disattivare l'invio: Impostazioni → Brief AI.
    </p>
  </div>
</body>
</html>"""


def render_brief_text(data: Dict[str, Any], ai_summary: str) -> str:
    """Versione testuale dell'email."""
    raw = _build_data_summary_text(data)
    return f"BRIEF MATTUTINO ESTATEWISE — {data['data_brief']}\n\n{ai_summary}\n\n{raw}"


async def build_brief(db: AsyncIOMotorDatabase, config: Dict[str, Any]) -> Dict[str, Any]:
    """Costruisce il brief completo (dati + AI summary + HTML/text) pronto per l'invio."""
    data = await aggregate_brief_data(db, config)
    ai_summary = await generate_ai_summary(db, data)
    return {
        "data": data,
        "ai_summary": ai_summary,
        "html": render_brief_html(data, ai_summary),
        "text": render_brief_text(data, ai_summary),
        "stats": {
            "rate_in_ritardo": len(data.get("rate_in_ritardo", [])),
            "ape_in_scadenza": len(data.get("ape_in_scadenza", [])),
            "contratti_in_scadenza": len(data.get("contratti_in_scadenza", [])),
            "interventi_aperti": len(data.get("interventi_aperti", [])),
        }
    }
