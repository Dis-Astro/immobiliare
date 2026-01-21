"""
Router Report con supporto opzionale per WeasyPrint.
Se WeasyPrint non è disponibile, i report PDF restituiscono un messaggio di errore.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional
from datetime import date, datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import io
import logging

# Try to import WeasyPrint - it may fail if system dependencies are missing
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    logging.warning(f"WeasyPrint not available: {e}. PDF generation disabled.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("Pandas not available. Excel export disabled.")

from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/reports", tags=["Report"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "pdf"

# Jinja2 environment
if TEMPLATES_DIR.exists():
    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True
    )
else:
    jinja_env = None

# Default CSS for PDF
DEFAULT_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @top-center { content: "EstateWise"; font-size: 10pt; color: #666; }
    @bottom-center { content: "Pagina " counter(page) " di " counter(pages); font-size: 9pt; color: #666; }
}
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #333; }
h1 { font-size: 20pt; margin-bottom: 0.5em; color: #1a1a2e; }
h2 { font-size: 16pt; margin-top: 1.5em; margin-bottom: 0.5em; color: #1a1a2e; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }
h3 { font-size: 13pt; margin-top: 1em; margin-bottom: 0.3em; color: #333; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; }
th, td { padding: 8px 12px; text-align: left; border: 1px solid #ddd; }
th { background-color: #f5f5f5; font-weight: 600; }
tr:nth-child(even) { background-color: #fafafa; }
.header { text-align: center; margin-bottom: 2em; }
.info-box { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 1em 0; }
.status-ok { color: #28a745; }
.status-warning { color: #ffc107; }
.status-danger { color: #dc3545; }
.footer { margin-top: 2em; padding-top: 1em; border-top: 1px solid #ddd; font-size: 9pt; color: #666; }
.signature-area { margin-top: 3em; }
.signature-box { display: inline-block; width: 45%; text-align: center; }
.signature-line { border-top: 1px solid #333; margin-top: 50px; padding-top: 5px; }
"""


def generate_pdf(html_content: str) -> bytes:
    """Generate PDF from HTML using WeasyPrint."""
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Generazione PDF non disponibile. Librerie di sistema mancanti (WeasyPrint)."
        )
    
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf(stylesheets=[CSS(string=DEFAULT_CSS)])
    return pdf_bytes


@router.get("/status")
async def get_report_status():
    """Check report generation capabilities."""
    return {
        "pdf_available": WEASYPRINT_AVAILABLE,
        "excel_available": PANDAS_AVAILABLE,
        "csv_available": True,
        "json_available": True,
        "message": "OK" if WEASYPRINT_AVAILABLE else "PDF generation requires system libraries. Install libpangoft2-1.0-0"
    }


@router.get("/contratto/{contratto_id}/pdf")
async def get_contratto_pdf(
    contratto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Generate and download contract PDF (fascicolo contratto)."""
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF non disponibile - WeasyPrint non installato")
    
    contratto = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    # Fetch related data
    locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0})
    affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0})
    unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0})
    immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0}) if unita else None
    
    rate = await db.rate.find({"contratto_id": contratto_id}, {"_id": 0}).sort("periodo", 1).to_list(100)
    variazioni = await db.variazioni.find({"contratto_id": contratto_id}, {"_id": 0}).to_list(50)
    documenti = await db.documenti.find({"livello": "contratto", "ref_id": contratto_id}, {"_id": 0}).to_list(50)
    
    if jinja_env:
        try:
            template = jinja_env.get_template("contratto.html")
            html_content = template.render(
                contratto=contratto,
                locatore=locatore,
                affittuario=affittuario,
                unita=unita,
                immobile=immobile,
                rate=rate,
                variazioni=variazioni,
                documenti=documenti,
                generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            )
        except Exception:
            # Fallback to basic HTML
            html_content = f"""
            <h1>Fascicolo Contratto {contratto.get('codice_contratto', 'N/A')}</h1>
            <p>Locatore: {locatore.get('nome') if locatore else 'N/A'}</p>
            <p>Affittuario: {affittuario.get('nome') if affittuario else 'N/A'}</p>
            <p>Immobile: {immobile.get('titolo') if immobile else 'N/A'}</p>
            <p>Canone: € {contratto.get('canone_importo', 0):,.2f}</p>
            """
    else:
        html_content = f"<h1>Contratto {contratto.get('codice_contratto', 'N/A')}</h1>"
    
    pdf_bytes = generate_pdf(html_content)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=contratto_{contratto['codice_contratto']}.pdf"
        }
    )


@router.get("/immobile/{immobile_id}/pdf")
async def get_immobile_pdf(
    immobile_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Generate and download property PDF (scheda immobile)."""
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF non disponibile - WeasyPrint non installato")
    
    immobile = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    unita_list = await db.unita.find({"immobile_id": immobile_id}, {"_id": 0}).to_list(100)
    spese = await db.spese.find({"immobile_id": immobile_id}, {"_id": 0}).sort("data", -1).to_list(50)
    documenti = await db.documenti.find({"livello": "immobile", "ref_id": immobile_id}, {"_id": 0}).to_list(50)
    
    for u in unita_list:
        contratti = await db.contratti.find({"unita_id": u["id"]}, {"_id": 0}).to_list(10)
        u["contratti"] = contratti
    
    if jinja_env:
        try:
            template = jinja_env.get_template("immobile.html")
            html_content = template.render(
                immobile=immobile,
                unita_list=unita_list,
                spese=spese,
                documenti=documenti,
                totale_spese=sum(s["importo"] for s in spese),
                generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            )
        except Exception:
            html_content = f"<h1>Scheda Immobile {immobile.get('codice', 'N/A')}</h1>"
    else:
        html_content = f"<h1>Immobile {immobile.get('codice', 'N/A')}</h1>"
    
    pdf_bytes = generate_pdf(html_content)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=immobile_{immobile['codice']}.pdf"
        }
    )


