from __future__ import annotations

import json

from zombie import wisereport_fetcher


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, params=None, headers=None, timeout=None):  # noqa: ANN001
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        if "c1040001.aspx" in url:
            return FakeResponse("<html><script>var x = { encparam: 'abc123==' };</script></html>")
        if "c1010001.aspx" in url:
            return FakeResponse("<html><table id='cTB11'></table></html>")
        return FakeResponse(json.dumps({"YYMM": ["2024/12<br />(IFRS별도)"], "DATA": []}))


def test_extract_encparam_finds_script_value() -> None:
    html = "<html><script>var params = { encparam: 'token-value==' };</script></html>"

    assert wisereport_fetcher.extract_encparam(html) == "token-value=="


def test_fetch_indicator_payload_uses_page_then_payload_request() -> None:
    session = FakeSession()

    result = wisereport_fetcher.fetch_indicator_payload(
        session=session,
        stock_code="032940",
        rpt=3,
        fin_gubun="IFRSS",
        frq_typ="0",
        timeout=5,
    )

    assert result.payload_json == '{"YYMM": ["2024/12<br />(IFRS\\ubcc4\\ub3c4)"], "DATA": []}'
    assert len(session.calls) == 2
    assert session.calls[0]["params"] == {"cmp_cd": "032940", "cn": ""}
    assert session.calls[1]["params"] == {
        "cmp_cd": "032940",
        "frq": "0",
        "rpt": 3,
        "finGubun": "IFRSS",
        "frqTyp": "0",
        "cn": "",
        "encparam": "abc123==",
    }


def test_fetch_overview_page_uses_company_overview_url() -> None:
    session = FakeSession()

    html = wisereport_fetcher.fetch_overview_page(session=session, stock_code="041590", timeout=5)

    assert html == "<html><table id='cTB11'></table></html>"
    assert session.calls[0]["url"].endswith("/company/c1010001.aspx")
    assert session.calls[0]["params"] == {"cmp_cd": "041590", "cn": ""}
