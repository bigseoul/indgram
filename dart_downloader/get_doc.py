import OpenDartReader
dart = OpenDartReader('888e4aca3aba61a62811ba87e0fc054e2d9f6ea0')
doc = dart.document('20250430000504')
print(f"Doc length: {len(doc) if doc else 0}")
