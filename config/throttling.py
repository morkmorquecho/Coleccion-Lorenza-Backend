from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class LoginThrottle(AnonRateThrottle):
    scope = 'login'

class RegisterThrottle(AnonRateThrottle):
    scope = 'register'

class SensitiveOperationThrottle(UserRateThrottle):
    scope = 'sensitive'
    

class BurstRateThrottle(UserRateThrottle):
    """
    Límite de ráfaga para prevenir ataques de fuerza bruta.
    Se aplica globalmente a todas las vistas.
    """
    scope = 'burst'
    
    def allow_request(self, request, view):
        """
        Se aplica tanto a usuarios autenticados como anónimos
        """
        return super().allow_request(request, view)
    
class RegisterValidThrottle(AnonRateThrottle):
    scope = 'register_valid'

    def allow_request(self, request, view):
        self.request = request
        return True 

    def throttle_success(self):
        if getattr(self.request, "_is_valid", False):
            return super().throttle_success()