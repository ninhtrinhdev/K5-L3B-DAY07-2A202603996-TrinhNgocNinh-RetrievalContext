"""Build the bonus benchmark (World health statistics 2023) and verify every evidence against the chunks.

Outputs (bonus/data):
  questions.json     all questions (dev + test), Day 7 schema + bonus extensions:
     group         table | image | chart | multihop | text | unanswerable   (one primary group per question)
     gold          list of evidence items; `gold_mode` = "any" (alternatives) or "all" (multi-hop: every item required)
     gold[i]       {source_id, page, chunk_id, evidence, locator}
                   evidence = exact substring of the chunk (for figures: the caption, which identifies the figure chunk)
                   locator  = where a human checks it (table row/column, figure crop file + what to read)
     calc          arithmetic used, if any
  benchmark_report.json  counts per split/group + verification results
No retrieval is run here. Questions were written by reading the source (text chunks, table rows, figure crops)
BEFORE any retrieval experiment; test questions must never be used for tuning.
"""
import hashlib
import json
import re
from collections import Counter

import common

chunks = json.loads((common.DATA / "chunks.json").read_text(encoding="utf-8"))
by_id = {c["id"]: c for c in chunks}
figs = {f["figure"]: f for f in json.loads((common.DATA / "figures.json").read_text(encoding="utf-8"))}
SRC = common.CORPUS
Q = []


def text_ev(snippet, locator="đoạn văn"):
    hits = [c for c in chunks if c["metadata"]["kind"] == "text" and snippet in c["text"]]
    assert len(hits) >= 1, f"text evidence not found: {snippet[:60]}"
    c = hits[0]
    return {"source_id": SRC, "page": c["page"], "chunk_id": c["id"], "evidence": snippet, "locator": f"tr. {c['page']}, {locator}"}


def row_ev(page, country, column, must_contain):
    """Evidence = the full markdown row of `country` on `page`; `must_contain` values are asserted to be in that row."""
    for c in chunks:
        if c["page"] == page and c["metadata"]["kind"] == "table":
            for line in c["text"].split("\n"):
                if line.startswith(f"| {country} |"):
                    for v in must_contain:
                        assert f"| {v} |" in line or f"| {v} " in line, (country, v, line)
                    return {"source_id": SRC, "page": page, "chunk_id": c["id"], "evidence": line,
                            "locator": f"tr. {page}, bảng annex, hàng '{country}', cột '{column}'"}
    raise AssertionError(f"row not found: {country} p{page}")


def fig_ev(number, reading, in_text_layer=()):
    f = figs[number]
    c = by_id[f["id"]]
    assert f["caption"] in c["text"]
    for v in in_text_layer:  # values that are printed as text inside the figure (sanity check of the reading)
        assert v in c["text"], (number, v)
    return {"source_id": SRC, "page": f["page"], "chunk_id": f["id"], "evidence": f["caption"],
            "locator": f"tr. {f['page']}, Figure {number}, crop {f['crop']}: {reading}"}


def add(qid, split, group, question, answer, gold, mode="any", calc=None):
    item = {"id": qid, "split": split, "group": group, "question": question, "expected_answer": answer,
            "answerable": True, "expected_behavior": "search_and_answer", "gold_mode": mode, "gold": gold}
    if calc:
        item["calc"] = calc
    Q.append(item)


def absent(qid, split, question, keywords, reason):
    hits = {k: sorted({c["page"] for c in chunks if re.search(re.escape(k), c["text"], re.I)}) for k in keywords}
    Q.append({"id": qid, "split": split, "group": "unanswerable", "question": question, "answerable": False,
              "expected_behavior": "search_and_abstain", "absence_reason": reason, "absence_check": {"keywords": hits}})


# ============================== DEV (15 answerable + 3 unanswerable) ==============================
add("d-tb1", "dev", "table", "What was life expectancy at birth for males and for females in Mali in 2019?",
    "Male 62.2 years, female 63.4 years (2019).", [row_ev(100, "Mali", "Life expectancy at birth, Male/Female, 2019", ["62.2", "63.4"])])
add("d-tb2", "dev", "table", "What was the suicide mortality rate in Afghanistan in 2019?",
    "4.1 per 100 000 population (2019).", [row_ev(104, "Afghanistan", "Suicide mortality rate (per 100 000 population), 2019", ["4.1"])])
add("d-tb3", "dev", "table", "What was the prevalence of stunting in children under 5 in Viet Nam in 2022?",
    "19.3% (2022).", [row_ev(126, "Viet Nam", "Prevalence of stunting in children under 5 (%), 2022", ["19.3"])])

