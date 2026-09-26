"""The `vwap` synthetic order type: a time-sliced order whose slice sizes follow the shape of the day's volume.

It works like a `TimeWeightedAveragePriceOrder`, but trades more where the market usually trades more, so the average paid tracks the day's volume-weighted average price.

Typical usage example:

  order = volume_weighted_average_price.VolumeWeightedAveragePriceOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=600,
      price_reference={"kind": "marketable"},
      slices=6,
      over_minutes=60.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class VolumeWeightedAveragePriceOrder(synthetic_order.SyntheticOrder):
    """A time-sliced order whose slice sizes follow the shape of the day's volume.

    It works like a `TimeWeightedAveragePriceOrder`, but trades more where the market usually trades more, so the average paid tracks the day's volume-weighted average price.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        slices: The int number of slices, from 2 to 60. The quantity must be at least this.
        over_minutes: The float number of minutes to spread the slices over. Above zero.
        volume_profile: The list of float relative weights, one per half hour from the open, none negative and adding up to more than zero, or None to let UBI use its own.
    """

    SYNTHETIC_TYPE = "vwap"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        slices: int,
        over_minutes: float,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        closes_position: bool = False,
        dry_run: bool = False,
        volume_profile: list[float] | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            slices: The int number of slices, from 2 to 60. The quantity must be at least this.
            over_minutes: The float number of minutes to spread the slices over. Above zero.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            trigger_price: The float trigger price in rupees of the order itself, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            volume_profile: The list of float relative weights, one per half hour from the open, none negative and adding up to more than zero, or None to let UBI use its own.

        Raises:
            Nothing.
        """
        super().__init__(
            instrument,
            transaction_type=transaction_type,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            validity=validity,
            disclosed_quantity=disclosed_quantity,
            after_market=after_market,
            tag=tag,
            price_reference=price_reference,
            quantity_reference=quantity_reference,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.slices = slices
        self.over_minutes = over_minutes
        self.volume_profile = volume_profile

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "slices": self.slices,
            "over_minutes": self.over_minutes,
            "volume_profile": self.volume_profile,
        }
