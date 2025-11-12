import re

time_re = re.compile(r'^.*?(\d{2}):(\d{2}):(\d{2}),(\d{3})')

def parse_hora(linea):
    match = time_re.search(linea)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        segs = h*3600 + m*60 + s
        return segs, f"{match.group(1)}:{match.group(2)}:{match.group(3)},{match.group(4)}"
    return None, None

def segs_a_hora(segundos):
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

