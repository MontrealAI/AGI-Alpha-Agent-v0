# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy


def identifier(value):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid identifier')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid integer')
    return value


class AccountBook:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError('invalid balances')
        self.balances = {identifier(key): integer(value) for key, value in initial.items()}
        self.revisions = {key: 0 for key in self.balances}
        self.receipts = {}

    def transact(self, request, operations, expected):
        identifier(request)
        if not isinstance(operations, list) or not operations or not isinstance(expected, dict):
            raise ValueError('invalid batch')
        touched = set()
        for op in operations:
            if not isinstance(op, dict) or set(op) != {'from', 'to', 'amount'}:
                raise ValueError('invalid operation')
            source, target = identifier(op['from']), identifier(op['to'])
            integer(op['amount'], 1)
            if source not in self.balances or target not in self.balances:
                raise ValueError('unknown account')
            touched.update((source, target))
        if set(expected) != touched:
            raise ValueError('incomplete revision guard')
        for account, revision in expected.items():
            identifier(account)
            integer(revision)

        # Validate types before equality: bools compare equal to ints in Python.
        # Retry recognition precedes comparison against current revisions.
        payload = deepcopy((operations, expected))
        if request in self.receipts:
            old, receipt = self.receipts[request]
            if old != payload:
                raise ValueError('request conflict')
            return deepcopy(receipt)
        if any(self.revisions[account] != revision for account, revision in expected.items()):
            raise ValueError('stale revision')

        # All sequential execution happens against a private tentative balance map.
        balances = dict(self.balances)
        for op in operations:
            source, target, amount = op['from'], op['to'], op['amount']
            if balances[source] < amount:
                raise ValueError('overdraft')
            balances[source] -= amount
            balances[target] += amount
        revisions = dict(self.revisions)
        for account in touched:
            revisions[account] += 1
        receipt = dict(request=request, balances={a: balances[a] for a in sorted(touched)},
                       revisions={a: revisions[a] for a in sorted(touched)})
        self.balances, self.revisions = balances, revisions
        self.receipts[request] = (payload, receipt)
        return deepcopy(receipt)

    def snapshot(self):
        return deepcopy(dict(balances=self.balances, revisions=self.revisions))
