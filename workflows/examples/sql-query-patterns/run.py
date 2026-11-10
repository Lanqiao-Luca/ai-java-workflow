"""Four synthetic SQL semantics controls, using SQLite in memory only."""
import json
import sqlite3


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Fixture:
    """Count SELECT executions separately from in-memory fixture setup."""

    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.selects = 0

    def select(self, sql, parameters=()):
        self.selects += 1
        return self.connection.execute(sql, parameters).fetchall()

    def close(self):
        self.connection.close()


def parent_fixture():
    fixture = Fixture()
    fixture.connection.executescript('''
        CREATE TABLE parent (id INTEGER PRIMARY KEY);
        CREATE TABLE child (
            id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL,
            amount INTEGER NOT NULL
        );
        INSERT INTO parent VALUES (1), (2), (3);
        INSERT INTO child VALUES (1, 1, 4), (2, 1, 6), (3, 2, 7);
    ''')
    return fixture


def n_plus_one():
    fixture = parent_fixture()
    try:
        parents = fixture.select('SELECT id FROM parent ORDER BY id')
        individual = []
        for (parent_id,) in parents:
            count, total = fixture.select(
                'SELECT COUNT(*), COALESCE(SUM(amount), 0) '
                'FROM child WHERE parent_id = ?', (parent_id,)
            )[0]
            individual.append([parent_id, count, total])
        individual_queries = fixture.selects
        fixture.selects = 0
        batched_parents = fixture.select('SELECT id FROM parent ORDER BY id')
        grouped = fixture.select(
            'SELECT parent_id, COUNT(*), SUM(amount) FROM child '
            'WHERE parent_id IN (?, ?, ?) GROUP BY parent_id',
            tuple(row[0] for row in batched_parents)
        )
        lookup = {row[0]: row[1:] for row in grouped}
        batched = [[parent_id, *lookup.get(parent_id, (0, 0))]
                   for (parent_id,) in batched_parents]
        require(individual == batched == [[1, 2, 10], [2, 1, 7], [3, 0, 0]],
                'batch aggregation changed results or lost zero-child parent')
        require(individual_queries == 4 and fixture.selects == 2,
                'unexpected SELECT execution counts')
        return {'individual': individual, 'batched': batched,
                'individual_selects': individual_queries,
                'batched_selects': fixture.selects,
                'zero_child_parent_preserved': batched[-1] == [3, 0, 0]}
    finally:
        fixture.close()


def parent_pagination():
    fixture = parent_fixture()
    try:
        page = fixture.select('SELECT id FROM parent ORDER BY id LIMIT 2')
        children = fixture.select(
            'SELECT parent_id, id FROM child WHERE parent_id IN (?, ?) '
            'ORDER BY parent_id, id', tuple(row[0] for row in page)
        )
        parent_first_queries = fixture.selects
        fixture.selects = 0
        joined = fixture.select(
            'SELECT p.id, c.id FROM parent p LEFT JOIN child c '
            'ON c.parent_id = p.id ORDER BY p.id, c.id LIMIT 2'
        )
        parent_ids = [row[0] for row in page]
        joined_parent_ids = sorted({row[0] for row in joined})
        require(parent_ids == [1, 2] and children == [(1, 1), (1, 2), (2, 3)],
                'parent-first pagination lost expected parents or children')
        require(joined == [(1, 1), (1, 2)] and joined_parent_ids == [1],
                'JOIN plus LIMIT counterexample was not reproduced')
        require(parent_first_queries == 2 and fixture.selects == 1,
                'unexpected pagination SELECT counts')
        return {'parent_first_ids': parent_ids, 'children': children,
                'join_limit_rows': joined, 'join_limit_parent_ids': joined_parent_ids,
                'parent_first_selects': parent_first_queries,
                'join_limit_selects': fixture.selects}
    finally:
        fixture.close()


