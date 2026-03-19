import hashlib
from flask_login import current_user


class Helper():
    """Stateless utility class — all methods are static."""

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @staticmethod
    def format_number(number):
        """Return int if float is whole, otherwise return as-is."""
        if isinstance(number, float) and number.is_integer():
            return int(number)
        return number

    @staticmethod
    def format_number_with_commas(value) -> str:
        if isinstance(value, (int, float)):
            return "{:,.0f}".format(value)
        return value