@router.get("/verbale/{verbale_id}/pdf")
async def get_verbale_pdf(
    verbale_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Generate and download verbale PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF non disponibile - WeasyPrint non installato")
    
    verbale = await db.verbali.find_one({"id": verbale_id}, {"_id": 0})
    if not verbale:
        raise HTTPException(status_code=404, detail="Verbale non trovato")
    
    contratto = await db.contratti.find_one({"id": verbale["contratto_id"]}, {"_id": 0})
    affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0}) if contratto else None
    locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0}) if contratto else None
    unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0}) if contratto else None
    immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0}) if unita else None
    
    if jinja_env:
        try:
            template = jinja_env.get_template("verbale.html")
            html_content = template.render(
                verbale=verbale,
                contratto=contratto,
                affittuario=affittuario,
                locatore=locatore,
                unita=unita,
                immobile=immobile,
                generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            )
        except Exception:
            html_content = f"<h1>Verbale {verbale.get('tipo', 'N/A')}</h1>"
    else:
        html_content = f"<h1>Verbale {verbale.get('tipo', 'N/A')}</h1>"
    
    pdf_bytes = generate_pdf(html_content)
    
    codice = contratto['codice_contratto'] if contratto else 'unknown'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=verbale_{verbale['tipo']}_{codice}.pdf"
        }
    )


@router.get("/pagamenti/pdf")
async def get_pagamenti_pdf(
    periodo_da: Optional[str] = None,
    periodo_a: Optional[str] = None,
    immobile_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Generate and download payments report PDF."""
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF non disponibile - WeasyPrint non installato")
    
    query = {}
    if periodo_da:
        query["periodo"] = {"$gte": periodo_da}
    if periodo_a:
        if "periodo" not in query:
            query["periodo"] = {}
        query["periodo"]["$lte"] = periodo_a
    
    rate = await db.rate.find(query, {"_id": 0}).sort("periodo", 1).to_list(10000)
    
    if immobile_id:
        unita_ids = [u["id"] async for u in db.unita.find({"immobile_id": immobile_id}, {"id": 1})]
        contratto_ids = [c["id"] async for c in db.contratti.find({"unita_id": {"$in": unita_ids}}, {"id": 1})]
        rate = [r for r in rate if r["contratto_id"] in contratto_ids]
    
    for r in rate:
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else "N/A"
    
    totale = sum(r["importo"] for r in rate)
    incassato = sum(r["importo"] for r in rate if r["stato"] == "incassato")
    in_ritardo = sum(r["importo"] for r in rate if r["stato"] == "in_ritardo")
    
    if jinja_env:
        try:
            template = jinja_env.get_template("pagamenti.html")
            html_content = template.render(
                rate=rate,
                periodo_da=periodo_da or "inizio",
                periodo_a=periodo_a or "oggi",
                totale=totale,
                incassato=incassato,
                in_ritardo=in_ritardo,
                percentuale=round(incassato/totale*100, 1) if totale > 0 else 0,
                generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
            )
        except Exception:
            html_content = f"<h1>Report Pagamenti</h1><p>Totale: € {totale:,.2f}</p>"
    else:
        html_content = f"<h1>Report Pagamenti</h1>"
    
    pdf_bytes = generate_pdf(html_content)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_pagamenti_{date.today().isoformat()}.pdf"
        }
    )


@router.get("/pagamenti")
async def report_pagamenti(
    periodo_da: Optional[str] = None,
    periodo_a: Optional[str] = None,
    immobile_id: Optional[str] = None,
    formato: str = Query("json", enum=["json", "csv", "excel"]),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Report pagamenti in JSON, CSV or Excel format."""
    query = {}
    if periodo_da:
        query["periodo"] = {"$gte": periodo_da}
    if periodo_a:
        if "periodo" not in query:
            query["periodo"] = {}
        query["periodo"]["$lte"] = periodo_a
    
    rate = await db.rate.find(query, {"_id": 0}).sort("periodo", 1).to_list(10000)
    
    if immobile_id:
        unita_ids = [u["id"] async for u in db.unita.find({"immobile_id": immobile_id}, {"id": 1})]
        contratto_ids = [c["id"] async for c in db.contratti.find({"unita_id": {"$in": unita_ids}}, {"id": 1})]
        rate = [r for r in rate if r["contratto_id"] in contratto_ids]
    
    for r in rate:
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else ""
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1})
            if unita:
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else ""
    
    if formato == "json":
        totale = sum(r["importo"] for r in rate)
        incassato = sum(r["importo"] for r in rate if r["stato"] == "incassato")
        return {
            "periodo": f"{periodo_da or 'inizio'} - {periodo_a or 'oggi'}",
            "totale_rate": len(rate),
            "totale_importo": totale,
            "totale_incassato": incassato,
            "percentuale_incasso": round(incassato / totale * 100, 1) if totale > 0 else 0,
            "rate": rate
        }
    
    elif formato == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Periodo", "Contratto", "Affittuario", "Immobile", "Importo", "Stato", "Data Incasso"])
        for r in rate:
            writer.writerow([r["periodo"], r.get("contratto_codice", ""), r.get("affittuario_nome", ""), r.get("immobile_titolo", ""), r["importo"], r["stato"], r.get("data_incasso", "")])
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=report_pagamenti.csv"}
        )
    
    elif formato == "excel":
        if not PANDAS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Excel export non disponibile - pandas non installato")
        
        df = pd.DataFrame([{
            "Periodo": r["periodo"],
            "Contratto": r.get("contratto_codice", ""),
            "Affittuario": r.get("affittuario_nome", ""),
            "Immobile": r.get("immobile_titolo", ""),
            "Importo": r["importo"],
            "Stato": r["stato"],
            "Data Incasso": r.get("data_incasso", "")
        } for r in rate])
        
        output = io.BytesIO()
        df.to_excel(output, index=False, sheet_name="Pagamenti")
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=report_pagamenti.xlsx"}
        )


