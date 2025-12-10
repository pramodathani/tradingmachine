from assets.exceptions import *
from assets.instruments import *

class Equity(TradeableInstrument):
    """
    Equity class encapsulates the functionality of an equity instrument.
    """

    def __init__(self, id):
        """
        Equity class encapsulates the functionality of an equity instrument.
        
        - `id`: ID of the equity instrument. Format: `exchange:tradingsymbol`.
        """
        super().__init__(id=id)
        
        if self.exchange not in ['NSE', 'BSE']:
            raise InstrumentException(f"Instrument {id} is not an equity instrument.")

    def __repr__(self):
        """
        Returns a string representation of the equity instrument.
        """
        return f"Equity(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity instrument.
        """
        return f"Equity(id=\"{self._id}\")"
 
    @property
    def holdings(self):
        """
        Get holdings.
        """
        holdings = self._zerodha_rest_api.get(url="https://api.kite.trade/portfolio/holdings")['data']
        if holdings is None or len(holdings) == 0:
            return None

        holdings = pd.DataFrame(holdings)
        holdings = holdings[(holdings['exchange'] == self.exchange) & (holdings['tradingsymbol'] == self.tradingsymbol)]
        
        if holdings.empty:
            return None
        
        holdings.reset_index(inplace=True, drop=True)
        return holdings

    @property
    def holdings_value(self):
        """
        Get the value of the holdings in the equity instrument.
        """
        holdings = self.holdings
        if holdings is None or holdings.empty:
            return None

        return holdings.loc[0, 'last_price'] * holdings.loc[0, 'quantity']

    @property
    def holdings_pnl(self):
        """
        Get the pnl of the holdings in the equity instrument
        """
        holdings = self.holdings
        if holdings is None or holdings.empty:
            return None

        return holdings.loc[0, 'pnl']

    def add_to_holdings(self, quantity=1, price=None, variety='regular'):
        """
        Add to holdings. This assumes that requisite funds/margin are available.

        - `quantity`: Quantity.
        - `price`: Price at which to buy. If not specified, the current market price is used.
        - `variety`: Order variety. {regular, bo, co, amo}
        """
        if price is None:
            order_id = self.buy_at_market_price(quantity=quantity, product='CNC')
        else:
            order_id = self.buy_at_limit_price(quantity=quantity, price=price, variety=variety, product='CNC')
        return order_id

    def reduce_holdings(self, quantity=1, price=None, variety='regular'):
        """
        Reduce holdings.

        - `quantity`: Quantity to sell.
        - `price`: Price at which to sell. If not specified, the current market price is used.
        - `variety`: Order variety. {regular, bo, co, amo}
        """        
        holdings = self.holdings
        if holdings is None or holdings.empty:
            raise InstrumentException(f"No holdings found for {self.id}.") 

        if holdings.loc[0, 'quantity'] < quantity:
            raise InstrumentException(f"Insufficient holdings found for {self.id}.")

        if price is None:
            order_id = self.sell_at_market_price(quantity=quantity, product=holdings['product'][0])
        else:
            order_id = self.sell_at_limit_price(quantity=quantity, price=price, variety=variety, product='CNC')
        return order_id

    def liquidate_holdings(self, price=None, variety='regular'):
        """
        Liquidate holdings.
        """
        holdings = self.holdings
        if holdings is None or holdings.empty:
            raise InstrumentException(f"No holdings found for {self.id}.")

        if price is None:
            order_id = self.sell_at_market_price(quantity=holdings['quantity'][0], product=holdings['product'][0])
        else:
            order_id = self.sell_at_limit_price(quantity=holdings['quantity'][0], price=price, variety=variety, product='CNC')
        return order_id

class EquityFutures(Futures):
    """
    EquityFutures class encapsulates the functionality of an equity futures contract.
    """    

    def __init__(self, id):
        """
        EquityFutures class encapsulates the functionality of an equity futures contract.

        - `id`: ID of the equity futures contract. Format: `exchange:tradingsymbol`.
        """
        obj = Instrument(id=id)
        underlying_asset = Equity(id=f"NSE:{obj.name}")
        super().__init__(id=id, underlying_asset=underlying_asset)
        

        if self.segment != 'NFO-FUT':
            raise EquityFuturesException(f"Instrument {id} is not an equity futures contract.")

    def __repr__(self):
        """
        Returns a string representation of the equity futures contract.
        """
        return f"EquityFutures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity futures contract.
        """
        return f"EquityFutures(id=\"{self._id}\")"
 
class EquityOption(Option):
    """
    EquityOption class encapsulates the functionality of an equity options contract.
    """
    
    def __init__(self, id):
        """
        EquityOption class encapsulates the functionality of an equity option.

        - `id`: ID of the equity call option. Format: `exchange:tradingsymbol`.
        """
        obj = Instrument(id=id)
        underlying_asset = Equity(id=f"NSE:{obj.name}")
        super().__init__(id=id, underlying_asset=underlying_asset)
        
        if self.segment != 'NFO-OPT':
            raise EquityOptionException(f"Instrument {id} is not a equity option.")

    def __repr__(self):
        """
        Returns a string representation of the equity futures option.
        """
        return f"EquityOption(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity futures option.
        """
        return f"EquityOption(id=\"{self._id}\")"


class EquityIndex(Index):
    """
    EquityIndex class encapsulates the functionality of an equity index.
    """

    def __init__(self, id):
        """
        EquityIndex class encapsulates the functionality of an equity index.
        
        - `id`: ID of the equity index. Format: `exchange:tradingsymbol`.
        """
        super().__init__(id=id)

        if self.exchange not in ['NSE', 'BSE']:
            raise EquityIndexException(f"Instrument {id} is not an equity index.")

    def __repr__(self):
        """
        Returns a string representation of the equity index.
        """
        return f"EquityIndex(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity index.
        """
        return f"EquityIndex(id=\"{self._id}\")"

class EquityIndexFutures(IndexFutures):
    """
    EquityIndexFutures class encapsulates the functionality of an equity index futures contract
    """

    def __init__(self, id):
        """
        EquityIndexFutures class encapsulates the functionality of an equity index futures contract
        
        - `id`: ID of the equity index futures contract. Format: `exchange:tradingsymbol`.
        """
        obj = Instrument(id=id)
        underlying_asset = EquityIndex(id=f"NSE:{obj.name}")
        super().__init__(id=id, underlying_asset=underlying_asset)
        if self.exchange != 'NFO' or self.underlying.segment != 'INDICES':
            raise EquityIndexFuturesException(f"Instrument {id} is not an equity index futures contract.")

    def __repr__(self):
        """
        Returns a string representation of the equity index futures contract.
        """
        return f"EquityIndexFutures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity index futures contract.
        """
        return f"EquityIndexFutures(id=\"{self._id}\")"

class EquityIndexOption(IndexOption):
    """
    EquityIndexOption class encapsulates the functionality of an equity index option.
    """

    def __init__(self, id):
        """
        EquityIndexOption class encapsulates the functionality of an equity index option.
        
        - `id`: ID of the equity index call option. Format: `exchange:tradingsymbol`.
        """
        obj = Instrument(id=id)
        underlying_asset = EquityIndex(id=f"NSE:{obj.name}")
        super().__init__(id=id, underlying_asset=underlying_asset)
        if self.segment != 'NFO-OPT' or self.underlying.segment != 'INDICES':
            raise EquityIndexOptionException(f"Instrument {id} is not an equity index option.")

    def __repr__(self):
        """
        Returns a string representation of the equity index option.
        """
        return f"EquityIndexOption(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the equity index option.
        """
        return f"EquityIndexOption(id=\"{self._id}\")"
