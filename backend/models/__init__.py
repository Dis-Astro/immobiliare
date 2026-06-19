# EstateWise Models
from .user import User, UserCreate, UserUpdate, UserInDB, UserRole
from .soggetto import Soggetto, SoggettoCreate, SoggettoUpdate, TipoSoggetto
from .immobile import Immobile, ImmobileCreate, ImmobileUpdate
from .unita import Unita, UnitaCreate, UnitaUpdate, TipoImmobile, DestinazioneUso
from .contratto import Contratto, ContrattoCreate, ContrattoUpdate, StatoContratto, Periodicita, StatoDeposito
from .modello_contratto import ModelloContratto, ModelloContrattoCreate, ModelloContrattoUpdate, TipoModelloContratto, FormatoModelloContratto
from .rata import Rata, RataCreate, RataUpdate, StatoRata, MetodoPagamento
from .documento import Documento, DocumentoCreate, LivelloDocumento
from .valutazione import ValutazioneAffittuario, ValutazioneCreate, EventoCritico, EventoCriticoCreate, GravitaEvento
from .verbale import VerbaleStato, VerbaleCreate, TipoVerbale
from .variazione import VariazioneContratto, VariazioneCreate, TipoVariazione
from .spesa import SpesaImmobile, SpesaCreate, CategoriaSpesa, ImputabileA
from .intervento import InterventoManutenzione, InterventoCreate, PrioritaIntervento, StatoIntervento
from .notifica import Notifica, NotificaCreate, TipoNotifica, StatoNotifica
from .audit import AuditLog, AuditLogCreate
from .recesso import Recesso, RecessoCreate, StatoRecesso
