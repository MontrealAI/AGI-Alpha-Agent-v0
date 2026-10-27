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


class Journal:
    def __init__(self, initial):
        if not isinstance(initial, dict):
            raise ValueError('invalid initial balances')
        self.wallets = {identifier(key): {'available': integer(value), 'reserved': 0, 'spent': 0}
                        for key, value in initial.items()}
        self.jobs = {}
        self.events = []
        self.receipts = {}

    def append(self, event):
        if not isinstance(event, dict) or set(event) != {'id', 'job', 'owner', 'kind', 'amount'}:
            raise ValueError('invalid event')
        identifier(event['id'])
        identifier(event['job'])
        identifier(event['owner'])
        identifier(event['kind'])
        integer(event['amount'])
        if event['id'] in self.receipts:
            old, receipt = self.receipts[event['id']]
            if old != event:
                raise ValueError('conflicting event ID')
            return deepcopy(receipt)
        owner, job, kind, amount = (event[key] for key in ('owner', 'job', 'kind', 'amount'))
        if owner not in self.wallets:
            raise ValueError('unknown owner')
        wallets = deepcopy(self.wallets)
        jobs = deepcopy(self.jobs)
        wallet = wallets[owner]
        if kind == 'reserve':
            if amount <= 0 or job in jobs or wallet['available'] < amount:
                raise ValueError('invalid reservation')
            wallet['available'] -= amount
            wallet['reserved'] += amount
            jobs[job] = {'owner': owner, 'cap': amount, 'state': 'active'}
        elif kind in {'settle', 'cancel'}:
            if job not in jobs or jobs[job]['state'] != 'active' or jobs[job]['owner'] != owner:
                raise ValueError('invalid owned active job')
            record = jobs[job]
            if amount > record['cap'] or (kind == 'cancel' and amount != 0):
                raise ValueError('invalid terminal amount')
            wallet['reserved'] -= record['cap']
            wallet['available'] += record['cap'] - amount
            wallet['spent'] += amount
            record['state'] = 'settled' if kind == 'settle' else 'canceled'
        else:
            raise ValueError('unknown kind')
        receipt = {'id': event['id'], 'sequence': len(self.events) + 1, 'job': job, 'kind': kind}
        # Publish only successful transitions and keep the journal independent.
        self.wallets, self.jobs = wallets, jobs
        self.events.append(deepcopy(event))
        self.receipts[event['id']] = (deepcopy(event), deepcopy(receipt))
        return deepcopy(receipt)

    def snapshot(self):
        return deepcopy({'wallets': self.wallets, 'jobs': self.jobs})

    def export_log(self):
        return deepcopy(self.events)

    @classmethod
    def replay(cls, initial, events):
        if not isinstance(events, list):
            raise ValueError('invalid log')
        journal = cls(initial)
        for event in events:
            journal.append(event)
        return journal
