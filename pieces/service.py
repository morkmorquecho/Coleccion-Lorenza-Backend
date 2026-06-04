from django.utils import timezone  
from decimal import Decimal
import requests
from decouple import config
from orders.models import ExchangeRate
from django.core.cache import cache

class BanxicoClient:

    @staticmethod
    def fetch_rate() -> Decimal:
        """Responsabilidad: hablar con la API de Banxico"""
        url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
        response = requests.get(url, headers={"Bmx-Token": config('CONSULT_BMX_TOKEN')}, timeout=3)
        dato = response.json()['bmx']['series'][0]['datos'][0]['dato']
        return Decimal(dato)


EXCHANGE_RATE_CACHE_KEY = 'usd_to_mxn_rate'
EXCHANGE_RATE_CACHE_TTL = 60 * 60 * 24 

class CurrencyService:
    
    @staticmethod
    def get_usd_rate() -> Decimal:
        """Obtiene el rate vigente: cache → Banxico → BD (fallback)"""

        # 1. Intentar desde cache (evita llamada a Banxico y a la BD)
        cached_rate = cache.get(EXCHANGE_RATE_CACHE_KEY)
        if cached_rate is not None:
            return Decimal(cached_rate)

        # 2. Cache miss: buscar en Banxico y persistir
        try:
            rate = BanxicoClient.fetch_rate()
            ExchangeRate.objects.update_or_create(
                id=1,
                defaults={
                    'usd_to_mxn': rate,
                    'fetched_at': timezone.now()
                }
            )
            cache.set(EXCHANGE_RATE_CACHE_KEY, str(rate), EXCHANGE_RATE_CACHE_TTL)
            return rate

        # 3. Fallback: Banxico falló, usar el último rate guardado en BD
        except Exception:
            rate = ExchangeRate.objects.latest('fetched_at').usd_to_mxn
            # También cachear el fallback para no golpear la BD en cada error
            cache.set(EXCHANGE_RATE_CACHE_KEY, rate, EXCHANGE_RATE_CACHE_TTL)
            return rate

