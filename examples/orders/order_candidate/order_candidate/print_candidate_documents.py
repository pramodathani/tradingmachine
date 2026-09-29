"""Build the candidate objects of a multi-instrument order and show what each overrides.

The program builds three order candidates over Vodafone Idea and Yes Bank, one taking every field from the template and two overriding the side, the quantity, the price or the tag, and prints the object UBI would read for each, naming the fields it overrides. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/order_candidate/order_candidate/print_candidate_documents.py
"""

from tradingmachine.assets import equities
from tradingmachine.orders import order_candidate


class CandidateDocumentReport:
    """A report of the candidate objects a multi-instrument order would send.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        second_share: The tradingmachine.assets.equities.Equity for Yes Bank on the NSE.
        candidates: The list of tradingmachine.orders.order_candidate.OrderCandidate the report prints.
    """

    def __init__(self):
        """Looks up the two shares and builds the candidates.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.second_share = equities.Equity(exchange="nse", symbol="YESBANK")
        self.candidates = [
            order_candidate.OrderCandidate(self.share),
            order_candidate.OrderCandidate(
                self.second_share,
                transaction_type="sell",
                quantity=2,
                price=21.0,
            ),
            order_candidate.OrderCandidate(
                self.share,
                order_type="market",
                tag="exitleg",
            ),
        ]

    def overridden_fields(self, document: dict) -> list[str]:
        """Lists the template fields a candidate object overrides.

        Args:
            document: The dict candidate object built by `OrderCandidate.document`.

        Returns:
            A list of str field names, every key except `instrument_id`.

        Raises:
            Nothing.
        """
        fields = []
        for field in document:
            if field != "instrument_id":
                fields.append(field)
        return fields

    def run(self) -> None:
        """Prints each candidate's instrument, object and overridden fields.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for number, candidate in enumerate(self.candidates, start=1):
            document = candidate.document()
            fields = self.overridden_fields(document)
            print(f"Candidate {number}: {candidate.instrument.symbol}")
            print(f"  object: {document}")
            if fields:
                print(f"  overrides: {', '.join(fields)}")
            else:
                print("  overrides nothing, so every field comes from the template")


if __name__ == "__main__":
    CandidateDocumentReport().run()
