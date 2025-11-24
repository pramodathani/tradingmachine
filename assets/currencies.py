from assets.exceptions import *
from assets.instruments import *

class CurrencyFutures(Futures):
    """
    CurrencyFutures class encapsulates the functionality of a currency futures contract.
    """

    def __init__(self, id):
        """
        CurrencyFutures class encapsulates the functionality of a currency futures contract.

        - `id`: ID of the currency futures contract. Format: `exchange:tradingsymbol`.
        """
        underlying_asset = None
        super().__init__(id=id, underlying_asset=underlying_asset)
        
        if self.segment not in ['BCD-FUT', 'CDS-FUT']:
            raise CurrencyFuturesException('Instrument is not a currency futures contract.')
        
    def __repr__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"CurrencyFutures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"CurrencyFutures(id=\"{self._id}\")"

class CurrencyOption(Option):
    """
    CurrencyOption class encapsulates the functionality of a currency option contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        CurrencyOption class encapsulates the functionality of a currency option contract.

        - `id`: ID of the currency option contract. Format: `exchange:tradingsymbol`.
        - `underlying_asset`: Underlying asset for the currency call option contract. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)

        if self.segment not in ['BCD-OPT', 'CDS-OPT']:
            raise CurrencyOptionException('Instrument is not a currency call option contract.')

    def __repr__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"CurrencyOption(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"CurrencyOption(id=\"{self._id}\")"
