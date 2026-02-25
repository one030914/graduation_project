import time

class Timer:
    def __init__(self):
        self.marks = []
        self.start = time.perf_counter()

    def mark(self, name: str):
        now = time.perf_counter()
        self.marks.append((name, now - self.start))
        self.start = now

    def report(self) -> dict:
        return {name: round(sec, 3) for name, sec in self.marks}