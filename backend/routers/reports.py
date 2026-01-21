from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import io

from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/reports", tags=["Report"])


@router.get("/pagamenti")
async def report_pagamenti(
    periodo_da: Optional[str] = None,  # YYYY-MM
    periodo_a: Optional[str] = None,
    immobile_id: Optional[str] = None,
    formato: str = Query("json", enum=["json", "csv", "excel"]),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Report pagamenti."""
    query = {}
    if periodo_da:
        query["periodo"] = {"$gte": periodo_da}
    if periodo_a:
        if "periodo" not in query:
            query["periodo"] = {}
        query["periodo"]["$lte"] = periodo_a
    
    rate = await db.rate.find(query, {"_id": 0}).sort("periodo", 1).to_list(10000)
    
    # Filter by immobile if needed
    if immobile_id:
        unita_ids = [u["id"] async for u in db.unita.find({"immobile_id": immobile_id}, {"id": 1})]
        contratto_ids = [c["id"] async for c in db.contratti.find({"unita_id": {"$in": unita_ids}}, {"id": 1})]
        rate = [r for r in rate if r["contratto_id"] in contratto_ids]
    
    # Enrich
    for r in rate:
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else ""
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1, "codice_unita": 1})
            if unita:
                r["unita_codice"] = unita["codice_unita"]
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else ""
    
    if formato == "json":
        # Calculate summary
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
            writer.writerow([
                r["periodo"],
                r.get("contratto_codice", ""),
                r.get("affittuario_nome", ""),
                r.get("immobile_titolo", ""),
                r["importo"],
                r["stato"],
                r.get("data_incasso", "")
            ])
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=report_pagamenti.csv"}
        )
    
    elif formato == "excel":
        import pandas as pd
        
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


@router.get("/immobile/{immobile_id}")
async def report_immobile(
    immobile_id: str,
    formato: str = Query("json", enum=["json", "csv", "excel"]),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Report dettagliato immobile."""
    immobile = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    # Get units
    unita_list = await db.unita.find({"immobile_id": immobile_id}, {"_id": 0}).to_list(100)
    
    # Get contracts for each unit
    for u in unita_list:
        u["contratti"] = await db.contratti.find({"unita_id": u["id"]}, {"_id": 0}).to_list(100)
        for c in u["contratti"]:
            affittuario = await db.soggetti.find_one({"id": c["affittuario_id"]}, {"nome": 1})
            c["affittuario_nome"] = affittuario["nome"] if affittuario else ""
    
    # Get expenses
    spese = await db.spese.find({"immobile_id": immobile_id}, {"_id": 0}).to_list(1000)
    totale_spese = sum(s["importo"] for s in spese)
    
    # Get income
    unita_ids = [u["id"] for u in unita_list]
    contratto_ids = [c["id"] async for c in db.contratti.find({"unita_id": {"$in": unita_ids}}, {"id": 1})]
    rate_incassate = await db.rate.find({
        "contratto_id": {"$in": contratto_ids},
        "stato": "incassato"
    }, {"_id": 0}).to_list(10000)
    totale_incassi = sum(r["importo"] for r in rate_incassate)
    
    report = {
        "immobile": immobile,
        "unita": unita_list,
        "statistiche": {
            "totale_unita": len(unita_list),
            "unita_locate": len([u for u in unita_list if u.get("contratti") and any(c["stato"] == "attivo" for c in u["contratti"])]),
            "totale_incassi": totale_incassi,
            "totale_spese": totale_spese,
            "profit_loss": totale_incassi - totale_spese
        },
        "spese_dettaglio": spese[:20]
    }
    
    if formato == "json":
        return report
    
    elif formato == "excel":
        import pandas as pd
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Immobile sheet
            pd.DataFrame([immobile]).to_excel(writer, sheet_name="Immobile", index=False)
            
            # Unita sheet
            unita_flat = [{
                "Codice": u["codice_unita"],
                "Tipo": u["tipo_immobile"],
                "MQ": u.get("mq", ""),
                "Stato": "Locata" if any(c["stato"] == "attivo" for c in u.get("contratti", [])) else "Libera"
            } for u in unita_list]
            pd.DataFrame(unita_flat).to_excel(writer, sheet_name="Unita", index=False)
            
            # Spese sheet
            pd.DataFrame(spese).to_excel(writer, sheet_name="Spese", index=False)
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=report_{immobile['codice']}.xlsx"}
        )
    
    return report


@router.get("/executive")
async def report_executive(
    anno: Optional[int] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Report executive per supervisori."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono accedere a questo report")
    
    if not anno:
        anno = date.today().year
    
    # Total properties and units
    tot_immobili = await db.immobili.count_documents({})
    tot_unita = await db.unita.count_documents({})
    
    # Active contracts
    contratti_attivi = await db.contratti.count_documents({"stato": "attivo"})
    
    # Units with active contracts
    contratti = await db.contratti.find({"stato": "attivo"}, {"unita_id": 1}).to_list(10000)
    unita_locate = len(set(c["unita_id"] for c in contratti))
    
    # Occupancy rate
    tasso_occupazione = round(unita_locate / tot_unita * 100, 1) if tot_unita > 0 else 0
    
    # Income by month
    rate = await db.rate.find({"periodo": {"$regex": f"^{anno}"}}, {"_id": 0}).to_list(100000)
    incassi_per_mese = {}
    for r in rate:
        mese = r["periodo"]
        if r["stato"] == "incassato":
            incassi_per_mese[mese] = incassi_per_mese.get(mese, 0) + r["importo"]
    
    # Expenses by month
    spese = await db.spese.find({"data": {"$regex": f"^{anno}"}}, {"_id": 0}).to_list(100000)
    spese_per_mese = {}
    for s in spese:
        mese = s["data"][:7]
        spese_per_mese[mese] = spese_per_mese.get(mese, 0) + s["importo"]
    
    # Calculate profit/loss per month
    tutti_mesi = sorted(set(list(incassi_per_mese.keys()) + list(spese_per_mese.keys())))
    profit_loss = [{
        "mese": m,
        "incassi": incassi_per_mese.get(m, 0),
        "spese": spese_per_mese.get(m, 0),
        "profit": incassi_per_mese.get(m, 0) - spese_per_mese.get(m, 0)
    } for m in tutti_mesi]
    
    # Late payments stats
    rate_ritardo = await db.rate.count_documents({"stato": "in_ritardo"})
    totale_rate_anno = len(rate)
    percentuale_insoluti = round(rate_ritardo / totale_rate_anno * 100, 1) if totale_rate_anno > 0 else 0
    
    # Contracts expiring soon
    from dateutil.relativedelta import relativedelta
    target_30 = (date.today() + relativedelta(days=30)).isoformat()
    contratti_scadenza = await db.contratti.count_documents({
        "stato": "attivo",
        "data_scadenza": {"$lte": target_30}
    })
    
    # Critical events
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