add("d-im1", "dev", "image", "According to the timeline of 75 years of public health, in which year did WHO found the Expanded Programme on Immunization?",
    "1974.", [fig_ev("3.3", "mốc 1974: 'WHO founds the Expanded Programme on Immunization'", ["1974", "Expanded Programme"])])
add("d-im2", "dev", "image", "In the diagram of countries affected by multiple forms of malnutrition in 2022, how many countries crossed only the stunting threshold?",
    "21 countries.", [fig_ev("2.10", "vùng 'Stunting': 21 countries only crossed stunting threshold", ["21 countries only crossed"])])
add("d-im3", "dev", "image", "On the map of national health and climate change plans or strategies in 2021, what status is shown for Canada?",
    "No (no national health and climate change plan or strategy in place).", [fig_ev("1.16", "Canada tô màu xanh đậm = 'No' theo chú giải", ["Under development"])])

add("d-ch1", "dev", "chart", "Globally, what percentage of people living with HIV knew their status in 2015 and in 2021?",
    "69% in 2015 and 85% in 2021.", [fig_ev("2.20", "panel a, cột xanh nhạt: 2015 = 69, 2021 = 85", ["69", "85"])])
add("d-ch2", "dev", "chart", "What was the average annual rate of reduction (ARR) of the global under-five mortality rate in 2000-2010 and in 2010-2021?",
    "4.0% in 2000-2010 and 2.7% in 2010-2021.", [fig_ev("1.4", "nhãn ARR trên đường U5MR: 4.0% (2000-2010), 2.7% (2010-2021)", ["4.0%", "2.7%"])])
add("d-ch3", "dev", "chart", "In the European Region in 2020, what proportion of the population used safely-managed drinking-water services and safely-managed sanitation services?",
    "92% drinking-water and 70% sanitation.", [fig_ev("2.13", "European Region: cột xanh dương 92, cột xanh lá 70", ["92", "70"])])

add("d-mh1", "dev", "multihop", "For Mali, what are life expectancy at birth for both sexes (2019) and the maternal mortality ratio (2020)?",
    "Life expectancy 62.8 years (2019); maternal mortality ratio 440 per 100 000 live births (2020).",
    [row_ev(100, "Mali", "Life expectancy at birth, Both sexes, 2019", ["62.8"]),
     row_ev(101, "Mali", "Maternal mortality ratio (per 100 000 live births), 2020", ["440"])], mode="all")
add("d-mh2", "dev", "multihop", "How much higher was Afghanistan's maternal mortality ratio in 2020 than the global ratio that year?",
    "Afghanistan 620 vs global 223 per 100 000 live births: 397 higher (about 2.8 times).",
    [row_ev(97, "Afghanistan", "Maternal mortality ratio (per 100 000 live births), 2020", ["620"]),
     text_ev("223 (UI: 202–255) deaths per 100 000 live births that year")], mode="all", calc="620 - 223 = 397; 620 / 223 = 2.78")
add("d-mh3", "dev", "multihop", "How many children under 5 were affected by stunting globally in 2022, and how many countries crossed only the stunting threshold in the malnutrition diagram?",
    "148.1 million children; 21 countries.",
    [fig_ev("2.7", "biểu đồ phải, đường Stunting, nhãn 2022 = 148.1", ["148.1"]),
     fig_ev("2.10", "vùng 'Stunting': 21", ["21 countries only crossed"])], mode="all")

add("d-tx1", "dev", "text", "How did the global age-standardized prevalence of current tobacco use change between 2000 and 2020?",
    "It fell by over 30%, from 32.7% in 2000 to 22.3% in 2020.", [text_ev("has declined by over 30% – from 32.7% in 2000 to 22.3% in 2020")])
add("d-tx2", "dev", "text", "How did the average implementation status of IHR core capacities change from 2021 to 2022?",
    "It increased from 64% in 2021 to 66% in 2022.", [text_ev("increased from 64% in 2021 to 66% in 2022")])
add("d-tx3", "dev", "text", "Was anaemia prevalence higher among pregnant or non-pregnant women aged 15-49, and what were the values?",
    "Higher among pregnant women: 36.5% versus 29.6% in non-pregnant women.", [text_ev("Prevalence was higher among pregnant women [36.5% (UI: 34.0–39.1)] than non-pregnant women [29.6%")])

absent("d-na1", "dev", "How many mpox (monkeypox) cases were reported globally in 2022?", ["mpox", "monkeypox"],
       "Không có 'mpox'/'monkeypox' trong bất kỳ chunk nào (text, bảng, hình) của 136 trang.")
