from django.utils import timezone  
from decimal import Decimal
import requests
from decouple import config
from orders.models import ExchangeRate

class BanxicoClient:

    @staticmethod
    def fetch_rate() -> Decimal:
        """Responsabilidad: hablar con la API de Banxico"""
        url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
        response = requests.get(url, headers={"Bmx-Token": config('CONSULT_BMX_TOKEN')}, timeout=3)
        dato = response.json()['bmx']['series'][0]['datos'][0]['dato']
        return Decimal(dato)

class CurrencyService:
    
    @staticmethod
    def get_usd_rate() -> Decimal:
        """Responsabilidad: obtener el rate vigente con fallback"""
        try:
            rate = BanxicoClient.fetch_rate()
            ExchangeRate.objects.update_or_create(
                id=1,  
                defaults={
                    'usd_to_mxn': rate,
                    'fetched_at': timezone.now()
                }
            )            
            return rate
        except Exception:
            return ExchangeRate.objects.latest('fetched_at').usd_to_mxn

    @staticmethod
    def convert(amount: Decimal, to_currency: str, rate: Decimal) -> Decimal:
        """Responsabilidad: hacer la conversión"""
        if to_currency == 'USD' and rate:
            return round(amount / rate, 2)
        return amount

