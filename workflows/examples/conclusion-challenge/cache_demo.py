"""Fictional in-memory cache defect; no external services or real user data."""


class Notes:
    def __init__(self):
        self.store = {'note-a': 'version-one'}
        self.cache = {}

    def read(self, key):
        if key not in self.cache:
            self.cache[key] = self.store[key]
        return self.cache[key]

    def write(self, key, value):
        self.store[key] = value
        # Deliberate defect: a previously cached value is retained.


def observe():
    notes = Notes()
    before = notes.read('note-a')
    notes.write('note-a', 'version-two')
    stored = notes.store['note-a']
    cached = notes.read('note-a')
    notes.cache.clear()
    fresh = notes.read('note-a')
    return {'before': before, 'stored_after_write': stored,
            'cached_after_write': cached, 'after_clear': fresh}
