class TradingMachineException(Exception):
    """
    Trading Machine Exception class represents all trading machine related errors. Default code is 1000.
    """

    def __init__(self, message, code=1000):
        """
        Trading Machine Exception class represents all trading machine related errors. Default code is 1000.

        -`message`: (string) error text
        -`code`: error code
        """
        super(TradingMachineException, self).__init__(message)
        self.code = code

class InstrumentException(TradingMachineException):
    """
    Instrument Exception class represents an error that occurs while interacting with the instrument.
    """

    def __init__(self, message, code=1500):
        """
        Instrument Exception class represents an error that occurs while interacting with the instrument.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(InstrumentException, self).__init__(message)
        self.code = code

class TradeableInstrumentException(TradingMachineException):
    """
    Tradeable Instrument Exception class represents an error that occurs while interacting with the tradeable instrument.
    """

    def __init__(self, message, code=1501):
        """
        Instrument Exception class represents an error that occurs while interacting with the tradeable instrument.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(TradeableInstrumentException, self).__init__(message)
        self.code = code

class NonTradeableInstrumentException(TradingMachineException):
    """
    Non Tradeable Instrument Exception class represents an error that occurs while interacting with the non tradeable instrument.
    """

    def __init__(self, message, code=1502):
        """
        Instrument Exception class represents an error that occurs while interacting with the non tradeable instrument.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(TradeableInstrumentException, self).__init__(message)
        self.code = code


class FuturesException(TradingMachineException):
    """
    Equity Exception class represents an error that occurs while interacting with a futures contract.
    """

    def __init__(self, message, code=1503):
        """
        Equity Exception class represents an error that occurs while interacting with a futures contract.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(FuturesException, self).__init__(message)
        self.code = code

class OptionException(TradingMachineException):
    """
    Option Exception class represents an error that occurs while interacting with an option.
    """

    def __init__(self, message, code=1504):
        """
        Option Exception class represents an error that occurs while interacting with an option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(OptionException, self).__init__(message)
        self.code = code


class IndexException(TradingMachineException):
    """
    Index Exception class represents an error that occurs while interacting with an index.
    """

    def __init__(self, message, code=1505):
        """
        Index Exception class represents an error that occurs while interacting with an index.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(FuturesException, self).__init__(message)
        self.code = code

class IndexFuturesException(TradingMachineException):
    """
    Index Futures Exception class represents an error that occurs while interacting with an index futures contract.
    """

    def __init__(self, message, code=1506):
        """
        Index Futures Exception class represents an error that occurs while interacting with an index futures contract.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(IndexFuturesException, self).__init__(message)
        self.code = code

class IndexOptionException(TradingMachineException):
    """
    Index Option Exception class represents an error that occurs while interacting with an index option.
    """

    def __init__(self, message, code=1507):
        """
        Index Option Exception class represents an error that occurs while interacting with an index option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(IndexOptionException, self).__init__(message)
        self.code = code


class EquityException(TradingMachineException):
    """
    Equity Exception class represents an error that occurs while interacting with an equity.
    """

    def __init__(self, message, code=1601):
        """
        Equity Exception class represents an error that occurs while interacting with an equity.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityException, self).__init__(message)
        self.code = code
        
class EquityFuturesException(InstrumentException):
    """
    Equity Futures Exception class represents an error that occurs while interacting with an equity futures.
    """

    def __init__(self, message, code=1602):
        """
        Equity Futures Exception class represents an error that occurs while interacting with an equity futures.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityFuturesException, self).__init__(message)
        self.code = code

class EquityOptionException(InstrumentException):
    """
    Equity Option Exception class represents an error that occurs while interacting with an equity option.
    """

    def __init__(self, message, code=1603):
        """
        Equity Option Exception class represents an error that occurs while interacting with an equity option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityOptionException, self).__init__(message)
        self.code = code


class EquityIndexException(InstrumentException):
    """
    Equity Index Exception class represents an error that occurs while interacting with an equity index.    
    """

    def __init__(self, message, code=1611):
        """
        Equity Index Exception class represents an error that occurs while interacting with an equity index.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityIndexException, self).__init__(message)
        self.code = code

class EquityIndexFuturesException(InstrumentException):
    """
    Equity Index Futures Exception class represents an error that occurs while interacting with an equity index futures contract.
    """

    def __init__(self, message, code=1612):
        """
        Equity Index Futures Exception class represents an error that occurs while interacting with an equity index futures contract.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityIndexFuturesException, self).__init__(message)
        self.code = code

class EquityIndexOptionException(EquityException):
    """
    Equity Index Option Exception class represents an error that occurs while interacting with an equity index option.
    """

    def __init__(self, message, code=1613):
        """
        Equity Index Option Exception class represents an error that occurs while interacting with an equity index option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(EquityIndexOptionException, self).__init__(message)
        self.code = code


class CommodityIndexException(InstrumentException):
    """
    Commodity Index Exception class represents an error that occurs while interacting with a commodity index.
    """

    def __init__(self, message, code=1701):
        """
        Commodity Index Exception class represents an error that occurs while interacting with a commodity index.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(CommodityIndexException, self).__init__(message)
        self.code = code

class CommodityFuturesException(InstrumentException):
    """
    Commodity Futures Exception class represents an error that occurs while interacting with a commodity futures.
    """

    def __init__(self, message, code=1702):
        """
        Commodity Futures Exception class represents an error that occurs while interacting with a commodity futures.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(CommodityFuturesException, self).__init__(message)
        self.code = code

class CommodityOptionException(InstrumentException):
    """
    Commodity Option Exception class represents an error that occurs while interacting with a commodity option.
    """

    def __init__(self, message, code=1703):
        """
        Commodity Call Option Exception class represents an error that occurs while interacting with a commodity call option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(CommodityOptionException, self).__init__(message)
        self.code = code


class CurrencyFuturesException(InstrumentException):
    """
    Currency Futures Exception class represents an error that occurs while interacting with currency futures.
    """

    def __init__(self, message, code=1801):
        """
        Currency Futures Exception class represents an error that occurs while interacting with currency futures.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(CurrencyFuturesException, self).__init__(message)
        self.code = code

class CurrencyOptionException(InstrumentException):
    """
    Currency Option Exception class represents an error that occurs while interacting with currency option.
    """

    def __init__(self, message, code=1802):
        """
        Currency Option Exception class represents an error that occurs while interacting with currency option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(CurrencyOptionException, self).__init__(message)
        self.code = code


class FixedIncomeException(InstrumentException):
    """
    Fixed Income Exception class represents an error that occurs while interacting with fixed income.
    """

    def __init__(self, message, code=1901):
        """
        Fixed Income Exception class represents an error that occurs while interacting with fixed income.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(FixedIncomeException, self).__init__(message)
        self.code = code

class FixedIncomeFuturesException(InstrumentException):
    """
    Fixed Income Futures Exception class represents an error that occurs while interacting with fixed income futures.
    """

    def __init__(self, message, code=1901):
        """
        Fixed Income Futures Exception class represents an error that occurs while interacting with fixed income futures.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(FixedIncomeFuturesException, self).__init__(message)
        self.code = code

class FixedIncomeOptionException(InstrumentException):
    """
    Fixed Income Option Exception class represents an error that occurs while interacting with fixed income option.
    """

    def __init__(self, message, code=1902):
        """
        Fixed Income Option Exception class represents an error that occurs while interacting with fixed income option.

        -`message`: The error message.
        -`code`: The error code.
        """        
        super(FixedIncomeOptionException, self).__init__(message)
        self.code = code
