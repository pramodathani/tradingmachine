from assets.exceptions import *
from assets.instruments import *

class FixedIncome(TradeableInstrument):
    """
    FixedIncome class encapsulates the functionality of a fixed income instrument.
    """

    def __init__(self, id):
        """
        FixedIncome class encapsulates the functionality of a fixed income instrument.

        - `id`: ID of the fixed income instrument. Format: `exchange:tradingsymbol`.
        """
        super().__init__(id=id)

        if 'NSE' not in self.segment:
            raise FixedIncomeException(f'Instrument is not a fixed income instrument: {id}')
        
    def __repr__(self):
        """
        Returns a string representation of the fixed income instrument.
        """
        return f"FixedIncome(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the fixed income instrument.
        """
        return f"FixedIncome(id=\"{self._id}\")"

class FixedIncomeFutures(Futures):
    """
    FixedIncomeFutures class encapsulates the functionality of a fixed income futures contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        FixedIncomeFutures class encapsulates the functionality of a fixed income futures contract.

        - `id`: ID of the fixed income futures contract. Format: `exchange:tradingsymbol`.
        - `underlying_asset` is the underlying asset of the futures contract. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)

    def __repr__(self):
        """
        Returns a string representation of the fixed income futures contract.
        """
        return f"FixedIncomeFutures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the fixed income futures contract.
        """
        return f"FixedIncomeFutures(id=\"{self._id}\")"

class FixedIncomeOption(Option):
    """
    FixedIncomeOption class encapsulates the functionality of a fixed income option contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        FixedIncomeOption class encapsulates the functionality of a fixed income option contract.

        - `id`: ID of the fixed income option contract. Format: `exchange:tradingsymbol`.
        - `underlying_asset` is the underlying asset of the option contract. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)
        
        if self.segment != 'CDS-OPT':
            raise FixedIncomeOptionException(f'Instrument is not a fixed income option contract: {id}')
        
    def __repr__(self):
        """
        Returns a string representation of the fixed income option contract.
        """
        return f"FixedIncomeOption(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the fixed income option contract.
        """
        return f"FixedIncomeOption(id=\"{self._id}\")"
