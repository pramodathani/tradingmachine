# data/mapping/rules/zerodha.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/zerodha.yaml`, reordered into the canonical segment order. `raw_table` points at this project's `instruments.zerodha`.

Every segment here has an empty rules list. Zerodha publishes one flat instrument type per exchange with no discriminating column, so nothing about this broker is an equality match and `zerodha.py` classifies every row itself — see that note for the dispatch.

The file is still necessary rather than ceremonial. It declares, per segment, which raw column supplies each identity field and each broker field, which is what the base class reads once the adapter has chosen a segment. It is also what config validation checks, so a segment name or shape that is not canonical still fails at load time on this broker exactly as on the others.

Two identity declarations look wrong and are not. Both fixed income segments name `exchange_token` as their symbol source; the adapter replaces it with the ISIN resolved from the shared security identifier map, and the column named here is what that lookup is keyed on. `nse_commodities` names `name` rather than the trading symbol, because this broker's commodity rows carry the readable name there — with two exceptions the adapter handles, a blank name and one row misnamed after an unrelated fund.
