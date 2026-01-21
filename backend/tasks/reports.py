from celery_app import celery_app
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import date, datetime, timezone
from pathlib import Path
import asyncio
import os
import logging
import io

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'estatewise')

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "pdf"

# Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True
)


def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def generate_pdf_from_html(html_content: str, css_content: str = None) -> bytes:
    """Generate PDF from HTML string using WeasyPrint."""
    stylesheets = []
    if css_content:
        stylesheets.append(CSS(string=css_content))
    
    # Default stylesheet
    default_css = """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "EstateWise - Gestione Immobili";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Pagina " counter(page) " di " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.5;
        color: #333;
    }
    h1 { font-size: 20pt; margin-bottom: 0.5em; color: #1a1a2e; }
    h2 { font-size: 16pt; margin-top: 1.5em; margin-bottom: 0.5em; color: #1a1a2e; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }
    h3 { font-size: 13pt; margin-top: 1em; margin-bottom: 0.3em; color: #333; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; }
    th, td { padding: 8px 12px; text-align: left; border: 1px solid #ddd; }
    th { background-color: #f5f5f5; font-weight: 600; }
    tr:nth-child(even) { background-color: #fafafa; }
    .header { text-align: center; margin-bottom: 2em; }
    .header img { max-height: 60px; }
    .info-box { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 1em 0; }
    .status-ok { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-danger { color: #dc3545; }
    .footer { margin-top: 2em; padding-top: 1em; border-top: 1px solid #ddd; font-size: 9pt; color: #666; }
    .signature-area { margin-top: 3em; display: flex; justify-content: space-between; }
    .signature-box { width: 45%; text-align: center; }
    .signature-line { border-top: 1px solid #333; margin-top: 50px; padding-top: 5px; }
    """
    stylesheets.append(CSS(string=default_css))
    
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf(stylesheets=stylesheets)
    
    return pdf_bytes


@celery_app.task(name='tasks.reports.generate_contratto_pdf')
def generate_contratto_pdf(contratto_id: str) -> dict:
    """Generate PDF for a contract (fascicolo contratto)."""
    async def run():
        db = get_db()
        
        contratto = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
        if not contratto:
            return {"error": "Contratto non trovato"}
        
        # Fetch related data
        locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0})
        affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0})
        unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0})
        immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0}) if unita else None
        
        rate = await db.rate.find({"contratto_id": contratto_id}, {"_id": 0}).sort("periodo", 1).to_list(100)
        variazioni = await db.variazioni.find({"contratto_id": contratto_id}, {"_id": 0}).to_list(50)
        documenti = await db.documenti.find({"livello": "contratto", "ref_id": contratto_id}, {"_id": 0}).to_list(50)
        
        # Render template
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
        
        pdf_bytes = generate_pdf_from_html(html_content)
        
        # Save to storage
        output_dir = Path("/data/uploads/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"contratto_{contratto['codice_contratto']}_{date.today().isoformat()}.pdf"
        
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"path": str(output_path), "size": len(pdf_bytes)}
    
    return asyncio.get_event_loop().run_until_complete(run())


@celery_app.task(name='tasks.reports.generate_immobile_pdf')
def generate_immobile_pdf(immobile_id: str) -> dict:
    """Generate PDF for a property (scheda immobile)."""
    async def run():
        db = get_db()
        
        immobile = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
        if not immobile:
            return {"error": "Immobile non trovato"}
        
        unita_list = await db.unita.find({"immobile_id": immobile_id}, {"_id": 0}).to_list(100)
        spese = await db.spese.find({"immobile_id": immobile_id}, {"_id": 0}).sort("data", -1).to_list(50)
        documenti = await db.documenti.find({"livello": "immobile", "ref_id": immobile_id}, {"_id": 0}).to_list(50)
        
        # Get contracts for each unit
        for u in unita_list:
            contratti = await db.contratti.find({"unita_id": u["id"]}, {"_id": 0}).to_list(10)
            u["contratti"] = contratti
        
        template = jinja_env.get_template("immobile.html")
        html_content = template.render(
            immobile=immobile,
            unita_list=unita_list,
            spese=spese,
            documenti=documenti,
            totale_spese=sum(s["importo"] for s in spese),
            generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        )
        
        pdf_bytes = generate_pdf_from_html(html_content)
        
        output_dir = Path("/data/uploads/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"immobile_{immobile['codice']}_{date.today().isoformat()}.pdf"
        
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"path": str(output_path), "size": len(pdf_bytes)}
    
    return asyncio.get_event_loop().run_until_complete(run())


@celery_app.task(name='tasks.reports.generate_verbale_pdf')
def generate_verbale_pdf(verbale_id: str) -> dict:
    """Generate PDF for a verbale (consegna/riconsegna)."""
    async def run():
        db = get_db()
        
        verbale = await db.verbali.find_one({"id": verbale_id}, {"_id": 0})
        if not verbale:
            return {"error": "Verbale non trovato"}
        
        contratto = await db.contratti.find_one({"id": verbale["contratto_id"]}, {"_id": 0})
        affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0}) if contratto else None
        locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0}) if contratto else None
        unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0}) if contratto else None
        immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0}) if unita else None
        
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
        
        pdf_bytes = generate_pdf_from_html(html_content)
        
        output_dir = Path("/data/uploads/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"verbale_{verbale['tipo']}_{contratto['codice_contratto'] if contratto else 'unknown'}_{date.today().isoformat()}.pdf"
        
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"path": str(output_path), "size": len(pdf_bytes)}
    
    return asyncio.get_event_loop().run_until_complete(run())


@celery_app.task(name='tasks.reports.generate_pagamenti_pdf')
def generate_pagamenti_pdf(periodo_da: str = None, periodo_a: str = None, immobile_id: str = None) -> dict:
    """Generate PDF report for payments."""
    async def run():
        db = get_db()
        
        query = {}
        if periodo_da:
            query["periodo"] = {"$gte": periodo_da}
        if periodo_a:
            if "periodo" not in query:
                query["periodo"] = {}
            query["periodo"]["$lte"] = periodo_a
        
        rate = await db.rate.find(query, {"_id": 0}).sort("periodo", 1).to_list(10000)
        
        # Filter by immobile if specified
        if immobile_id:
            unita_ids = [u["id"] async for u in db.unita.find({"immobile_id": immobile_id}, {"id": 1})]
            contratto_ids = [c["id"] async for c in db.contratti.find({"unita_id": {"$in": unita_ids}}, {"id": 1})]
            rate = [r for r in rate if r["contratto_id"] in contratto_ids]
        
        # Enrich with contract/tenant info
        for r in rate:
            contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
            if contratto:
                r["contratto_codice"] = contratto.get("codice_contratto")
                affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
                r["affittuario_nome"] = affittuario["nome"] if affittuario else "N/A"
        
        # Calculate totals
        totale = sum(r["importo"] for r in rate)
        incassato = sum(r["importo"] for r in rate if r["stato"] == "incassato")
        in_ritardo = sum(r["importo"] for r in rate if r["stato"] == "in_ritardo")
        
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
        
        pdf_bytes = generate_pdf_from_html(html_content)
        
        output_dir = Path("/data/uploads/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"report_pagamenti_{date.today().isoformat()}.pdf"
        
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"path": str(output_path), "size": len(pdf_bytes)}
    
    return asyncio.get_event_loop().run_until_complete(run())
