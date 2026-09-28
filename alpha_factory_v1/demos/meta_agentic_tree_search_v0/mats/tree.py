# SPDX-License-Identifier: Apache-2.0
"""Simple best-first search helpers for integer policies.

The module defines :class:`Node` and :class:`Tree` used by the search loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import math


@dataclass
class Node:
    """A single state in the search tree."""

    agents: List[int]
    reward: float = 0.0
    visits: int = 0
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    value: float = field(init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.reward):
            raise ValueError("A node reward must be finite")
        self.agents = list(self.agents)
        self.value = self.reward
        self.reward = 0.0


class Tree:
    """Minimal UCB1-style search tree for integer policies."""

    def __init__(self, root: Node, exploration: float = 1.4, branching: int = 2, max_depth: int = 32) -> None:
        """Initialize the tree.

        Args:
            root: Root node of the tree.
            exploration: Exploration constant for UCB1.
        """

        if not math.isfinite(exploration) or exploration < 0:
            raise ValueError("Exploration must be finite and nonnegative")
        if not 2 <= branching <= 8 or not 1 <= max_depth <= 128:
            raise ValueError("Branching must be 2–8 and depth 1–128")
        self.root = root
        self.exploration = exploration
        self.branching = branching
        self.max_depth = max_depth

    def _available(self, node: Node, depth: int) -> bool:
        return depth < self.max_depth and (
            len(node.children) < self.branching or any(self._available(child, depth + 1) for child in node.children)
        )

    def select(self) -> Node:
        """Choose a node with an unexpanded branch, using UCB1 between full nodes."""

        node = self.root
        depth = 0
        if not self._available(node, depth):
            raise RuntimeError("The bounded search tree is fully expanded")
        while len(node.children) >= self.branching:
            node = max(
                (child for child in node.children if self._available(child, depth + 1)),
                key=lambda n: float("inf")
                if not n.visits
                else (n.reward / n.visits) + self.exploration * math.sqrt(math.log(max(1, node.visits)) / n.visits),
            )
            depth += 1
        return node

    def add_child(self, parent: Node, child: Node) -> None:
        """Attach ``child`` to ``parent``."""

        if child is parent or child.parent is not None or child is self.root:
            raise ValueError("A child must be a new, unattached node")
        cursor: Optional[Node] = parent
        depth = 0
        while cursor is not self.root:
            if cursor is None or depth >= self.max_depth:
                raise ValueError("Parent does not belong to this bounded tree")
            cursor = cursor.parent
            depth += 1
        if depth >= self.max_depth or len(parent.children) >= self.branching:
            raise ValueError("Parent has no unexpanded branch")
        child.parent = parent
        parent.children.append(child)

    def backprop(self, node: Node) -> None:
        """Propagate ``node``'s reward up to the root."""

        reward = node.value
        current: Optional[Node] = node
        while current is not None:
            current.visits += 1
            current.reward += reward
            current = current.parent

    def best_leaf(self) -> Node:
        """Return the visited leaf with highest average reward."""

        best: Optional[Node] = None
        stack = [self.root]
        while stack:
            n = stack.pop()
            if not n.children and n.visits and (best is None or n.reward / n.visits > best.reward / best.visits):
                best = n
            stack.extend(reversed(n.children))
        return best if best is not None else self.root
