"""20 Python coding tasks with hidden asserts. Each: (id, level, prompt, tests, reference).
Levels: 1 easy, 2 medium, 3 harder / bug-fix. References are only used to validate the tests themselves."""

TASKS = [
("rle", 1, """Write a Python function `rle_encode(s: str) -> str` that run-length encodes a string: each run of the same
character becomes the count followed by the character, e.g. "aaabcc" -> "3a1b2c". Empty string -> "".""",
"""assert rle_encode("aaabcc") == "3a1b2c"
assert rle_encode("") == ""
assert rle_encode("a") == "1a"
assert rle_encode("zzzzzzzzzzzz") == "12z"
assert rle_encode("abab") == "1a1b1a1b"
""",
"""def rle_encode(s):
    out=[];i=0
    while i<len(s):
        j=i
        while j<len(s) and s[j]==s[i]: j+=1
        out.append(f"{j-i}{s[i]}"); i=j
    return "".join(out)
"""),

("brackets", 1, """Write `is_balanced(s: str) -> bool` that returns True if all brackets ()[]{} in s are balanced and correctly
nested. Other characters are ignored.""",
"""assert is_balanced("([]{})")
assert is_balanced("a(b[c]{d}e)f")
assert not is_balanced("(]")
assert not is_balanced("(()")
assert not is_balanced(")(")
assert is_balanced("")
assert not is_balanced("{[}]")
""",
"""def is_balanced(s):
    st=[];m={')':'(',']':'[','}':'{'}
    for c in s:
        if c in '([{': st.append(c)
        elif c in m:
            if not st or st.pop()!=m[c]: return False
    return not st
"""),

("roman", 1, """Write `to_roman(n: int) -> str` converting an integer 1..3999 to a Roman numeral (standard subtractive form,
e.g. 4 -> "IV", 1994 -> "MCMXCIV").""",
"""assert to_roman(1) == "I"
assert to_roman(4) == "IV"
assert to_roman(9) == "IX"
assert to_roman(58) == "LVIII"
assert to_roman(1994) == "MCMXCIV"
assert to_roman(3999) == "MMMCMXCIX"
""",
"""def to_roman(n):
    v=[(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    r=''
    for a,b in v:
        while n>=a: r+=b;n-=a
    return r
"""),

("merge_intervals", 1, """Write `merge_intervals(intervals: list[list[int]]) -> list[list[int]]` that merges overlapping or touching
closed intervals and returns them sorted by start. Example: [[1,3],[2,6],[8,10],[10,12]] -> [[1,6],[8,12]].""",
"""assert merge_intervals([[1,3],[2,6],[8,10],[10,12]]) == [[1,6],[8,12]]
assert merge_intervals([]) == []
assert merge_intervals([[5,7],[1,2]]) == [[1,2],[5,7]]
assert merge_intervals([[1,10],[2,3],[4,5]]) == [[1,10]]
""",
"""def merge_intervals(iv):
    out=[]
    for a,b in sorted(iv):
        if out and a<=out[-1][1]: out[-1][1]=max(out[-1][1],b)
        else: out.append([a,b])
    return out
"""),

("semver", 1, """Write `compare_versions(a: str, b: str) -> int` for dotted numeric versions like "1.2.10". Return -1 if a<b,
0 if equal, 1 if a>b. Missing parts count as 0, so "1.2" == "1.2.0". Compare numerically, so "1.10" > "1.9".""",
"""assert compare_versions("1.2.10", "1.2.9") == 1
assert compare_versions("1.10", "1.9") == 1
assert compare_versions("1.2", "1.2.0") == 0
assert compare_versions("0.9.9", "1.0") == -1
assert compare_versions("2.0.0.1", "2") == 1
""",
"""def compare_versions(a,b):
    x=[int(p) for p in a.split('.')];y=[int(p) for p in b.split('.')]
    n=max(len(x),len(y));x+=[0]*(n-len(x));y+=[0]*(n-len(y))
    return (x>y)-(x<y)
"""),

("anagrams", 1, """Write `group_anagrams(words: list[str]) -> list[list[str]]`. Group words that are anagrams of each other.
Inside each group keep the input order; order groups by the first appearance of their first word.""",
"""assert group_anagrams(["eat","tea","tan","ate","nat","bat"]) == [["eat","tea","ate"],["tan","nat"],["bat"]]
assert group_anagrams([]) == []
assert group_anagrams(["a"]) == [["a"]]
assert group_anagrams(["ab","ba","abc","cab","b"]) == [["ab","ba"],["abc","cab"],["b"]]
""",
"""def group_anagrams(ws):
    d={}
    for w in ws: d.setdefault(''.join(sorted(w)),[]).append(w)
    return list(d.values())
"""),

("spiral", 2, """Write `spiral(matrix: list[list[int]]) -> list[int]` returning the elements of a rectangular matrix in clockwise
spiral order starting at the top-left. Works for empty and non-square matrices.""",
"""assert spiral([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]
assert spiral([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) == [1,2,3,4,8,12,11,10,9,5,6,7]
assert spiral([]) == []
assert spiral([[1],[2],[3]]) == [1,2,3]
assert spiral([[1,2]]) == [1,2]
""",
"""def spiral(m):
    r=[]
    m=[row[:] for row in m]
    while m:
        r+=m.pop(0)
        m=[list(x) for x in zip(*m)][::-1]
    return r
"""),

("lru", 2, """Implement class `LRUCache` with `__init__(self, capacity: int)`, `get(self, key) -> int` (returns -1 if absent)
and `put(self, key, value) -> None`. Both operations must update recency; when capacity is exceeded evict the least
recently used key.""",
"""c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1
assert c.get(3) == 3 and c.get(4) == 4
c.put(3, 30)
c.put(5, 5)
assert c.get(4) == -1 and c.get(3) == 30
""",
"""from collections import OrderedDict
class LRUCache:
    def __init__(self,c): self.c=c; self.d=OrderedDict()
    def get(self,k):
        if k not in self.d: return -1
        self.d.move_to_end(k); return self.d[k]
    def put(self,k,v):
        self.d[k]=v; self.d.move_to_end(k)
        if len(self.d)>self.c: self.d.popitem(last=False)
"""),

("topo", 2, """Write `build_order(deps: dict[str, list[str]]) -> list[str]`. deps maps a package to the packages it depends
on (which must come before it). Return a valid order containing every package mentioned (keys and dependencies).
When several packages are available, pick them in alphabetical order. Raise ValueError if there is a cycle.""",
"""assert build_order({"app": ["lib", "utils"], "lib": ["utils"], "utils": []}) == ["utils", "lib", "app"]
assert build_order({"b": ["a"], "c": ["a"]}) == ["a", "b", "c"]
assert build_order({}) == []
try:
    build_order({"a": ["b"], "b": ["a"]}); raise SystemExit("no error on cycle")
except ValueError:
    pass
""",
"""import heapq
def build_order(deps):
    nodes=set(deps)|{d for v in deps.values() for d in v}
    indeg={n:0 for n in nodes};out={n:[] for n in nodes}
    for k,v in deps.items():
        for d in v: out[d].append(k); indeg[k]+=1
    h=[n for n in nodes if indeg[n]==0];heapq.heapify(h);r=[]
    while h:
        n=heapq.heappop(h);r.append(n)
        for m in out[n]:
            indeg[m]-=1
            if indeg[m]==0: heapq.heappush(h,m)
    if len(r)!=len(nodes): raise ValueError("cycle")
    return r
"""),

("dijkstra", 2, """Write `shortest_path(graph: dict[str, dict[str, int]], start: str, goal: str) -> tuple[int, list[str]]`.
graph[u][v] is the non-negative weight of a directed edge u->v. Return (total_cost, path) of the cheapest path.
If goal is unreachable return (-1, []). If start == goal return (0, [start]).""",
"""g = {"A": {"B": 1, "C": 4}, "B": {"C": 2, "D": 5}, "C": {"D": 1}, "D": {}}
assert shortest_path(g, "A", "D") == (4, ["A", "B", "C", "D"])
assert shortest_path(g, "D", "A") == (-1, [])
assert shortest_path(g, "B", "B") == (0, ["B"])
assert shortest_path({"X": {"Y": 7}}, "X", "Y") == (7, ["X", "Y"])
""",
"""import heapq
def shortest_path(g,s,t):
    pq=[(0,s,[s])];seen=set()
    while pq:
        c,u,p=heapq.heappop(pq)
        if u==t: return c,p
        if u in seen: continue
        seen.add(u)
        for v,w in g.get(u,{}).items():
            if v not in seen: heapq.heappush(pq,(c+w,v,p+[v]))
    return -1,[]
"""),

("flatten", 2, """Write `flatten(d: dict, sep: str = ".") -> dict` that flattens nested dictionaries into one level with joined
keys, e.g. {"a": {"b": 1, "c": {"d": 2}}, "e": 3} -> {"a.b": 1, "a.c.d": 2, "e": 3}. Lists are values and are not
flattened. An empty nested dict produces no keys.""",
"""assert flatten({"a": {"b": 1, "c": {"d": 2}}, "e": 3}) == {"a.b": 1, "a.c.d": 2, "e": 3}
assert flatten({"x": [1, {"y": 2}]}) == {"x": [1, {"y": 2}]}
assert flatten({"a": {}}) == {}
assert flatten({"a": {"b": 1}}, sep="/") == {"a/b": 1}
""",
"""def flatten(d,sep='.',p=''):
    r={}
    for k,v in d.items():
        key=f"{p}{sep}{k}" if p else k
        if isinstance(v,dict): r.update(flatten(v,sep,key))
        else: r[key]=v
    return r
"""),

("csv_line", 2, '''Write `parse_csv_line(line: str) -> list[str]` that splits one CSV line by commas, honoring double-quoted fields:
commas inside quotes do not split, and a doubled quote "" inside a quoted field means one literal quote.
Do not use the csv module. Example input line:  a,"b,c","say ""hi"""
Expected result: ["a", "b,c", 'say "hi"']''',
r'''assert parse_csv_line('a,"b,c","say ""hi"""') == ["a", "b,c", 'say "hi"']
assert parse_csv_line('1,2,3') == ["1", "2", "3"]
assert parse_csv_line('') == [""]
assert parse_csv_line('a,,b') == ["a", "", "b"]
assert parse_csv_line('"",x') == ["", "x"]
''',
"""def parse_csv_line(s):
    out=[];cur='';q=False;i=0
    while i<len(s):
        c=s[i]
        if q:
            if c=='"':
                if i+1<len(s) and s[i+1]=='"': cur+='"';i+=1
                else: q=False
            else: cur+=c
        else:
            if c=='"': q=True
            elif c==',': out.append(cur);cur=''
            else: cur+=c
        i+=1
    out.append(cur);return out
"""),

("lis", 2, """Write `lis_length(nums: list[int]) -> int` returning the length of the longest strictly increasing subsequence.
It must handle 10 000 elements quickly (O(n log n)).""",
"""assert lis_length([10,9,2,5,3,7,101,18]) == 4
assert lis_length([]) == 0
assert lis_length([7,7,7]) == 1
assert lis_length(list(range(10000))) == 10000
assert lis_length(list(range(10000, 0, -1))) == 1
""",
"""import bisect
def lis_length(a):
    t=[]
    for x in a:
        i=bisect.bisect_left(t,x)
        if i==len(t): t.append(x)
        else: t[i]=x
    return len(t)
"""),

("sudoku", 2, """Write `valid_sudoku(board: list[list[str]]) -> bool` for a 9x9 board of "1".."9" or "." (empty). Return True if
no row, column or 3x3 box contains a repeated digit (the board does not need to be solvable).""",
"""b = [list(r) for r in ["53..7....","6..195...",".98....6.","8...6...3","4..8.3..1","7...2...6",".6....28.","...419..5","....8..79"]]
assert valid_sudoku(b)
b2 = [r[:] for r in b]; b2[0][0] = "8"
assert not valid_sudoku(b2)
b3 = [r[:] for r in b]; b3[1][1] = "9"
assert not valid_sudoku(b3)
assert valid_sudoku([["."]*9 for _ in range(9)])
""",
"""def valid_sudoku(b):
    seen=set()
    for i in range(9):
        for j in range(9):
            v=b[i][j]
            if v=='.': continue
            for k in (('r',i,v),('c',j,v),('b',i//3,j//3,v)):
                if k in seen: return False
                seen.add(k)
    return True
"""),

("calc", 3, """Write `evaluate(expr: str) -> float` that evaluates an arithmetic expression with + - * / , parentheses,
unary minus, decimal numbers and spaces, with normal precedence. Do not use eval/exec. Example: "2*(3+4) - -1" -> 15.""",
"""assert abs(evaluate("2*(3+4) - -1") - 15) < 1e-9
assert abs(evaluate("1 + 2 * 3") - 7) < 1e-9
assert abs(evaluate("(1+2)*3") - 9) < 1e-9
assert abs(evaluate("10 / 4") - 2.5) < 1e-9
assert abs(evaluate("-(2.5*2)") + 5) < 1e-9
assert abs(evaluate("2-3-4") + 5) < 1e-9
assert abs(evaluate("8/2/2") - 2) < 1e-9
""",
"""def evaluate(s):
    s=s.replace(' ','');i=0
    def num():
        nonlocal i
        j=i
        while i<len(s) and (s[i].isdigit() or s[i]=='.'): i+=1
        return float(s[j:i])
    def factor():
        nonlocal i
        if s[i]=='-': i+=1; return -factor()
        if s[i]=='(':
            i+=1; v=expr(); i+=1; return v
        return num()
    def term():
        nonlocal i
        v=factor()
        while i<len(s) and s[i] in '*/':
            op=s[i];i+=1;f=factor();v=v*f if op=='*' else v/f
        return v
    def expr():
        nonlocal i
        v=term()
        while i<len(s) and s[i] in '+-':
            op=s[i];i+=1;t=term();v=v+t if op=='+' else v-t
        return v
    return expr()
"""),

("knapsack", 3, """Write `knapsack(items: list[tuple[int, int]], capacity: int) -> tuple[int, list[int]]`. items[i] = (weight, value).
Each item may be used at most once. Return (best_total_value, sorted list of chosen item indices). If several
selections tie, any one with the maximal value is accepted, but the indices must really achieve that value within
capacity.""",
"""items = [(1, 1), (3, 4), (4, 5), (5, 7)]
v, idx = knapsack(items, 7)
assert v == 9 and sum(items[i][0] for i in idx) <= 7 and sum(items[i][1] for i in idx) == 9 and idx == sorted(idx)
assert knapsack([], 10) == (0, [])
assert knapsack([(5, 10)], 4) == (0, [])
v, idx = knapsack([(2, 3), (2, 3), (3, 5)], 4)
assert v == 6 and sorted(idx) == [0, 1]
""",
"""def knapsack(items,W):
    n=len(items);dp=[[0]*(W+1) for _ in range(n+1)]
    for i,(w,v) in enumerate(items,1):
        for c in range(W+1):
            dp[i][c]=dp[i-1][c]
            if w<=c: dp[i][c]=max(dp[i][c],dp[i-1][c-w]+v)
    c=W;r=[]
    for i in range(n,0,-1):
        if dp[i][c]!=dp[i-1][c]: r.append(i-1);c-=items[i-1][0]
    return dp[n][W],sorted(r)
"""),

("bugfix_median", 3, """The following function should return the median of a non-empty list of numbers without modifying the input
list, but it has bugs. Return a corrected version of `median` (same name and signature).

def median(xs):
    xs.sort()
    n = len(xs)
    if n % 2 == 1:
        return xs[n / 2]
    return (xs[n // 2] + xs[n // 2 + 1]) / 2
""",
"""a = [3, 1, 2]
assert median(a) == 2 and a == [3, 1, 2]
assert median([4, 1, 3, 2]) == 2.5
assert median([5]) == 5
assert median([1.5, -1.5]) == 0
""",
"""def median(xs):
    s=sorted(xs);n=len(s)
    if n%2: return s[n//2]
    return (s[n//2-1]+s[n//2])/2
"""),

("bugfix_account", 3, """This class has bugs. Fix it so that: deposit/withdraw reject non-positive amounts with ValueError,
withdraw raises ValueError("insufficient funds") when the balance is too small (balance must stay unchanged),
and history is a list of ("deposit"|"withdraw", amount) tuples that is separate for every account. Return the
corrected class `Account`.

class Account:
    def __init__(self, owner, history=[]):
        self.owner = owner
        self.balance = 0
        self.history = history
    def deposit(self, amount):
        self.balance += amount
        self.history.append(("deposit", amount))
    def withdraw(self, amount):
        self.balance -= amount
        if self.balance < 0:
            raise ValueError("insufficient funds")
        self.history.append(("withdraw", amount))
""",
"""a = Account("ann"); b = Account("bob")
a.deposit(100); a.withdraw(30)
assert a.balance == 70 and a.history == [("deposit", 100), ("withdraw", 30)]
assert b.history == [] and b.balance == 0
try:
    a.withdraw(1000); raise SystemExit("no error")
except ValueError as e:
    assert "insufficient" in str(e)
assert a.balance == 70
for bad in (0, -5):
    try:
        a.deposit(bad); raise SystemExit("no error")
    except ValueError:
        pass
assert a.balance == 70 and len(a.history) == 2
""",
"""class Account:
    def __init__(self,owner,history=None):
        self.owner=owner;self.balance=0;self.history=[] if history is None else history
    def deposit(self,a):
        if a<=0: raise ValueError("amount must be positive")
        self.balance+=a;self.history.append(("deposit",a))
    def withdraw(self,a):
        if a<=0: raise ValueError("amount must be positive")
        if a>self.balance: raise ValueError("insufficient funds")
        self.balance-=a;self.history.append(("withdraw",a))
"""),

("date_diff", 3, """Write `workdays_between(start: str, end: str, holidays: list[str]) -> int` counting working days (Mon-Fri,
excluding the given holiday dates) in the inclusive range start..end. Dates are "YYYY-MM-DD". If end < start
return 0. Use only the standard library.""",
"""assert workdays_between("2026-09-28", "2026-10-04", []) == 5
assert workdays_between("2026-09-28", "2026-10-04", ["2026-09-30"]) == 4
assert workdays_between("2026-10-03", "2026-10-04", []) == 0
assert workdays_between("2026-10-05", "2026-10-01", []) == 0
assert workdays_between("2026-01-01", "2026-12-31", []) == 261
""",
"""from datetime import date,timedelta
def workdays_between(s,e,h):
    a=date.fromisoformat(s);b=date.fromisoformat(e);hs=set(h);n=0
    while a<=b:
        if a.weekday()<5 and a.isoformat() not in hs: n+=1
        a+=timedelta(days=1)
    return n
"""),

("tokenize_words", 3, """Write `top_words(text: str, k: int) -> list[tuple[str, int]]` returning the k most frequent words. Words are
case-insensitive sequences of letters (any alphabet, including Cyrillic) and apostrophes inside a word ("don't").
Sort by count descending, then alphabetically. Example: top_words("Мир мир, world! World's end", 2) ->
[("мир", 2), ("end", 1)].""",
"""assert top_words("Мир мир, world! World's end", 2) == [("мир", 2), ("end", 1)]
assert top_words("a b a c b a", 2) == [("a", 3), ("b", 2)]
assert top_words("don't Don't stop", 1) == [("don't", 2)]
assert top_words("", 3) == []
assert top_words("x1y z", 5) == [("x", 1), ("y", 1), ("z", 1)]
""",
"""import re
from collections import Counter
def top_words(t,k):
    ws=re.findall(r"[^\\W\\d_]+(?:'[^\\W\\d_]+)*",t.lower())
    return sorted(Counter(ws).items(),key=lambda x:(-x[1],x[0]))[:k]
"""),
]