absent("d-na2", "dev", "What is the density of hospital beds per 10 000 population in Brazil?", ["hospital bed", "beds per"],
       "Bảng annex (tr. 113-119) chỉ có mật độ bác sĩ, điều dưỡng/hộ sinh, nha sĩ, dược sĩ; không có giường bệnh.")
absent("d-na3", "dev", "What is the prevalence of e-cigarette use among adolescents?", ["e-cigarette", "vaping", "electronic cigarette"],
       "Phần thuốc lá (tr. 24-25, Fig 1.9, annex 3.a) chỉ nói 'current tobacco use' ở người từ 15 tuổi; không có thuốc lá điện tử.")

# ============================== TEST (24 answerable + 6 unanswerable) ==============================
add("t-tb1", "test", "table", "In Mongolia, how many years longer was female than male life expectancy at birth in 2019?",
    "9.0 years (female 72.8, male 63.8).", [row_ev(100, "Mongolia", "Life expectancy at birth, Male/Female, 2019", ["63.8", "72.8"])], calc="72.8 - 63.8 = 9.0")
add("t-tb2", "test", "table", "What proportion of births in Brazil were attended by skilled health personnel?",
    "98% (primary data, 2013-2022).", [row_ev(97, "Brazil", "Proportion of births attended by skilled health personnel (%), 2013-2022", ["98"])])
add("t-tb3", "test", "table", "For Afghanistan, what were the age-standardized prevalence of tobacco use (2020) and DTP3 immunization coverage among 1-year-olds (2021)?",
    "Tobacco use 23.3% (2020); DTP3 coverage 66% (2021).", [row_ev(112, "Afghanistan", "Tobacco use prevalence 2020; DTP3 coverage 2021", ["23.3", "66"])])
add("t-tb4", "test", "table", "What was the total population (both sexes) of Thailand in 2021?",
    "71 601 thousand (about 71.6 million) in 2021.", [row_ev(102, "Thailand", "Total population (000s), Both sexes, 2021", ["71 601"])])
add("t-tb5", "test", "table", "By how many percentage points was the prevalence of anaemia in women of reproductive age higher in Afghanistan than in Brazil in 2019?",
    "26.5 percentage points (Afghanistan 42.6%, Brazil 16.1%).",
    [row_ev(120, "Afghanistan", "Prevalence of anaemia in women of reproductive age (%), 2019", ["42.6"]),
     row_ev(120, "Brazil", "Prevalence of anaemia in women of reproductive age (%), 2019", ["16.1"])], mode="all", calc="42.6 - 16.1 = 26.5")
add("t-tb6", "test", "table", "What was healthy life expectancy at birth for both sexes in Viet Nam in 2019?",
    "65.3 years (2019).", [row_ev(102, "Viet Nam", "Healthy life expectancy at birth, Both sexes, 2019", ["65.3"])])

add("t-im1", "test", "image", "According to the timeline of 75 years of public health, what did the World Health Assembly adopt in 2003?",
    "The WHO Framework Convention on Tobacco Control, WHO's first global public health treaty.",
    [fig_ev("3.3", "mốc 2003: WHA adopts the WHO Framework Convention on Tobacco Control", ["2003", "Framework Convention on Tobacco"])])
add("t-im2", "test", "image", "In the diagram of countries affected by multiple forms of malnutrition in 2022, how many countries crossed both the stunting and anaemia thresholds (and no other)?",
    "17 countries.", [fig_ev("2.10", "vùng giao Stunting-Anaemia: 17 countries crossed stunting and anaemia thresholds", ["17 countries crossed stunting"])])
add("t-im3", "test", "image", "On the world map of maternal mortality ratio by country in 2020, what are the highest and the lowest legend classes?",
    "Highest class: 1000 or more per 100 000 live births; lowest class: below 20.",
    [fig_ev("1.2", "chú giải: lớp cao nhất '≥1000', thấp nhất '<20' (per 100 000 live births)", ["1000", "<20"])])
add("t-im4", "test", "image", "On the map of under-five and neonatal mortality by country in 2021, what do the circles represent and what value does the largest legend circle stand for?",
    "The circles show the neonatal mortality rate (per 1000 live births); the largest legend circle is 40.",
    [fig_ev("1.6", "chú giải: vòng tròn = Neonatal mortality rate (per 1000 live births), vòng lớn nhất = 40", ["Neonatal mortality rate", "40"])])
