import random
from collections import Counter
from math import comb

flags = 0
def neighbors(n, side):
    row, col = n // side, n % side
    result = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue  # skip the dot itself
            r, c = row + dr, col + dc
            if 0 <= r < side and 0 <= c < side:
                result.append(r * side + c)
    return result

def nextdoor(n, Board):
    bits = neighbors(n, Board.side)
    tiles = []
    for i in bits:
        tiles.append(next((d for d in Board.tiles if d.id == i), None))
    return tiles

class tile:
    def __init__(self, value, id, revealed):
        self.value = value
        self.id = id
        self.revealed = revealed
        self.flagged = False
    def click(self, Board):
        if self.revealed:
            return
        self.revealed = True
        Board.turns += 1
        if self.value == 100:
            print("Game Over!")
            raise SystemExit
        if self.value == 0:
            for square in nextdoor(self.id, Board):
                if not square.flagged:
                    square.click(Board)
    def flag(self):
        global flags
        flags += 1
        self.flagged = True

        

       




class bomb:
     def __init__(self, bit, id):
        self.id = id
        self.pos = bit    

class Board:
    def __init__(self, side):
        self.side = side
        self.bits = self.side * self.side
        self.turns = 0

    def makemines(self, num):
        self.bombs = []
        self.tiles = []
        for i in range(num):
            self.bombs.append(bomb(random.randint(0, self.bits), i))
        for i in range(self.bits):
                    if any(mine.pos == i for mine in self.bombs):
                        self.tiles.append(tile(100, i, False))
                    else:   
                        self.tiles.append(tile(10, i, False))
        regular = self.tiles
        for square in regular:
            count = 0
            buddys = nextdoor(square.id, self)
            if square.value == 100:
                square.value = 100
                continue
            for dot in buddys:
                if dot is not None and dot.value == 100:
                    count = count + 1
            square.value = count

    def display(self):
        k = 0
        line = ""
        for i in range(self.bits):
            dot = next((d for d in self.tiles if d.id == i), None)
            if dot.revealed:
                dotdisplay = "b" if dot.value == 100 else dot.value
            elif dot.flagged:
               dotdisplay = "f" 
            else:
                dotdisplay = "."
            
            k = k + 1
            line = line + " " + str(dotdisplay)
            if k == self.side:
                print(line)
                line = ""
                k = 0
        if line:
            print(line)

def _convolve(left, right):
    result = Counter()
    for left_mines, left_count in left.items():
        for right_mines, right_count in right.items():
            result[left_mines + right_mines] += left_count * right_count
    return result


def _constraints(Board):
    constraints = []
    for square in Board.tiles:
        if not square.revealed or square.value < 0 or square.value == 100:
            continue
        hood = nextdoor(square.id, Board)
        hidden = frozenset(
            neighbor.id for neighbor in hood
            if not neighbor.revealed and not neighbor.flagged
        )
        flagged = sum(neighbor.flagged for neighbor in hood)
        remaining = square.value - flagged
        if hidden or remaining != 0:
            constraints.append((hidden, remaining))
    return constraints


def _components(variables, constraints):
    adjacent = {variable: set() for variable in variables}
    for cells, _ in constraints:
        for cell in cells:
            adjacent[cell].update(cells - {cell})

    components = []
    unseen = set(variables)
    while unseen:
        component = set()
        pending = [unseen.pop()]
        while pending:
            cell = pending.pop()
            component.add(cell)
            for neighbor in adjacent[cell] & unseen:
                unseen.remove(neighbor)
                pending.append(neighbor)
        components.append(component)
    return components


def _enumerate_component(component, constraints):
    relevant = [(cells, remaining) for cells, remaining in constraints if cells <= component]
    frequency = Counter(cell for cells, _ in relevant for cell in cells)
    order = sorted(component, key=lambda cell: -frequency[cell])
    assignments = {}
    mine_counts = Counter()
    cell_mine_counts = {cell: Counter() for cell in component}

    def search(index, mines):
        for cells, remaining in relevant:
            assigned_mines = sum(assignments.get(cell, 0) for cell in cells)
            unassigned = sum(cell not in assignments for cell in cells)
            if assigned_mines > remaining or assigned_mines + unassigned < remaining:
                return
        if index == len(order):
            mine_counts[mines] += 1
            for cell, is_mine in assignments.items():
                if is_mine:
                    cell_mine_counts[cell][mines] += 1
            return
        cell = order[index]
        for is_mine in (0, 1):
            assignments[cell] = is_mine
            search(index + 1, mines + is_mine)
        del assignments[cell]

    search(0, 0)
    return mine_counts, cell_mine_counts


