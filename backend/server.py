from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def seed_admin_user():
    """Seed admin user if not exists."""
    from utils.auth import get_password_hash
    
    admin = await db.users.find_one({"email": "admin@estatewise.it"})
    if not admin:
        # Also delete old admin if exists
        await db.users.delete_many({"email": {"$regex": "admin@"}})
        
        admin_user = {
            "id": "admin-001",
            "email": "admin@estatewise.it",
            "nome": "Amministratore",
            "password_hash": get_password_hash("admin123"),
            "ruolo": "supervisore",
            "attivo": True,
            "must_change_password": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_user)
        logger.info("Admin user seeded: admin@estatewise.it / admin123")


async def seed_tipi_immobile():
    """Seed predefined property types."""
    tipi = [
        "appartamento", "ufficio", "negozio", "magazzino", "capannone",
        "box_auto", "posto_auto", "cantina", "terreno", "villa",
        "loft", "attico", "mansarda", "locale_commerciale", "laboratorio", "altro"
    ]
    
    existing = await db.config.find_one({"key": "tipi_immobile"})
    if not existing:
        await db.config.insert_one({"key": "tipi_immobile", "values": tipi})
        logger.info("Property types seeded")


async def seed_categorie_spesa():
    """Seed expense categories."""
    categorie = [
        "manutenzione_ordinaria", "manutenzione_straordinaria", "utenze",
        "tasse", "assicurazione", "condominio", "pulizie", "giardinaggio",
        "sicurezza", "altro"
    ]
    
    existing = await db.config.find_one({"key": "categorie_spesa"})
    if not existing:
        await db.config.insert_one({"key": "categorie_spesa", "values": categorie})
        logger.info("Expense categories seeded")


# NOTA: Scheduler in-process RIMOSSO - Usare Celery + Redis + Beat
# I task di notifica sono gestiti da: celery_app.py + tasks/notifications.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting EstateWise API...")
    await seed_admin_user()
    await seed_tipi_immobile()
    await seed_categorie_spesa()
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.soggetti.create_index("id", unique=True)
    await db.soggetti.create_index("cf")
    await db.soggetti.create_index("piva")
    await db.immobili.create_index("id", unique=True)
    await db.immobili.create_index("codice", unique=True)
    await db.unita.create_index("id", unique=True)
    await db.contratti.create_index("id", unique=True)
    await db.contratti.create_index("codice_contratto", unique=True)
    await db.rate.create_index("id", unique=True)
    await db.rate.create_index("contratto_id")
    await db.documenti.create_index("id", unique=True)
    await db.valutazioni_affittuari.create_index("id", unique=True)
    await db.eventi_critici.create_index("id", unique=True)
    await db.verbali.create_index("id", unique=True)
    await db.variazioni.create_index("id", unique=True)
    await db.spese.create_index("id", unique=True)
    await db.interventi.create_index("id", unique=True)
    await db.notifiche.create_index("id", unique=True)
    await db.notifiche.create_index("user_id")
    await db.audit_log.create_index("id", unique=True)
    await db.recessi.create_index("id", unique=True)
    
    logger.info("Database indexes created")
    
    # NOTA: Lo scheduler in-process è stato RIMOSSO.
    # Le notifiche vengono gestite da Celery + Redis + Beat
    # Avviare i servizi con: docker-compose up -d (redis, worker, beat)
    
    yield
    
    # Shutdown
    logger.info("Shutting down EstateWise API...")
    client.close()


# Create the main app
app = FastAPI(
    title="EstateWise API",
    description="API per gestione affitti immobiliari aziendali",
    version="1.0.0",
    lifespan=lifespan
)

# Create a router with the /api/v1 prefix
api_router = APIRouter(prefix="/api/v1")


# Import and include all routers
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.soggetti import router as soggetti_router
from routers.immobili import router as immobili_router
from routers.unita import router as unita_router
from routers.contratti import router as contratti_router
from routers.rate import router as rate_router
from routers.documenti import router as documenti_router
from routers.valutazioni import router as valutazioni_router
from routers.verbali import router as verbali_router
from routers.variazioni import router as variazioni_router
from routers.spese import router as spese_router
from routers.interventi import router as interventi_router
from routers.notifiche import router as notifiche_router
from routers.mappa import router as mappa_router
from routers.reports import router as reports_router
from routers.dashboard import router as dashboard_router
from routers.audit import router as audit_router

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(soggetti_router)
api_router.include_router(immobili_router)
api_router.include_router(unita_router)
api_router.include_router(contratti_router)
api_router.include_router(rate_router)
api_router.include_router(documenti_router)
api_router.include_router(valutazioni_router)
api_router.include_router(verbali_router)
api_router.include_router(variazioni_router)
api_router.include_router(spese_router)
api_router.include_router(interventi_router)
api_router.include_router(notifiche_router)
api_router.include_router(mappa_router)
api_router.include_router(reports_router)
api_router.include_router(dashboard_router)
api_router.include_router(audit_router)


# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check DB
    try:
        await db.command("ping")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    
    # Check storage
    storage_path = Path("/data/uploads")
    storage_status = "ok" if storage_path.exists() else "missing"
    
    return {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "storage": storage_status
        }
    }


# Global search endpoint
@api_router.get("/search")
async def global_search(q: str):
    """Global search across all entities."""
    from routers.auth import get_current_user, oauth2_scheme
    
    results = {
        "immobili": [],
        "unita": [],
        "contratti": [],
        "soggetti": []
    }
    
    # Search immobili
    immobili = await db.immobili.find({
        "$or": [
            {"codice": {"$regex": q, "$options": "i"}},
            {"titolo": {"$regex": q, "$options": "i"}},
            {"indirizzo": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0, "id": 1, "codice": 1, "titolo": 1}).limit(5).to_list(5)
    results["immobili"] = immobili
    
    # Search unita
    unita = await db.unita.find({
        "$or": [
            {"codice_unita": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0, "id": 1, "codice_unita": 1, "immobile_id": 1}).limit(5).to_list(5)
    results["unita"] = unita
    
    # Search contratti
    contratti = await db.contratti.find({
        "$or": [
            {"codice_contratto": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0, "id": 1, "codice_contratto": 1}).limit(5).to_list(5)
    results["contratti"] = contratti
    
    # Search soggetti
    soggetti = await db.soggetti.find({
        "$or": [
            {"nome": {"$regex": q, "$options": "i"}},
            {"cf": {"$regex": q, "$options": "i"}},
            {"piva": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0, "id": 1, "nome": 1, "tipo": 1}).limit(5).to_list(5)
    results["soggetti"] = soggetti
    
    return results


# Geocoding endpoint
@api_router.post("/geocode")
async def geocode_address(request: Request):
    """Geocode an address."""
    from utils.geocoding import geocode_address as geocode
    
    body = await request.json()
    address = body.get("address")
    
    if not address:
        return JSONResponse(status_code=400, content={"error": "Address required"})
    
    result = await geocode(address)
    if result:
        lat, lon, accuracy = result
        return {"lat": lat, "lon": lon, "accuracy": accuracy}
    
    return JSONResponse(status_code=404, content={"error": "Address not found"})


# Include the router in the main app
app.include_router(api_router)

# Also include under /api for backward compatibility
api_compat = APIRouter(prefix="/api")

@api_compat.get("/")
async def root():
    return {"message": "EstateWise API v1.0", "docs": "/docs"}

app.include_router(api_compat)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
