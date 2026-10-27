# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy


def identifier(value):
    if not isinstance(value, str) or not value:
        raise ValueError("invalid identifier")
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid integer")
    return value


class Ledger:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError("invalid initial balances")
        self.wallets = {identifier(k): {"available": integer(v), "reserved": 0, "spent": 0}
                        for k, v in initial.items()}
        self.requests = {}

    def _owned(self, owner, request):
        identifier(owner)
        identifier(request)
        if owner not in self.wallets or request not in self.requests:
            raise ValueError("unknown or unauthorized request")
        record = self.requests[request]
        # Authorize before returning any record, including terminal retries.
        if record["owner"] != owner:
            raise ValueError("unknown or unauthorized request")
        return record

    def reserve(self, owner, request, cap):
        identifier(owner)
        identifier(request)
        integer(cap, 1)
        if owner not in self.wallets:
            raise ValueError("unknown owner")
        if request in self.requests:
            old = self._owned(owner, request)
            if old["cap"] != cap:
                raise ValueError("request conflict")
            return deepcopy(old)
        wallet = self.wallets[owner]
        if wallet["available"] < cap:
            raise ValueError("insufficient balance")
        wallet["available"] -= cap
        wallet["reserved"] += cap
        record = {"owner": owner, "cap": cap, "state": "reserved", "actual": None}
        self.requests[request] = record
        return deepcopy(record)

    def settle(self, owner, request, actual):
        integer(actual)
        record = self._owned(owner, request)
        if record["state"] == "settled":
            if record["actual"] != actual:
                raise ValueError("settlement conflict")
            return deepcopy(record)
        if record["state"] != "reserved" or actual > record["cap"]:
            raise ValueError("invalid settlement")
        wallet = self.wallets[owner]
        wallet["reserved"] -= record["cap"]
        wallet["available"] += record["cap"] - actual
        wallet["spent"] += actual
        record.update(state="settled", actual=actual)
        return deepcopy(record)

    def cancel(self, owner, request):
        record = self._owned(owner, request)
        if record["state"] == "canceled":
            return deepcopy(record)
        if record["state"] != "reserved":
            raise ValueError("invalid cancellation")
        wallet = self.wallets[owner]
        wallet["reserved"] -= record["cap"]
        wallet["available"] += record["cap"]
        record["state"] = "canceled"
        return deepcopy(record)

    def snapshot(self):
        return deepcopy({"wallets": self.wallets, "requests": self.requests})