def date_boundary():
    fixture = Fixture()
    try:
        fixture.connection.executescript('''
            CREATE TABLE event (id INTEGER PRIMARY KEY, at TEXT);
            INSERT INTO event VALUES
                (1, '2040-06-14T23:59:59Z'),
                (2, '2040-06-15T00:00:00Z'),
                (3, '2040-06-15T12:00:00Z'),
                (4, '2040-06-15T23:59:59Z'),
                (5, '2040-06-16T00:00:00Z'),
                (6, NULL);
        ''')
        date_rows = fixture.select(
            "SELECT id FROM event WHERE DATE(at) = ? ORDER BY id", ('2040-06-15',)
        )
        range_rows = fixture.select(
            'SELECT id FROM event WHERE at >= ? AND at < ? ORDER BY id',
            ('2040-06-15T00:00:00Z', '2040-06-16T00:00:00Z')
        )
        require(date_rows == range_rows == [(2,), (3,), (4,)],
                'UTC date and half-open interval differ at fixture boundaries')
        require(fixture.selects == 2, 'unexpected date SELECT count')
        return {'date_ids': [row[0] for row in date_rows],
                'half_open_ids': [row[0] for row in range_rows],
                'selects': fixture.selects,
                'preconditions': ['UTC calendar day', 'TEXT in fixed-width YYYY-MM-DDTHH:MM:SSZ',
                                  'second precision', 'BINARY text comparison',
                                  'NULL excluded by both predicates'],
                'excluded_boundary_ids': [1, 5, 6]}
    finally:
        fixture.close()


def proposed_unique():
    absent, installed = Fixture(), Fixture()
    try:
        for fixture in (absent, installed):
            fixture.connection.execute('CREATE TABLE item (code TEXT NOT NULL)')
        absent.connection.executemany('INSERT INTO item VALUES (?)', [('sample',), ('sample',)])
        absent_count = absent.select('SELECT COUNT(*) FROM item')[0][0]
        absent_indexes = absent.connection.execute('PRAGMA index_list(item)').fetchall()
        installed.connection.execute('CREATE UNIQUE INDEX item_code_unique ON item(code)')
        installed.connection.execute('INSERT INTO item VALUES (?)', ('sample',))
        rejected = False
        try:
            installed.connection.execute('INSERT INTO item VALUES (?)', ('sample',))
        except sqlite3.IntegrityError:
            rejected = True
        installed_count = installed.select('SELECT COUNT(*) FROM item')[0][0]
        installed_indexes = installed.connection.execute('PRAGMA index_list(item)').fetchall()
        require(absent_count == 2 and absent_indexes == [],
                'proposal-only fixture unexpectedly enforces uniqueness')
        require(rejected and installed_count == 1 and
                any(row[1] == 'item_code_unique' and row[2] == 1 for row in installed_indexes),
                'installed fixture did not enforce observed unique index')
        require(absent.selects == 1 and installed.selects == 1,
                'unexpected uniqueness SELECT counts')
        return {'proposed_schema': 'UNIQUE(code)', 'proposal_only_rows': absent_count,
                'proposal_only_indexes': absent_indexes,
                'installed_index': installed_indexes, 'installed_rows': installed_count,
                'duplicate_rejected': rejected,
                'selects': absent.selects + installed.selects,
                'metadata_reads': 2,
                'scope': 'Two independent in-memory fixtures; no deployment evidence'}
    finally:
        absent.close()
        installed.close()


def run_examples():
    return {'synthetic': True, 'database': 'SQLite :memory:',
            'sqlite_version': sqlite3.sqlite_version,
            'scope': {'external_connections': 0, 'repository_output_writes': 0,
                      'writes': 'in-memory fixtures only',
                      'evidence': 'semantics and SELECT counts only',
                      'not_measured': ['performance', 'MySQL execution plans',
                                       'production schema', 'authorization branches',
                                       'shard routing', 'concurrent changes']},
            'results': {'n_plus_one': n_plus_one(),
                        'parent_pagination': parent_pagination(),
                        'date_boundary': date_boundary(),
                        'proposed_unique': proposed_unique()}}


if __name__ == '__main__':
    print(json.dumps(run_examples(), ensure_ascii=False, indent=2))
