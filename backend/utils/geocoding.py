import aiohttp
import asyncio
from typing import Optional, Tuple
import os
import logging

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "EstateWise/1.0 (property-management-app)"

# Simple in-memory cache (in production use Redis)
_geocode_cache: dict = {}


async def geocode_address(address: str) -> Optional[Tuple[float, float, str]]:
    """
    Geocode an address using Nominatim.
    Returns (lat, lon, accuracy) or None if not found.
    """
    # Check cache first
    cache_key = address.lower().strip()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }
            headers = {"User-Agent": USER_AGENT}
            
            # Respect Nominatim rate limit (1 req/sec)
            await asyncio.sleep(1.1)
            
            async with session.get(NOMINATIM_URL, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        result = data[0]
                        lat = float(result["lat"])
                        lon = float(result["lon"])
                        accuracy = result.get("type", "unknown")
                        
                        # Cache the result
                        _geocode_cache[cache_key] = (lat, lon, accuracy)
                        
                        return (lat, lon, accuracy)
                else:
                    logger.warning(f"Geocoding failed with status {response.status}")
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    
    return None


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Reverse geocode coordinates to address.
    """
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json"
            }
            headers = {"User-Agent": USER_AGENT}
            
            await asyncio.sleep(1.1)
            
            url = "https://nominatim.openstreetmap.org/reverse"
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("display_name")
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")
    
    return None
