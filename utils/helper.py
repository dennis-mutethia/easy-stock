import hashlib


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

    @staticmethod
    def get_provider(phone_number):
        """
        Determine the network provider for a Kenyan mobile number.
        
        Args:
        number (str): A Kenyan mobile number without
        
        Returns:
        str: 'mpesa' or 'atl' based on the prefix.
        
        Raises:
        ValueError: If the number is invalid or belongs to another provider.
        """
        
        prefix = phone_number[-9:][:3]
        
        safaricom_prefixes = {
            '701', '702', '703', '704', '705', '706', '707', '708',
            '710', '711', '712', '713', '714', '715', '716', '717', '718', '719',
            '720', '721', '722', '723', '724', '725', '726', '727', '728', '729',
            '740', '741', '742', '743', '745', '746', '748',
            '757', '758', '759',
            '768', '769',
            '790', '791', '792', '793', '794', '795', '796', '797', '798', '799',
            '110', '111', '112', '113', '114', '115'
        }
        
        airtel_prefixes = {
            '730', '731', '732', '733', '734', '735', '736', '737', '738', '739',
            '750', '751', '752', '753', '754', '755', '756',
            '762', '767',
            '780', '781', '782', '785', '786', '787', '788', '789',
            '100', '101', '102', '103', '104', '105', '106', '107', '108'
        }
        
        if prefix in safaricom_prefixes:
            return 'mpesa'
        elif prefix in airtel_prefixes:
            return 'atl'
        else:
            raise ValueError(f"Unknown network for prefix {prefix}")