add("t-im5", "test", "image", "On the map of national health and climate change plans or strategies in 2021, what status is shown for China?",
    "Yes (a national health and climate change plan or strategy is in place).", [fig_ev("1.16", "China tô màu đỏ sẫm = 'Yes' theo chú giải", ["Under development"])])

add("t-ch1", "test", "chart", "In the Eastern Mediterranean Region in 2021, what percentages of people living with HIV knew their status, were on treatment and were virally suppressed?",
    "41% knew their status, 27% were on treatment and 24% were virally suppressed.", [fig_ev("2.20", "panel b, Eastern Mediterranean Region: 41 / 27 / 24", ["41", "27", "24"])])
add("t-ch2", "test", "chart", "How did the global prevalence of stunting in children under 5 change between 2000 and 2022?",
    "It fell from 33.0% in 2000 to 22.3% in 2022.", [fig_ev("2.7", "biểu đồ trái, đường Stunting: 33.0 (2000) -> 22.3 (2022)", ["33.0", "22.3"])])
add("t-ch3", "test", "chart", "In the Region of the Americas, how many of the total excess deaths in 2020-2021 were reported COVID-19 deaths?",
    "2.4 million reported COVID-19 deaths out of 3.2 million total excess deaths.",
    [fig_ev("1.13", "Region of the Americas: tổng 3.2, phần xanh 'Reported COVID-19' = 2.4 (nhãn in trong hình là '2,4')", ["3.2", "2,4"])])
add("t-ch4", "test", "chart", "What was the prevalence of current tobacco use among males in the South-East Asia Region in 2000 and in 2020?",
    "68.2% in 2000 and 46.6% in 2020.", [fig_ev("1.9", "hàng Male, South-East Asia Region: 68.2 (2000), 46.6 (2020)", ["68.2", "46.6"])])
add("t-ch5", "test", "chart", "In the African Region in 2020, what proportion of the population used safely-managed drinking-water, safely-managed sanitation and a hand-washing facility with soap and water?",
    "32% drinking-water, 23% sanitation and 28% hand-washing facility.", [fig_ev("2.13", "African Region: 32 / 23 / 28", ["32", "23", "28"])])

add("t-mh1", "test", "multihop", "For Mexico, what are life expectancy at birth for both sexes (2019) and the under-five mortality rate (2021)?",
    "Life expectancy 76.0 years (2019); under-five mortality rate 13 per 1000 live births (2021).",
    [row_ev(100, "Mexico", "Life expectancy at birth, Both sexes, 2019", ["76.0"]),
     row_ev(101, "Mexico", "Under-five mortality rate (per 1000 live births), 2021", ["13"])], mode="all")
add("t-mh2", "test", "multihop", "In the Region of the Americas, what were the prevalence of adult obesity in 2016 and the prevalence of adult hypertension in 2019?",
    "Obesity 28.6% (2016); hypertension 35.4% (2019).",
    [text_ev("was in the Americas where 28.6% (UI: 26.6–30.5%) of adults were obese"),
     text_ev("the Americas at 35.4% (UI: 33.3–37.6%)")], mode="all")
add("t-mh3", "test", "multihop", "What was the average annual rate of reduction of the global under-five mortality rate in 2010-2021, and how many countries will miss the SDG under-five mortality target if that trend continues?",
    "ARR 2.7% in 2010-2021; 54 countries will not meet the SDG target for under-five mortality.",
    [fig_ev("1.4", "nhãn ARR trên đường U5MR giai đoạn 2010-2021 = 2.7%", ["2.7%"]),
     text_ev("54 countries will not meet the SDG target for U5MR")], mode="all")
add("t-mh4", "test", "multihop", "For Brazil, what are the density of medical doctors and the UHC service coverage index?",
    "21.4 medical doctors per 10 000 population (2013-2021); UHC service coverage index 80 (2021).",
    [row_ev(113, "Brazil", "Density of medical doctors (per 10 000 population), 2013-2021", ["21.4"]),
     row_ev(105, "Brazil", "UHC: Service coverage index, 2021", ["80"])], mode="all")

add("t-tx1", "test", "text", "What share of adults globally were obese in 2016, and how did that compare with 2000?",
    "13.1% in 2016, up from 8.7% in 2000.", [text_ev("In 2016, 13.1% (UI: 12.4–13.9%) of adults globally were obese, up from 8.7% (UI: 8.4–9.0) in 2000")])
