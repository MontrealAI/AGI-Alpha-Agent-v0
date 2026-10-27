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


class Scheduler:
    def __init__(self, capacity):
        self.capacity = integer(capacity, 1)
        self.jobs = {}
        # Lease identities remain reserved for the lifetime of the scheduler.
        self.leases = {}

    def _owned(self, owner, job):
        identifier(owner)
        identifier(job)
        if job not in self.jobs or self.jobs[job]["owner"] != owner:
            raise ValueError("unknown or unauthorized job")
        return self.jobs[job]

    def add(self, owner, job, cost, dependencies):
        identifier(owner)
        identifier(job)
        integer(cost, 1)
        if cost > self.capacity or not isinstance(dependencies, list):
            raise ValueError("invalid job")
        for dep in dependencies:
            identifier(dep)
        if len(set(dependencies)) != len(dependencies) or job in dependencies:
            raise ValueError("invalid dependencies")
        if job in self.jobs:
            old = self._owned(owner, job)
            if old["cost"] != cost or old["deps"] != dependencies:
                raise ValueError("job conflict")
            return deepcopy(old)
        for dep in dependencies:
            self._owned(owner, dep)
        record = dict(owner=owner, cost=cost, deps=list(dependencies), state="pending", lease=None)
        self.jobs[job] = record
        return deepcopy(record)

    def _used(self):
        return sum(row["cost"] for row in self.jobs.values() if row["state"] == "running")

    def claim(self, owner, job, lease):
        identifier(lease)
        row = self._owned(owner, job)
        if row["state"] == "running" and row["lease"] == lease:
            return deepcopy(row)
        if lease in self.leases or row["state"] != "pending":
            raise ValueError("lease conflict")
        if any(self.jobs[dep]["state"] != "succeeded" for dep in row["deps"]):
            raise ValueError("dependencies not succeeded")
        if self._used() + row["cost"] > self.capacity:
            raise ValueError("capacity exceeded")
        row.update(state="running", lease=lease)
        self.leases[lease] = dict(owner=owner, job=job, result=None, canceled=False, receipt=None)
        return deepcopy(row)

    def finish(self, owner, job, lease, success):
        identifier(lease)
        if type(success) is not bool:
            raise ValueError("success must be bool")
        row = self._owned(owner, job)
        record = self.leases.get(lease)
        if not record or record["owner"] != owner or record["job"] != job or record["canceled"]:
            raise ValueError("invalid lease")
        # False is a completed failure, distinct from an unfinished lease.
        if record["result"] is not None:
            if record["result"] != success:
                raise ValueError("finish conflict")
            return deepcopy(record["receipt"])
        if row["state"] != "running" or row["lease"] != lease:
            raise ValueError("not active")
        row.update(state="succeeded" if success else "pending", lease=None)
        record["result"] = success
        record["receipt"] = deepcopy(row)
        return deepcopy(record["receipt"])

    def cancel(self, owner, job):
        row = self._owned(owner, job)
        if row["state"] == "succeeded":
            raise ValueError("already succeeded")
        if row["state"] == "running":
            self.leases[row["lease"]]["canceled"] = True
        row.update(state="canceled", lease=None)
        return deepcopy(row)

    def snapshot(self):
        return deepcopy(dict(capacity=self.capacity, used=self._used(), jobs=self.jobs))
