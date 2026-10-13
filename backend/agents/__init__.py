from .accounting import ACCOUNTING
from .boss import BOSS
from .customer_service import CUSTOMER_SERVICE
from .facilities import FACILITIES
from .inventory import INVENTORY
from .spec import RoleSpec

ROLE_SPECS: dict[str, RoleSpec] = {s.role: s for s in (BOSS, INVENTORY, ACCOUNTING, FACILITIES, CUSTOMER_SERVICE)}