add("t-tx2", "test", "text", "How many excess deaths globally could be attributed to the COVID-19 pandemic by the end of 2021?",
    "14.9 million (95% UI: 13.3-16.6 million).", [text_ev("14.9 million (95% UI: 13.3–16.6 million) excess deaths could be attributed to the COVID-19 pandemic by the end of 2021")])
add("t-tx3", "test", "text", "Since 2016, for how many countries has the availability and affordability of a core set of essential medicines been estimated, and what was the median value?",
    "17 countries (in the African, Americas and European regions), with a median of 15% (IQR: 0-28%).",
    [text_ev("has been estimated for 17 countries across WHO’s African, Americas and European regions, with a median value across all 17 countries of 15% (IQR: 0–28%)")])
add("t-tx4", "test", "text", "What was the global male-to-female ratio of tobacco use prevalence in 2020, and how had it changed since 2000?",
    "4.7 in 2020, up from 3.0 in 2000.", [text_ev("The male-to-female ratio at global level was 4.7 in 2020, rising from 3.0 in 2000")])

absent("t-na1", "test", "How many cholera cases were reported worldwide in 2022?", ["cholera"],
       "'cholera' không xuất hiện trong tài liệu; phần bệnh truyền nhiễm chỉ bàn HIV, lao, sốt rét, viêm gan, NTD.")
absent("t-na2", "test", "What was life expectancy at birth in Viet Nam in 2022?", ["life expectancy in 2022", "2022 life expectancy"],
       "Bảng annex (tr. 102) chỉ có tuổi thọ của Viet Nam năm 2019 (73.7); không có số liệu 2022. Trả lời đạt khi nêu rõ không có số 2022 (có thể nhắc số 2019 kèm năm).")
absent("t-na3", "test", "What is the global yellow fever vaccination coverage?", ["yellow fever"],
       "'yellow fever' không xuất hiện; phần tiêm chủng (Fig 2.18, annex 3.b) chỉ có DTP3, MCV2, PCV3, HPV.")
absent("t-na4", "test", "How many people died from drowning worldwide in 2019?", ["drowning"],
       "'drowning' không xuất hiện; phần thương tích (tr. 62-63, Fig 2.11-2.12, 2.17) chỉ có tai nạn giao thông, tự tử, giết người, ngộ độc không chủ ý.")
absent("t-na5", "test", "What is the current health expenditure per capita in Brazil?", ["expenditure per capita", "health expenditure per capita"],
       "Bảng annex (tr. 105, 113) chỉ có tỷ lệ dân có chi tiêu y tế hộ gia đình >10%/>25% và chi tiêu y tế công trong tổng chi chính phủ; không có chi tiêu y tế bình quân đầu người.")
absent("t-na6", "test", "What is the global prevalence of chronic hepatitis C infection?", ["hepatitis C", "HCV"],
       "'hepatitis C' không xuất hiện; tài liệu chỉ báo cáo viêm gan B (tr. 54-55, Fig 2.6, annex HBsAg).")

# ============================== verify + write ==============================
ids = [q["id"] for q in Q]
assert len(ids) == len(set(ids))
problems = []
for q in Q:
    if q["answerable"]:
        for g in q["gold"]:
            c = by_id[g["chunk_id"]]
            if not (g["evidence"] in c["text"] and c["page"] == g["page"] and c["source_id"] == g["source_id"]):
                problems.append((q["id"], g["chunk_id"]))
    else:
        found = {k: p for k, p in q["absence_check"]["keywords"].items() if p}
        if found:
            problems.append((q["id"], "keyword present", found))
dev_q = {q["question"].casefold() for q in Q if q["split"] == "dev"}
test_q = {q["question"].casefold() for q in Q if q["split"] == "test"}
assert not dev_q & test_q
counts = Counter((q["split"], q["group"]) for q in Q)
need = {("test", "table"): 6, ("test", "image"): 5, ("test", "chart"): 5, ("test", "multihop"): 4, ("test", "text"): 4, ("test", "unanswerable"): 6}
for k, n in need.items():
    assert counts[k] >= n, (k, counts[k])
assert sum(1 for q in Q if q["split"] == "dev" and q["answerable"]) >= 15 and counts[("dev", "unanswerable")] >= 3
test_hash = hashlib.sha256(json.dumps([q for q in Q if q["split"] == "test"], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
(common.DATA / "questions.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
report = {"total": len(Q), "counts": {f"{s}/{g}": n for (s, g), n in sorted(counts.items())}, "problems": problems,
          "test_sha256": test_hash, "note": "gold verified as exact substring of the named chunk on the stated page"}
(common.DATA / "benchmark_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1))
