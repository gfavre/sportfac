import re
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from django.core.cache import cache


if TYPE_CHECKING:
    from .models import FamilyUser  # only used for type hints

IS_INSTRUCTOR_CACHE_TTL = 7200  # 2h
UPDATABLE_CHILDREN_CACHE_TTL = 3600  # 1h


def cached_user_property(name: str, ttl: int = 3600) -> Callable:
    """
    Decorator to cache a per-user property with a TTL.

    Args:
        name: Unique key name (e.g. 'is_instructor').
        ttl: Time to live in seconds.

    Usage:
        @cached_user_property("is_instructor", ttl=600)
        def is_instructor(user):
            ...
    """

    def decorator(func: Callable[["FamilyUser"], Any]) -> Callable[["FamilyUser"], Any]:
        @wraps(func)
        def wrapper(user: "FamilyUser") -> Any:
            cache_key = f"user:{user.pk}:{name}"
            if (val := cache.get(cache_key)) is not None:
                return val
            val = func(user)
            cache.set(cache_key, val, ttl)
            return val

        return wrapper

    return decorator


def invalidate_user_cache(user_id: int, *keys: str) -> None:
    for key in keys:
        cache.delete(f"user:{user_id}:{key}")


@cached_user_property("is_instructor", ttl=7200)
def is_instructor(user: "FamilyUser") -> bool:
    return user.coursesinstructors_set.exists()


@cached_user_property("updatable_children", ttl=3600)
def updatable_children_count(user: "FamilyUser") -> int:
    from registrations.models import Child

    return user.children.filter(status=Child.STATUS.imported).count()


def get_street_and_number(address: str) -> (str, str):
    # Remove email addresses
    address = re.sub(r"\S+@\S+", "", address)
    # Remove postal code pattern if present at the end
    address = re.sub(r"\d{4}\s+\w+\s*$", "", address)

    # Remove newline and carriage return characters
    address = address.replace("\n", " ").replace("\r", " ").replace("  ", " ")

    # Extract and remove the street number if present at the end
    number_match_end = re.search(r"(\d+-?\w*)\s*(,|$)", address)
    number_match_start = re.search(r"^(\d+-?\w*)\s*", address)

    street_number = None
    if number_match_end:
        street_number = number_match_end.group(1)
        address = re.sub(r"\d+-?\w*\s*(,|$)", "", address)
    elif number_match_start:
        street_number = number_match_start.group(1)
        address = re.sub(r"^\d+-?\w*\s*", "", address)

    # Remove trailing comma if present
    address = re.sub(r",$", "", address).strip()
    return address, street_number or ""


def can_impersonate(request):
    if not request.user.is_authenticated:
        return False
    return request.user.is_superuser or request.user.is_staff or request.user.is_manager


# TODO: MOVE THIS TO TESTS
test = """
# Example usage:
addresses = [
    "Rue de l'Union 20 , 1800 vevey",
    "12 Avenue de Corsier",
    'Av.De.Gilamont.64 \r\n1800 Vevey',
    'Rue des Moulins 18\r\n1800 Vevey',
    'Avenue du General Guisan 27-B',
    'Rue du conseil',
    'Chemin de Pomey 14a',
     "C/O EVAM\nAvenue de la Prairie 9A\n (Foyer Providence)"
]

for addr in addresses:
    clean_address, street_number = clean_street_address(addr)
    print(f"Original: {addr}")
    print(f"Clean Address: {clean_address}")
    print(f"Street Number: {street_number}\n")

"""
