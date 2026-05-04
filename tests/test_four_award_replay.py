from __future__ import annotations

import pytest
from datetime import date

from modules.four_award.replay import ReplayFailure, run_replay_case


def test_replay_matches_expected_successful_review():
    four_before = """== Current nominations ==
=== Example article ===
{{Four Award Nomination
 | article = Example article
 | dyknom = Template:Did you know nominations/Example article
 | user = Example
}}
"""
    records_before = """== Four Awards ==
{| class="wikitable"
! User
! Article
! Award date
! Creation date
! DYK date
! GA date
! FA date
|}
"""
    talk_before = """{{Article history
|action1=DYK
|action1date=2020-01-07
|action1link=[[Template:Did you know nominations/Example article]]
|action2=GAN
|action2date=2020-02-01
|action2link=[[Talk:Example article/GA1]]
|action3=FAC
|action3date=2020-03-01
|action3result=promoted
|action3link=[[Wikipedia:Featured article candidates/Example article/archive1]]
|currentstatus=FA
}}
"""
    case = {
        "settings": {"allow_automated_approval": True},
        "pages": {
            "Wikipedia:Four Award": {
                "before_text": four_before,
                "expected_text": "== Current nominations ==\n\n",
            },
            "Wikipedia:Four Award/Records": {
                "before_text": records_before,
                "expected_text": records_before.replace(
                    "|}\n",
                    "|-\n"
                    f"| [[User:Example|Example]] || [[Example article]] || {{{{dts|{date.today().year}|{date.today().month:02d}|{date.today().day:02d}}}}} || "
                    "{{dts|2020|01|01}} || {{dts|2020|01|07}} || {{dts|2020|02|01}} || {{dts|2020|03|01}}\n"
                    "|}\n\n",
                ),
            },
            "Talk:Example article": {
                "before_text": talk_before,
                "expected_text": talk_before.replace("}}\n", "|four=yes\n}}\n"),
            },
            "User talk:Example": {
                "before_text": "",
                "expected_text": "\n\n== Four Award ==\n<!-- FourAwardBot:approved:Example_article -->\n{{subst:Four Award Message|Example article}}\n",
            },
            "Template:Did you know nominations/Example article": {
                "before_text": "[[User:Example|Example]]",
                "expected_text": "[[User:Example|Example]]",
            },
            "Talk:Example article/GA1": {
                "before_text": "[[User:Example|Example]]",
                "expected_text": "[[User:Example|Example]]",
            },
            "Wikipedia:Featured article candidates/Example article/archive1": {
                "before_text": "[[User:Example|Example]]",
                "expected_text": "[[User:Example|Example]]",
            },
        },
        "existing_pages": ["Example article"],
        "page_creation": {"Example article": {"user": "Example", "date": "2020-01-01"}},
        "revision_users": {
            "Example article": ["Example"],
            "Template:Did you know nominations/Example article": ["Example"],
            "Talk:Example article/GA1": ["Example"],
            "Wikipedia:Featured article candidates/Example article/archive1": ["Example"],
        },
        "expected_result": {"approved": 1, "failed": 0, "manual": 0},
    }

    payload = run_replay_case(case)

    assert [edit["title"] for edit in payload["edits"]] == [
        "Wikipedia:Four Award",
        "Talk:Example article",
        "User talk:Example",
        "Wikipedia:Four Award/Records",
    ]


def _successful_review_case() -> dict:
    four_text = """== Current nominations ==
=== Example article ===
{{Four Award Nomination
 | article = Example article
 | dyknom = Template:Did you know nominations/Example article
 | user = Example
}}
"""
    talk_text = """{{Article history
|action1=DYK
|action1date=2020-01-07
|action1link=[[Template:Did you know nominations/Example article]]
|action2=GAN
|action2date=2020-02-01
|action2link=[[Talk:Example article/GA1]]
|action3=FAC
|action3date=2020-03-01
|action3result=promoted
|action3link=[[Wikipedia:Featured article candidates/Example article/archive1]]
|currentstatus=FA
}}
"""
    return {
        "pages": {
            "Wikipedia:Four Award": {"before_text": four_text},
            "Wikipedia:Four Award/Records": {
                "before_text": "== Four Awards ==\n{| class=\"wikitable\"\n! User\n! Article\n|}\n"
            },
            "Talk:Example article": {"before_text": talk_text},
            "User talk:Example": {"before_text": ""},
            "Template:Did you know nominations/Example article": {
                "before_text": "[[User:Example|Example]]"
            },
            "Talk:Example article/GA1": {"before_text": "[[User:Example|Example]]"},
            "Wikipedia:Featured article candidates/Example article/archive1": {
                "before_text": "[[User:Example|Example]]"
            },
        },
        "existing_pages": ["Example article"],
        "page_creation": {"Example article": {"user": "Example", "date": "2020-01-01"}},
        "revision_users": {
            "Example article": ["Example"],
            "Template:Did you know nominations/Example article": ["Example"],
            "Talk:Example article/GA1": ["Example"],
            "Wikipedia:Featured article candidates/Example article/archive1": ["Example"],
        },
    }


def test_manual_review_report_explains_automated_approval_gate():
    case = _successful_review_case()
    case["settings"] = {"allow_automated_approval": False}
    case["expected_result"] = {"approved": 0, "failed": 0, "manual": 1}

    payload = run_replay_case(case)
    result = payload["result"]
    report = result["dry_run_report"]["wikitext"]

    assert result["reviews"][0]["issues"][-1]["code"] == "automated_approval_disabled"
    assert "=== Verification details ===" in report
    assert "Page creation / early edits" in report
    assert "DYK contribution" in report
    assert "GA contribution" in report
    assert "FA contribution" in report
    assert "Automated approval gate" in report
    assert "Automated approval is disabled by configuration" in report


def test_historical_payload_page_text_is_used_instead_of_live_four_award_page():
    case = _successful_review_case()
    historical_text = case["pages"]["Wikipedia:Four Award"]["before_text"]
    case["settings"] = {"allow_automated_approval": True}
    case["payload"] = {"four_page_text": historical_text}
    case["pages"]["Wikipedia:Four Award"]["before_text"] = "== Current nominations ==\n"
    case["expected_result"] = {"approved": 1, "failed": 0, "manual": 0}

    payload = run_replay_case(case)

    assert payload["result"]["reviews"][0]["article"] == "Example article"


def test_replay_failure_shows_diff():
    case = {
        "pages": {
            "Wikipedia:Four Award": {
                "before_text": "== Current nominations ==\n",
                "expected_text": "wrong\n",
            }
        },
        "expected_result": {"approved": 0, "failed": 0, "manual": 0},
    }

    with pytest.raises(ReplayFailure) as excinfo:
        run_replay_case(case)

    assert "expected/Wikipedia:Four Award" in str(excinfo.value)


def test_historic_great_mecca_feast_replay_fixture_loads():
    from modules.four_award.replay import load_case

    case = load_case("tests/fixtures/four_award_replay_1345035310_great_mecca_feast.json")

    assert case["pages"]["Wikipedia:Four Award"]["before_revid"] == 1345035310
    assert case["pages"]["Wikipedia:Four Award/Records"]["expected_revid"] == 1346457952
