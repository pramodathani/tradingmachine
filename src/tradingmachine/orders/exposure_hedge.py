"""The `exposure_hedge` synthetic order type: a hedge traded whenever the account's net exposure leaves a band.

UBI adds up the net positions of the watched instruments, each weighted by its exposure per unit, and when the total leaves the band between `lower_band` and `upper_band` it trades the hedge instrument to bring it back. UBI has no option pricing model, so the delta of an option is the caller's to supply as its exposure per unit. UBI decides the side and the quantity of every hedge, and never resolves price or quantity references for this type.

Typical usage example:

  order = exposure_hedge.ExposureHedgeOrder(
      nifty_future,
      watched=[
          exposure_watch.ExposureWatch(nifty_call, exposure_per_unit=0.5),
          exposure_watch.ExposureWatch(nifty_put, exposure_per_unit=-0.4),
      ],
      lower_band=-75.0,
      upper_band=75.0,
      product="nrml",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import exposure_watch
from tradingmachine.orders import synthetic_order


class ExposureHedgeOrder(synthetic_order.SyntheticOrder):
    """A standing instruction to trade one hedge instrument whenever the watched instruments' net exposure leaves a band.

    The instrument it is built on is the hedge, which is what it trades. UBI works out the side and the quantity of each hedge from the exposure, so the template carries placeholders for them. It answers HTTP 202 with an `outcome` of `armed` and sends nothing until the exposure leaves the band, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the hedge instrument.

    Attributes:
        watched: The list of exposure_watch.ExposureWatch whose positions are added up.
        lower_band: The float lowest net exposure allowed before a hedge is traded.
        upper_band: The float highest net exposure allowed before a hedge is traded.
        hedge_exposure_per_unit: The float exposure one unit of the hedge carries, or None to let UBI count 1.
    """

    SYNTHETIC_TYPE = "exposure_hedge"

    def __init__(
        self,
        hedge_instrument: instruments.TradeableInstrument,
        *,
        watched: list[exposure_watch.ExposureWatch],
        lower_band: float,
        upper_band: float,
        product: str,
        hedge_exposure_per_unit: float | None = None,
        validity: str | None = None,
        tag: str | None = None,
        closes_position: bool = False,
        dry_run: bool = False,
    ):
        """Initialises the hedge.

        Args:
            hedge_instrument: The instruments.TradeableInstrument traded to bring the exposure back inside the band.
            watched: The list of exposure_watch.ExposureWatch whose positions are added up.
            lower_band: The float lowest net exposure allowed, below `upper_band`.
            upper_band: The float highest net exposure allowed, above `lower_band`.
            product: The str product of the hedge orders, `cnc`, `mis` or `nrml`.
            hedge_exposure_per_unit: The float exposure one unit of the hedge carries, which must not be zero, or None to let UBI count 1.
            validity: The str validity of the hedge orders, `day` or `ioc`, or None to let UBI use `day`.
            tag: A str of up to twenty letters and digits to label the request with, or None.
            closes_position: A bool that is True when every hedge closes a position, so it may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI check the request and return it without recording or sending anything.

        Raises:
            Nothing.
        """
        super().__init__(
            hedge_instrument,
            transaction_type="buy",
            product=product,
            order_type="market",
            quantity=1,
            validity=validity,
            tag=tag,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.watched = list(watched)
        self.lower_band = lower_band
        self.upper_band = upper_band
        self.hedge_exposure_per_unit = hedge_exposure_per_unit

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, holding the watched instruments as UBI reads them and the hedge instrument's id, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        documents = []
        for watch in self.watched:
            documents.append(watch.document())
        return {
            "watched": documents,
            "lower_band": self.lower_band,
            "upper_band": self.upper_band,
            "hedge_instrument_id": self.instrument.instrument_id,
            "hedge_exposure_per_unit": self.hedge_exposure_per_unit,
        }
