import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional, Dict, Any
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@estatewise.local")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

# Setup Jinja2 templates
templates_path = Path(__file__).parent.parent / "templates"
if templates_path.exists():
    jinja_env = Environment(
        loader=FileSystemLoader(str(templates_path)),
        autoescape=select_autoescape(['html', 'xml'])
    )
else:
    jinja_env = None


async def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None
) -> bool:
    """
    Send an email via SMTP.
    Returns True if successful, False otherwise.
    """
    if not SMTP_HOST or not SMTP_USER:
        logger.warning(f"SMTP not configured. Would send email to {to_email}: {subject}")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = SMTP_FROM
        message["To"] = to_email
        message["Subject"] = subject
        
        if body_text:
            message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=SMTP_USE_TLS
        )
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def render_email_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Render an email template with the given context.
    """
    if jinja_env is None:
        # Fallback to simple formatting
        return f"<html><body>{context}</body></html>"
    
    try:
        template = jinja_env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render template {template_name}: {e}")
        return f"<html><body>Errore nel rendering del template</body></html>"


# Pre-built email templates
async def send_scadenza_contratto_email(
    to_email: str,
    contratto_codice: str,
    giorni_rimanenti: int,
    affittuario_nome: str,
    immobile_titolo: str
) -> bool:
    """Send contract expiration reminder."""
    subject = f"⚠️ Scadenza Contratto {contratto_codice} - {giorni_rimanenti} giorni"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #0F172A;">Promemoria Scadenza Contratto</h2>
        <p>Il contratto <strong>{contratto_codice}</strong> scadrà tra <strong>{giorni_rimanenti} giorni</strong>.</p>
        <table style="border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Affittuario:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{affittuario_nome}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Immobile:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{immobile_titolo}</td></tr>
        </table>
        <p>Accedi a EstateWise per gestire il rinnovo o la chiusura del contratto.</p>
        <p style="color: #666; font-size: 12px;">Questo è un messaggio automatico generato da EstateWise.</p>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html)


async def send_rata_ritardo_email(
    to_email: str,
    contratto_codice: str,
    periodo: str,
    giorni_ritardo: int,
    importo: float,
    affittuario_nome: str
) -> bool:
    """Send payment delay notification."""
    urgenza = "🔴 URGENTE" if giorni_ritardo > 7 else "⚠️ Avviso"
    subject = f"{urgenza} - Rata in ritardo {contratto_codice} ({periodo})"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: {'#EF4444' if giorni_ritardo > 7 else '#F59E0B'};">Pagamento in Ritardo</h2>
        <p>La rata del contratto <strong>{contratto_codice}</strong> risulta in ritardo di <strong>{giorni_ritardo} giorni</strong>.</p>
        <table style="border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Periodo:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{periodo}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Importo:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">€ {importo:,.2f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Affittuario:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{affittuario_nome}</td></tr>
        </table>
        <p style="color: #666; font-size: 12px;">Questo è un messaggio automatico generato da EstateWise.</p>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html)


async def send_evento_critico_email(
    to_email: str,
    tipo_evento: str,
    gravita: str,
    descrizione: str,
    affittuario_nome: str,
    immobile_titolo: str
) -> bool:
    """Send critical event notification."""
    subject = f"🚨 Evento Critico - {tipo_evento.replace('_', ' ').title()}"
    
    color = "#EF4444" if gravita == "alta" else "#F59E0B" if gravita == "media" else "#3B82F6"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: {color};">Evento Critico Registrato</h2>
        <p><strong>Tipo:</strong> {tipo_evento.replace('_', ' ').title()}</p>
        <p><strong>Gravità:</strong> <span style="color: {color}; text-transform: uppercase;">{gravita}</span></p>
        <table style="border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Affittuario:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{affittuario_nome}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Immobile:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{immobile_titolo}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Descrizione:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{descrizione}</td></tr>
        </table>
        <p>È richiesta attenzione immediata.</p>
        <p style="color: #666; font-size: 12px;">Questo è un messaggio automatico generato da EstateWise.</p>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html)