def _probabilities(Board):
    constraints = _constraints(Board)
    frontier = set().union(*(cells for cells, _ in constraints)) if constraints else set()
    hidden = {
        square.id for square in Board.tiles
        if not square.revealed and not square.flagged
    }
    interior = hidden - frontier
    mine_total = len({
        mine.pos for mine in Board.bombs
        if 0 <= mine.pos < Board.bits
    })
    remaining_mines = mine_total - sum(square.flagged for square in Board.tiles)

    if remaining_mines < 0 or remaining_mines > len(hidden):
        raise ValueError("The current flags conflict with the total mine count.")
    for cells, remaining in constraints:
        if remaining < 0 or remaining > len(cells):
            raise ValueError("The revealed clues conflict with the current flags.")
    if any(not cells and remaining != 0 for cells, remaining in constraints):
        raise ValueError("The revealed clues conflict with the current flags.")

    components = _components(frontier, constraints)
    models = [
        _enumerate_component(component, constraints)
        for component in components
    ]
    distributions = [model[0] for model in models]

    prefix = [Counter({0: 1})]
    for distribution in distributions:
        prefix.append(_convolve(prefix[-1], distribution))
    suffix = [Counter() for _ in range(len(distributions) + 1)]
    suffix[-1] = Counter({0: 1})
    for index in range(len(distributions) - 1, -1, -1):
        suffix[index] = _convolve(distributions[index], suffix[index + 1])

    interior_count = len(interior)

    def arrangements_with_interior(frontier_mines):
        interior_mines = remaining_mines - frontier_mines
        if 0 <= interior_mines <= interior_count:
            return comb(interior_count, interior_mines)
        return 0

    total_arrangements = sum(
        count * arrangements_with_interior(mines)
        for mines, count in prefix[-1].items()
    )
    if total_arrangements == 0:
        raise ValueError("No mine layout satisfies the revealed clues and mine count.")

    probabilities = {}
    for index, (_, cell_counts) in enumerate(models):
        other_groups = _convolve(prefix[index], suffix[index + 1])
        for cell, counts_by_mines in cell_counts.items():
            mine_arrangements = 0
            for group_mines, count in counts_by_mines.items():
                for other_mines, other_count in other_groups.items():
                    mine_arrangements += (
                        count * other_count
                        * arrangements_with_interior(group_mines + other_mines)
                    )
            probabilities[cell] = mine_arrangements / total_arrangements

    if interior_count:
        interior_mine_arrangements = sum(
            count * interior_mines
            * comb(interior_count - 1, interior_mines - 1)
            for frontier_mines, count in prefix[-1].items()
            if 1 <= (interior_mines := remaining_mines - frontier_mines) <= interior_count
        )
        probability = interior_mine_arrangements / total_arrangements
        for cell in interior:
            probabilities[cell] = probability
    return probabilities


def _subset_deductions(constraints):
    safe = set()
    mines = set()
    for first_index, (first_cells, first_remaining) in enumerate(constraints):
        for second_cells, second_remaining in constraints[first_index + 1:]:
            if first_cells < second_cells:
                extra = second_cells - first_cells
                extra_mines = second_remaining - first_remaining
            elif second_cells < first_cells:
                extra = first_cells - second_cells
                extra_mines = first_remaining - second_remaining
            else:
                continue
            if extra_mines == 0:
                safe.update(extra)
            elif extra_mines == len(extra):
                mines.update(extra)
    return safe, mines


def _preferred_first_click(Board):
    middle = (Board.side - 1) / 2
    center_cells = sorted(
        Board.tiles,
        key=lambda square: (
            (square.id // Board.side - middle) ** 2
            + (square.id % Board.side - middle) ** 2
        ),
    )
    corners = {
        0,
        Board.side - 1,
        Board.bits - Board.side,
        Board.bits - 1,
    }
    preferred = [
        square for square in center_cells
        if square.id in corners or abs(square.id // Board.side - middle) <= 0.5
        and abs(square.id % Board.side - middle) <= 0.5
    ]
    preferred.extend(square for square in Board.tiles if square.id in corners)
    safe_preferred = next(
        (square for square in preferred if square.value != 100), None
    )
    return safe_preferred or next(
        (square for square in Board.tiles if square.value != 100), None
    )


def flagging(Board):
    constraints = _constraints(Board)
    _, certain_mines = _subset_deductions(constraints)
    probabilities = _probabilities(Board)
    certain_mines.update(
        cell for cell, probability in probabilities.items() if probability == 1
    )
    for cell in certain_mines:
        square = Board.tiles[cell]
        if not square.flagged and not square.revealed:
            square.flag()


def clicking(Board):
    if Board.turns == 0:
        first = _preferred_first_click(Board)
        if first is not None:
            first.click(Board)
        return

    constraints = _constraints(Board)
    certain_safe, _ = _subset_deductions(constraints)
    probabilities = _probabilities(Board)
    certain_safe.update(
        cell for cell, probability in probabilities.items() if probability == 0
    )
    for cell in certain_safe:
        square = Board.tiles[cell]
        if not square.revealed and not square.flagged:
            square.click(Board)
    if certain_safe:
        return

    candidates = [
        Board.tiles[cell] for cell in probabilities
        if not Board.tiles[cell].revealed and not Board.tiles[cell].flagged
    ]
    if not candidates:
        return

    def guess_key(square):
        row, col = divmod(square.id, Board.side)
        is_edge = row in (0, Board.side - 1) or col in (0, Board.side - 1)
        hood = nextdoor(square.id, Board)
        information = sum(neighbor.revealed for neighbor in hood)
        information += sum(not neighbor.revealed and not neighbor.flagged for neighbor in hood)
        return probabilities[square.id], not is_edge, -information

    min(candidates, key=guess_key).click(Board)

def checkwin(Board):
    mine_positions = {
        mine.pos for mine in Board.bombs
        if 0 <= mine.pos < Board.bits
    }
    flagged_positions = {
        square.id for square in Board.tiles if square.flagged
    }
    if flagged_positions == mine_positions:
        print("Winner!")



size = int(input("SIZE?"))
bombs = int(input("BOMBS?"))
first = Board(size)
first.makemines(bombs)
while True:
    first.display()
    input()
    flagging(first)
    clicking(first)
    checkwin(first)
        
