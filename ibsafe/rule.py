import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Set

# === Canonical allergy types you can pass in `allergies` ===
ALLERGY_CANON = [
    "글루텐 알러지",
    "유당 알러지",
    "견과류 알러지",
    "해산물 알러지",
    "계란 알러지",
    "대두 알러지",
]

def _canon_allergies(allergies: List[str]) -> Set[str]:
    """
    Normalize allergy names to the canonical set (exact or fuzzy match).
    Examples accepted:
      - "글루텐", "글루텐 알러지" -> "글루텐 알러지"
      - "대두", "콩 알러지", "대두 알러지" -> "대두 알러지"
    """
    out = set()
    for x in allergies or []:
        x = (x or "").strip()
        if not x:
            continue
        for key in ALLERGY_CANON:
            if x == key or x in key or key in x:
                out.add(key)
    return out

def _parse_allergy_cell(cell: str) -> Set[str]:
    """Split the 엑셀의 '알러지_tag' 셀 -> set. '해당 없음'이면 empty set."""
    if not isinstance(cell, str) or not cell.strip() or cell.strip() == "해당 없음":
        return set()
    parts = [p.strip() for p in cell.split(",")]
    return set(p for p in parts if p)

def _exclude_recent_and_dislikes(
    df: pd.DataFrame,
    recent_list: List[str],
    dislikes: List[str]
) -> pd.Series:
    """True=keep. 최근 3일 섭취(정확 일치) 제외 + 기피 키워드(부분 일치) 제외"""
    recent_set = set([s.strip() for s in (recent_list or []) if isinstance(s, str) and s.strip()])
    not_recent = ~df["food"].isin(recent_set)

    if dislikes:
        # Escape regex special chars
        import re
        dislike_terms = [re.escape(k.strip()) for k in dislikes if k and isinstance(k, str)]
        pat = "|".join(dislike_terms)
        not_disliked = ~df["food"].str.contains(pat, na=False)
    else:
        not_disliked = pd.Series(True, index=df.index)

    return not_recent & not_disliked

def _exclude_allergies(
    df: pd.DataFrame,
    allergies: List[str]
) -> pd.Series:
    """True=keep. Row의 알러지_tag와 요청 알러지 집합이 교집합이면 제외."""
    want = _canon_allergies(allergies)
    if not want:
        return pd.Series(True, index=df.index)
    row_sets = df["알러지_tag"].apply(_parse_allergy_cell)
    return ~row_sets.apply(lambda s: bool(s & want))

def recommend_diet(
    excel_path: str,
    recent_3days: Optional[List[str]]=None,
    allergies: Optional[List[str]]=None,
    restrictions: Optional[List[str]]=None,
    random_seed: int = 42
) -> Dict[str, List[str]]:
    
    CATEGORY_RULE = {
    "아침": {"밥류": 2, "죽류": 2, "국/찌개/탕": 3, "반찬/나물/무침": 4},
    "점심": {"밥류": 2, "면/국수": 2, "국/찌개/탕": 2, "단백질/메인(육·해산물)": 4},
    "저녁": {"밥류": 2, "죽류": 1, "국/찌개/탕": 2, "단백질/메인(육·해산물)": 4},
}
    rng = np.random.default_rng(random_seed)
    df = pd.read_excel(excel_path)
    
    # --- 기존 필터링 (최근 3일, 알러지, 기피) 적용 ---
    #from rule_based_recommender import _exclude_recent_and_dislikes, _exclude_allergies
    keep = _exclude_recent_and_dislikes(df, recent_3days or [], restrictions or [])
    keep &= _exclude_allergies(df, allergies or [])
    df = df[keep].copy()

    # --- 끼니별 추천 ---
    result = {"아침": [], "점심": [], "저녁": []}
    used = set()

    for meal, rules in CATEGORY_RULE.items():
        picks = []
        for cat, n in rules.items():
            pool = df[(df["category"]==cat) & (~df["food"].isin(used))]["food"].unique().tolist()
            if len(pool) == 0:
                continue
            chosen = rng.choice(pool, size=min(len(pool), n), replace=False)
            chosen = [str(x) for x in chosen]
            picks.extend(chosen)
            used.update(chosen)
        result[meal] = picks

    return result


