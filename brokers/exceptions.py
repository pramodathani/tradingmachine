class KiteException(Exception):
    """
    Base exception class representing a Kite client exception.
    Every specific Kite client exception is a subclass of this and exposes two instance variables `.code`: (HTTP error code) and `.message`: (error text).
    """

    def __init__(self, message, code=500):
        """
        Base exception class representing a Kite client exception.
        Every specific Kite client exception is a subclass of this and exposes two instance variables `.code`: (HTTP error code) and `.message`: (error text).

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """        
        super(KiteException, self).__init__(message)
        self.code = code
        self.message = message

class GeneralException(KiteException):
    """
    General Exception class represents an unclassified, general error. Default code is 500.
    """

    def __init__(self, message, code=500):
        """
        General Exception class represents an unclassified, general error. Default code is 500.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """        
        super(GeneralException, self).__init__(message, code)

class InputException(KiteException):
    """
    Input Exception class represents user input errors such as missing and invalid parameters. Default code is 400.
    """

    def __init__(self, message, code=400):
        """
        Input Exception class represents user input errors such as missing and invalid parameters. Default code is 400.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(InputException, self).__init__(message, code)

class DataException(KiteException):
    """
    Data Exception class represents a bad response from the backend Order Management System (OMS). Default code is 502.
    """

    def __init__(self, message, code=502):
        """
        Data Exception class represents a bad response from the backend Order Management System (OMS). Default code is 502.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(DataException, self).__init__(message, code)

class NetworkException(KiteException):
    """
    Network Exception class represents a network issue between Kite and the backend Order Management System (OMS). Default code is 503.
    """

    def __init__(self, message, code=503):
        """
        Network Exception class represents a network issue between Kite and the backend Order Management System (OMS). Default code is 503.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(NetworkException, self).__init__(message, code)

class UserException(KiteException):
    """
    User Exception class represents user exceptions for certain calls. Default code is 403.
    """

    def __init__(self, message, code=403):
        """
        User Exception class represents user exceptions for certain calls. Default code is 403.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(UserException, self).__init__(message, code)

class TokenException(KiteException):
    """
    Token Exception class represents all token and authentication related errors. Default code is 403.
    """

    def __init__(self, message, code=403):
        """
        Token Exception class represents all token and authentication related errors. Default code is 403.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(TokenException, self).__init__(message, code)

class PermissionException(KiteException):
    """
    Permission Exception class represents permission denied exceptions for certain calls. Default code is 403.
    """

    def __init__(self, message, code=403):
        """
        Permission Exception class represents permission denied exceptions for certain calls. Default code is 403.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(PermissionException, self).__init__(message, code)

class OrderException(KiteException):
    """
    Order Exception class represents all order placement and manipulation errors. Default code is 500.
    """

    def __init__(self, message, code=500):
        """
        Order Exception class represents all order placement and manipulation errors. Default code is 500.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(OrderException, self).__init__(message, code)

class MarginException(KiteException):
    """
    Margin Exception class represents all margin related errors. Default code is 500.
    """

    def __init__(self, message, code=500):
        """
        Margin Exception class represents all margin related errors. Default code is 500.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(MarginException, self).__init__(message, code)

class HoldingException(KiteException):
    """
    Holding Exception class represents all holding related errors. Default code is 500.
    """

    def __init__(self, message, code=500):
        """
        Holding Exception class represents all holding related errors. Default code is 500.

        -`message`: (string) error text
        -`code`: (int) HTTP error code
        """
        super(HoldingException, self).__init__(message, code)

class ZerodhaException(KiteException):
    """
    Zerodha Exception class represents all Zerodha related errors. Default code is 1000.
    """

    def __init__(self, message, code=1000):
        """
        Zerodha Exception class represents all Zerodha related errors. Default code is 1000.

        -`message`: (string) error text
        -`code`: error code
        """
        super(ZerodhaException, self).__init__(message, code)