@router.get("/executive")
async def report_executive(
    anno: Optional[int] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Executive report for supervisors."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono accedere a questo report")
    
    if not anno:
        anno = date.today().year
    
    tot_immobili = await db.immobili.count_documents({})
    tot_unita = await db.unita.count_documents({})
    contratti_attivi = await db.contratti.count_documents({"stato": "attivo"})
    
    contratti = await db.contratti.find({"stato": "attivo"}, {"unita_id": 1}).to_list(10000)
    unita_locate = len(set(c["unita_id"] for c in contratti))
    tasso_occupazione = round(unita_locate / tot_unita * 100, 1) if tot_unita > 0 else 0
    
    rate = await db.rate.find({"periodo": {"$regex": f"^{anno}"}}, {"_id": 0}).to_list(100000)
    incassi_per_mese = {}
    for r in rate:
        mese = r["periodo"]
        if r["stato"] == "incassato":
            incassi_per_mese[mese] = incassi_per_mese.get(mese, 0) + r["importo"]
    
    spese = await db.spese.find({"data": {"$regex": f"^{anno}"}}, {"_id": 0}).to_list(100000)
    spese_per_mese = {}
    for s in spese:
        mese = s["data"][:7]
        spese_per_mese[mese] = spese_per_mese.get(mese, 0) + s["importo"]
    
    tutti_mesi = sorted(set(list(incassi_per_mese.keys()) + list(spese_per_mese.keys())))
    profit_loss = [{
        "mese": m,
        "incassi": incassi_per_mese.get(m, 0),
        "spese": spese_per_mese.get(m, 0),
        "profit": incassi_per_mese.get(m, 0) - spese_per_mese.get(m, 0)
    } for m in tutti_mesi]
    
    rate_ritardo = await db.rate.count_documents({"stato": "in_ritardo"})
    totale_rate_anno = len(rate)
    percentuale_insoluti = round(rate_ritardo / totale_rate_anno * 100, 1) if totale_rate_anno > 0 else 0
    
    from dateutil.relativedelta import relativedelta
    target_30 = (date.today() + relativedelta(days=30)).isoformat()
    contratti_scadenza = await db.contratti.count_documents({"stato": "attivo", "data_scadenza": {"$lte": target_30}})
    
    eventi_critici = await db.eventi_critici.count_documents({})
    eventi_alta = await db.eventi_critici.count_documents({"gravita": "alta"})
    
    return {
        "anno": anno,
        "patrimonio": {
            "immobili": tot_immobili,
            "unita_totali": tot_unita,
            "unita_locate": unita_locate,
            "unita_libere": tot_unita - unita_locate,
            "tasso_occupazione": tasso_occupazione
        },
        "contratti": {
            "attivi": contratti_attivi,
            "in_scadenza_30gg": contratti_scadenza
        },
        "finanze": {
            "totale_incassi": sum(incassi_per_mese.values()),
            "totale_spese": sum(spese_per_mese.values()),
            "profit_loss_totale": sum(incassi_per_mese.values()) - sum(spese_per_mese.values()),
            "andamento_mensile": profit_loss
        },
        "pagamenti": {
            "rate_in_ritardo": rate_ritardo,
            "percentuale_insoluti": percentuale_insoluti
        },
        "criticita": {
            "eventi_critici_totali": eventi_critici,
            "eventi_alta_gravita": eventi_alta
        }
    }
