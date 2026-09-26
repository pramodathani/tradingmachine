"""The trading account as a whole, rather than any one instrument in it.

`tradingmachine.accounts.account` holds `Account`, whose `flatten` is UBI's kill switch: it cancels every open order at every broker and then closes every position. Nothing is imported here, so import the module you need.

Typical usage example:

  from tradingmachine.accounts import account

  preview = account.Account().flatten(confirm="FLATTEN", dry_run=True)
"""
