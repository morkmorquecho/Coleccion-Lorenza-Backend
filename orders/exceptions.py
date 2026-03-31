class OrderError(Exception):
    """Clase base para todos los errores de órdenes"""
    pass

class OrderNotCancellableError(OrderError):
    """Cuando intentas cancelar una orden que no se puede cancelar"""
    pass

class RefundError(OrderError):
    """Cuando falla el reembolso en Stripe"""
    pass