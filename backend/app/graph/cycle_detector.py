from __future__ import annotations


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """
    DFS-based cycle detection. Returns a list of cycles,
    where each cycle is a list of file paths forming a loop.
    """
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbour in graph.get(node, []):
            if neighbour not in visited:
                dfs(neighbour)
            elif neighbour in rec_stack:
                # Found a cycle — extract the loop portion
                cycle_start = path.index(neighbour)
                cycles.append(path[cycle_start:] + [neighbour])

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def nodes_in_cycles(cycles: list[list[str]]) -> set[str]:
    result: set[str] = set()
    for cycle in cycles:
        result.update(cycle)
    return result