def recommend_sleep(hours: float) -> str:
    if hours <= 4:
        return "수면 시간이 매우 부족했습니다. 오늘은 가능하면 일찍 잠자리에 들어서 최소 7시간 이상 자도록 해보세요."
    elif hours <= 6:
        return "충분하지 않은 수면 시간이었습니다. 조금 더 자는 습관을 만들어 7–8시간 정도로 늘려보세요."
    elif hours <= 8:
        return "적절한 수면 시간을 확보했습니다. 이 패턴을 유지하는 것이 IBS 증상 완화에도 도움됩니다."
    elif hours <= 10:
        return "평균보다 긴 수면 시간을 가졌습니다. 너무 과한 수면은 장 리듬에 영향을 줄 수 있으니 7–8시간 정도로 줄이는 것이 좋습니다."
    else:
        return "과도하게 오래 잤습니다. 지나치게 긴 수면은 오히려 피로감이나 증상 악화를 유발할 수 있으니 일찍 일어나도록 해보세요."
    


from typing import List, Dict, Any, Tuple
import math

def _safe_stats(xs: List[float]) -> Dict[str, float]:
    xs = [float(x) for x in xs if x is not None]
    n = len(xs)
    if n == 0:
        return {"n":0,"mean":0.0,"std":0.0,"min":0.0,"max":0.0,"median":0.0}
    mean = sum(xs)/n
    var = sum((x-mean)**2 for x in xs)/n
    std = var**0.5
    xs_sorted = sorted(xs)
    median = xs_sorted[n//2] if n%2==1 else (xs_sorted[n//2-1]+xs_sorted[n//2])/2
    return {"n": n, "mean": mean, "std": std, "min": min(xs), "max": max(xs), "median": median}

def _rmssd(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    diffs = [(xs[i+1]-xs[i]) for i in range(len(xs)-1)]
    return (sum(d*d for d in diffs)/len(diffs))**0.5

def _max_consecutive(xs: List[int], predicate) -> int:
    best = cur = 0
    for v in xs:
        if predicate(v):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best

def _band_count(xs: List[int], low: int, high: int) -> int:
    return sum(1 for v in xs if low <= v <= high)

def _clip(a: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, a))


def recommend_step(steps: List[int], target: int = 6000) -> Tuple[str, str]:
    """
    입력: 최근 7일 걸음수 리스트(정수). 길이가 7 미만이면 앞을 0으로 채움.
    출력: (이번주 걸음수 평가, 내일의 목표 걸음수)
         - 평가: 숫자 없이 '규칙성 + 목표 대비 수준 + 권고' 자연어 문장 1개
         - 목표: '내일의 목표 걸음수: 7,000보' 형식 1개
    규칙성 판단은 '변동성(CV) 기준'만 사용하고, 목표 대비 평가는 별도로 함.
    """
    if not steps:
        raise ValueError("steps must be a non-empty list of integers.")
    xs = [max(0, int(v)) for v in steps[-7:]]
    n = len(xs)
    if n <= 3:
        today = xs[-1]
        if today < target*0.5:
            level = "매우 낮음"; eval_txt = "목표 걸음수 대비 크게 미달했습니다"; action = "더 많이 걸으세요"
        elif today < target*0.85:
            level = "낮음";     eval_txt = "목표 걸음수 대비 미비했습니다";       action = "조금 더 걸음을 늘려보세요"
        elif today < target*1.1:
            level = "적정";     eval_txt = "목표 범위에 근접했습니다";           action = "현재 수준을 유지해 보세요"
        else:
            level = "높음";     eval_txt = "목표를 잘 달성했습니다";             action = "무리하지 않도록 안정적으로 유지해 보세요"

        # 내일 목표(500보 단위, 증량 상한 = 오늘 + min(10%, 1500))
        propose = (
            min(target, max(4000, int(round(today/500)*500 + 1000)))
            if level in ("매우 낮음","낮음") else (7000 if level=="적정" else 8000)
        )
        cap_inc = min(int(today*0.10), 1500)
        base = min(propose, int(today + cap_inc)) if today > 0 else propose
        base = max(4000, min(10000, int(round(base/500)*500)))

        eval_sentence = f"이번 주 데이터가 부족하여 오늘 기준으로 평가합니다. 오늘은 {eval_txt}. {action}."
        target_step = f"{base}"
        return eval_sentence, target_step

    # 통계/지표

    mean = sum(xs)/n
    var  = sum((v-mean)**2 for v in xs)/n
    std  = var**0.5
    cv   = (std/(mean+1e-9)) if mean > 0 else 1.0
    band_low, band_high = int(target*0.8), int(target*1.2)   # 목표 ±20% (목표 관련 보정에만 활용)
    within_band = sum(1 for v in xs if band_low <= v <= band_high)
    avg3d = sum(xs[-3:])/3 if n >= 3 else mean

    # --- 목표 대비 수준 라벨 ---
    if mean < target*0.5:      level = "매우 낮음"
    elif mean < target*0.85:   level = "낮음"
    elif mean < target*1.1:    level = "적정"
    else:                      level = "높음"

    # --- 규칙성 라벨(★ CV만으로 판단) ---
    # 매우 규칙적: CV ≤ 0.15 / 규칙적: CV ≤ 0.30 / 다소 불규칙: CV ≤ 0.50 / 불규칙: 그 외
    if cv <= 0.15:             reg = "매우 규칙적"
    elif cv <= 0.30:           reg = "규칙적"
    elif cv <= 0.50:           reg = "다소 불규칙"
    else:                      reg = "불규칙"

    # --- 내일 목표 산정(500보 단위, 안전 상한: 최근3일평균 + min(10%, 1500)) ---
    if level in ("매우 낮음", "낮음"):
        base = min(target, max(4000, int(round(avg3d/500)*500 + 1000)))
    elif level == "적정":
        base = 7000
    else:  # 높음
        base = 8000

    # 규칙성 나쁠 때 과도한 목표 방지
    if reg in ("불규칙", "다소 불규칙"):
        base = max(5500, min(7500, base))
    # 목표 밴드에 거의 못 들어간 주는 상한 7천으로
    if within_band < 3:
        base = min(base, 7000)

    # 증량 상한
    if avg3d > 0:
        cap_inc = min(int(avg3d * 0.10), 1500)
        base = min(base, int(avg3d + cap_inc))

    # 범위/반올림
    base = max(4000, min(10000, base))
    base = int(round(base/500)*500)

    # --- 자연어 문장 (대조 + 맞춤 마무리) ---
    reg_bad = reg in ("불규칙", "다소 불규칙")
    level_good = level in ("적정", "높음")
    level_bad  = level in ("매우 낮음", "낮음")

    reg_phrase = {
        "매우 규칙적": "매우 규칙적입니다",
        "규칙적": "규칙적입니다",
        "다소 불규칙": "규칙적이지 못했습니다",
        "불규칙": "규칙적이지 못했습니다",
    }[reg]

    level_phrase_plain = {
        "매우 낮음": "목표 걸음수 대비 크게 미달합니다",
        "낮음": "목표 걸음수 대비 미비합니다",
        "적정": "목표 범위에 근접합니다",
        "높음": "목표를 잘 달성했습니다",
    }[level]
    level_phrase_contrast = {
        "적정": "평균적으로 목표 범위에는 근접했습니다",
        "높음": "평균적으로 목표를 잘 달성했습니다",
    }

    action_phrase_default = {
        "매우 낮음": "더 많이 걸으셔야 합니다",
        "낮음": "조금 더 걸음을 늘려보세요",
        "적정": "현재 수준을 유지해 보세요",
        "높음": "무리하지 않도록 안정적으로 유지해 보세요",
    }[level]

    # 규칙성 나쁠 때 마무리 문구
    if reg_bad and level_good:
        closing = "꾸준하게 걸으세요"
    elif reg_bad and level_bad:
        closing = "더 많이 꾸준하게 걸으세요"
    else:
        closing = action_phrase_default

    if reg_bad and level_good:
        eval_sentence = f"이번 주는 {reg_phrase}. 하지만 {level_phrase_contrast.get(level, level_phrase_plain)}. {closing}."
    elif (not reg_bad) and level_bad:
        eval_sentence = f"이번 주는 {reg_phrase}. 하지만 {level_phrase_plain}. {closing}."
    else:
        eval_sentence = f"이번 주는 {reg_phrase}. 또한 {level_phrase_plain}. {closing}."

    target_step = f"{base}"
    return eval_sentence, target_step

