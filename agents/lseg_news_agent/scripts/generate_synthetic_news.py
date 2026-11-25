"""Generate the synthetic Asterion Technologies news feed."""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "news.json"

ARTICLES = [
("ASTR-001","Asterion Technologies","ASTR","2026-11-25T09:15:00Z","Asterion reports record cloud revenue","Northstar Markets","https://example.test/astr-001","Asterion Technologies said cloud revenue reached a record in its latest quarter."),
("ASTR-002","Asterion Technologies","ASTR","2026-11-25T12:30:00Z","Asterion unveils next-generation AI accelerator","Tech Ledger","https://example.test/astr-002","Asterion announced the Orion accelerator, with general availability planned for 2027."),
("ASTR-003","Asterion Technologies","ASTR","2026-11-24T08:40:00Z","Asterion narrows guidance range","Capital Wire","https://example.test/astr-003","The company said fourth-quarter revenue guidance is now narrowed to a range of $420 million to $435 million."),
("ASTR-004","Asterion Technologies","ASTR","2026-11-24T15:10:00Z","Asterion reports record cloud revenue","Global Desk","https://example.test/astr-004","Asterion reported record cloud revenue and operating margin expansion in its quarterly update."),
("ASTR-005","Asterion Technologies","ASTR","2026-11-24T15:12:00Z","Asterion reports record cloud revenue","Northstar Markets","https://example.test/astr-001","Asterion Technologies said cloud revenue reached a record in its latest quarter."),
("ASTR-006","Asterion Technologies","ASTR","2026-11-23T07:55:00Z","Asterion signs strategic chip-supply partnership","Industry Times","https://example.test/astr-006","Asterion signed a two-year supply agreement with Helix Foundry for advanced chips."),
("ASTR-007","Asterion Technologies","ASTR","2026-11-23T09:05:00Z","Asterion and Helix Foundry enter chip supply deal","Semiconductor Daily","https://example.test/astr-007","Helix Foundry will supply advanced chips to Asterion under a two-year agreement."),
("ASTR-008","Asterion Technologies","ASTR","2026-11-22T10:20:00Z","Patent dispute poses manageable risk, analyst says","Market Brief","https://example.test/astr-008","A research note described Asterion's patent dispute as manageable and said a preliminary injunction remains possible."),
("ASTR-009","Asterion Technologies","ASTR","2026-11-22T14:45:00Z","Court setback threatens Asterion patent position","Legal Review","https://example.test/astr-009","A court allowed a competitor's motion to proceed in a patent dispute involving Asterion."),
("ASTR-010","Asterion Technologies","ASTR","2026-11-21T11:30:00Z","Asterion appoints Maria Chen chief operating officer","Executive Watch","https://example.test/astr-010","Asterion appointed Maria Chen as chief operating officer, effective December 1."),
("ASTR-011","Asterion Technologies","ASTR","2026-11-20T09:00:00Z","European regulator opens Asterion data review","Europe Regulation","https://example.test/astr-011","A European data regulator opened a review of Asterion's handling of customer information."),
("ASTR-012","Asterion Technologies","ASTR","2026-11-20T16:15:00Z","Competitor Nova Systems launches rival AI platform","Sector News","https://example.test/astr-012","Nova Systems launched a rival AI platform that may compete with Asterion's Orion offering."),
("ASTR-013","Asterion Technologies","ASTR","2026-11-19T08:20:00Z","Asterion announces plan to acquire Meridian Robotics","Deal Street",None,"Asterion said it plans to acquire private robotics firm Meridian Robotics for cash and stock."),
("ASTR-014","Asterion Technologies","ASTR","2026-11-19T13:50:00Z","Asterion acquisition of Meridian Robotics faces shareholder review","Deal Street","https://example.test/astr-014","Asterion said the proposed Meridian Robotics acquisition requires shareholder approval."),
("ASTR-015","Asterion Technologies","ASTR","2026-11-18T10:10:00Z","Asterion and Helix expand test manufacturing agreement","Industry Times","https://example.test/astr-015","Asterion and Helix Foundry expanded testing and manufacturing plans for the same chip programme."),
("ASTR-016","Asterion Technologies","ASTR","2026-11-18T17:40:00Z","Cloud spending survey lifts software sector outlook","Industry Watch","https://example.test/astr-016","An industry survey found software buyers plan to increase cloud spending over the next year."),
("ASTR-017","Asterion Technologies","ASTR","2026-11-17T10:00:00Z","Asterion opens new design centre","Regional Business","https://example.test/astr-017","Asterion opened a design centre in Manchester before the research period."),
("ASTR-018","Asterion Technologies","ASTR","2026-11-26T08:00:00Z","Asterion CEO speaks at London conference","Media Journal","https://example.test/astr-018","Asterion's chief executive spoke at a London conference after the research period."),
("ASTR-019","Nova Systems","NOVS","2026-11-24T10:30:00Z","Nova Systems launches rival AI platform","Sector News","https://example.test/novs-019","Nova Systems launched its new AI platform and did not mention Asterion in the announcement."),
("ASTR-020","Asterion Technologies","WRONG","2026-11-23T12:00:00Z","Wrong-ticker Asterion filing","Ticker Bureau","https://example.test/wrong-020","A filing header contains the wrong ticker symbol but names Asterion Technologies."),
("ASTR-021","Asterion Technologies","ASTR",None,"Asterion missing timestamp announcement","News Wire",None,"Asterion announced a board committee review but the feed omitted publication time."),
("ASTR-022","Asterion Technologies","ASTR","not-a-timestamp","Asterion malformed timestamp filing","Daily Filing","https://example.test/astr-022","Asterion filed an update with a timestamp that cannot be parsed."),
("ASTR-023","Asterion Technologies","ASTR","2026-11-25T07:10:00Z","Asterion reports record cloud revenue","Quick News","https://example.test/astr-023","Asterion posted quarterly cloud growth but did not disclose an absolute revenue figure."),
("ASTR-024","Asterion Technologies","ASTR","2026-11-25T18:00:00Z","Asterion cloud margin outlook improves","Capital Wire","https://example.test/astr-024","The company said margin performance improved in the cloud segment."),
("ASTR-025","Asterion Technologies","ASTR","2026-11-21T15:20:00Z","Asterion settles supplier dispute","Legal Review","https://example.test/astr-025","Asterion and a supplier agreed to a settlement, with no financial terms disclosed."),
("ASTR-026","Asterion Technologies","ASTR","2026-11-20T12:30:00Z","Asterion partners with university on chip research","Academic Wire",None,"Asterion and a university opened a chip-research programme with no funding amount disclosed."),
("ASTR-027","Asterion Technologies","ASTR","2026-11-19T09:10:00Z","Asterion board adds independent director","Governance Daily","https://example.test/astr-027","Asterion appointed an independent director to its board."),
("ASTR-028","Asterion Technologies","ASTR","2026-11-18T09:30:00Z","Asterion quarterly earnings date confirmed","Investor Desk","https://example.test/astr-028","Asterion confirmed the date of its next quarterly earnings release."),
("ASTR-029","Asterion Technologies","ASTR","2026-11-18T14:10:00Z","Industry demand for AI servers stays strong","Macro Ledger","https://example.test/astr-029","A market report said AI-server demand remained strong across the industry."),
("ASTR-030","Asterion Technologies","ASTR","2026-11-24T11:40:00Z","Asterion quarterly filing delayed by auditor","Audit News","https://example.test/astr-030","Asterion said its auditor needs additional time to complete the quarterly filing review."),
]

rows=[]
for article_id, company_name, ticker, published_at, headline, source, url, snippet in ARTICLES:
    rows.append({"article_id":article_id,"company_name":company_name,"ticker":ticker,"published_at":published_at,"headline":headline,"source":source,"url":url,"snippet":snippet})

DATA.parent.mkdir(parents=True, exist_ok=True)
DATA.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(f"Wrote {len(rows)} articles to {DATA}")

if __name__ == "__main__":
    pass
