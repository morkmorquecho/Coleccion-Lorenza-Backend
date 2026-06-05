import geoip2.database
import geoip2.errors
from django.conf import settings

REGION_NORMALIZE = {'MX': 'MX', 'US': 'US', 'CA': 'US'}

class CountryDetectionMiddleware:
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.reader = geoip2.database.Reader(settings.GEOIP_DB_PATH)

    def __call__(self, request):
        if settings.DEBUG:
            forced = request.META.get('HTTP_X_FORCE_COUNTRY')
            if forced and forced in REGION_NORMALIZE:
                request.detected_country = REGION_NORMALIZE[forced]
                return self.get_response(request)

        ip = self.get_client_ip(request)
        request.detected_country = self.get_country(ip)
        return self.get_response(request)

    def get_client_ip(self, request) -> str:
        # Cloudflare pone la IP real del cliente aquí
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            return cf_ip.strip()

        # Fallback para cuando no hay Cloudflare (dev local, etc.)
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()

        return request.META.get('REMOTE_ADDR')

    def get_country(self, ip) -> str:
        private_prefixes = ('127.', '192.168.', '10.', '::1')
        if any(ip.startswith(p) for p in private_prefixes):
            return 'MX'

        try:
            result = self.reader.country(ip)
            country = result.country.iso_code
            return country if country in ['MX', 'US'] else 'US'
        except (geoip2.errors.AddressNotFoundError, Exception):
            return 'US'