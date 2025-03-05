
from requests_ratelimiter import LimiterSession
import requests_cache

class SecApiSession:
    def __init__(self):
        self.headers = {
            'User-Agent': 'amrith321@gmail.com',
            'Authorization': '31180cc66b3b06a12376a2101b61a4018674a2e06a33f9f253259f27e90ac822' # Free trial api key
        }
        self.session = requests_cache.CachedSession('legendary_umbrella', expire_after=3600)
        self.limited_session = LimiterSession(session=self.session, per_second=8)

    def get_recent_filing(self, cik: str) -> list | None:
        assert len(cik) == 10

        print("Getting recent filing for CIK:", cik)

        url = f"https://api.sec-api.io/form-nport"
        data = {
            "query": f"genInfo.regCik:{cik}",
            "from": "0",
            "size": "1",
            "sort": [{ "filedAt": { "order": "desc" } }]
        }
        response = self.limited_session.post(url, headers=self.headers, json=data)
        if response.status_code != 200:
            return None
        filings = response.json().get("filings", [])
        if not filings or len(filings) < 1:
            return None
        recent_filing = filings[0]
        file_date = recent_filing.get("filedAt")
        result = []
        for holding in recent_filing.get("invstOrSecs", []):
            result.append({
                "cik": cik,
                "date": file_date,
                "company": holding.get("name"),
                "cusip": holding.get("cusip"),
                "balance": holding.get("balance"),
                "value": holding.get("valUSD")
            })

        

        return result

if __name__ == "__main__":
    sec_api = SecApiSession()
    print(sec_api.get_recent_filing("0000884394")) 