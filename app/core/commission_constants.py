from decimal import Decimal

# Comissão da plataforma sobre o valor do pedido (pagamento continua direto na academia).
PLATFORM_COMMISSION_RATE = Decimal("0.03")
PLATFORM_COMMISSION_PERCENT = Decimal("3.00")

COMMISSION_STATUS_PENDING = "pending"
COMMISSION_STATUS_PAID = "paid"
