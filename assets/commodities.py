from assets.instruments import *

class CommodityIndex(Index):
    """
    CommodityIndex class encapsulates the functionality of a commodity index.
    """

    def __init__(self, id):
        """
        CommodityIndex class encapsulates the functionality of a commodity index.

        - `id`: ID of the commodity index. Format: `exchange:tradingsymbol`.
        """
        super().__init__(id=id)

        if self.exchange not in ['MCX']:
            raise CommodityIndexException(f"Invalid exchange {self.exchange} for commodity index.")
        
    def __repr__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityIndex(id=\"{self._id}\")"

    def __str__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityIndex(id=\"{self._id}\")"

class CommodityFutures(Futures):
    """
    CommodityFutures class encapsulates the functionality of a commodity futures contract.
    """

    def __init__(self, id):
        """
        CommodityFutures class encapsulates the functionality of a commodity futures contract.

        - `id`: ID of the commodity futures contract. Format: `exchange:tradingsymbol`.
        """
        underlying_asset = None
        super().__init__(id=id, underlying_asset=underlying_asset)

        if self.segment != 'MCX-FUT':
            raise CommodityFuturesException(f'Instrument is not a commodity futures contract: {id}.')

    def __repr__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityFutures(id=\"{self._id}\")"

    def __str__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityFutures(id=\"{self._id}\")"

class CommodityOption(Option):
    """
    CommodityOption class encapsulates the functionality of a commodity option contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        CommodityOption class encapsulates the functionality of a commodity option contract.

        - `id`: ID of the commodity option contract. Format: `exchange:tradingsymbol`.
        - `underlying_asset`: Underlying asset for the commodity call option contract. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)

        if self.segment != 'MCX-OPT':
            raise CommodityOptionException(f'Instrument is not a commodity option contract: {id}.')

    def __repr__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityOption(id=\"{self._id}\")"

    def __str__(self):
        """
        Returns a string representation of the commodity index.
        """
        return f"CommodityOption(id=\"{self._id}\")"
