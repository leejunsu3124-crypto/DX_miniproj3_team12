# -*- coding: utf-8 -*-
"""
Day1 본체
- 역할: 웹 검색 / 주가 / 기업개요(추출+요약)를 병렬로 수행하고 결과를 정규 스키마로 병합
"""

from __future__ import annotations
from dataclasses import asdict
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.models.lite_llm import LiteLlm
from student.common.schemas import Day1Plan
from student.day1.impl.merge import merge_day1_payload
# 외부 I/O
from student.day1.impl.tavily_client import search_tavily, extract_url
from student.day1.impl.finance_client import get_quotes
from student.day1.impl.web_search import (
    looks_like_ticker,
    search_company_profile,
    extract_and_summarize_profile,
)

DEFAULT_WEB_TOPK = 6
MAX_WORKERS = 4
DEFAULT_TIMEOUT = 20

_SUM: Optional[LiteLlm] = LiteLlm(model="openai/gpt-4o-mini")

# ------------------------------------------------------------------------------
# TODO[DAY1-I-01] 요약용 경량 LLM 준비
#  - 목적: 기업 개요 본문을 Extract 후 간결 요약
#  - LiteLlm(model="openai/gpt-4o-mini") 형태로 _SUM에 할당
# ------------------------------------------------------------------------------
_SUM: Optional[LiteLlm] = None


def _summarize(text: str) -> str:
        # 요약할 내용이 없으면 바로 종료
    if not text:
        return ""

    # 요약용 LLM이 준비 안 됐으면 요약 생략
    if _SUM is None:
        return ""

    try:
        # LiteLlm이 invoke(dict) 형태를 받는다고 주석에 적혀 있었으니까 그 방식으로 호출
        resp = _SUM.invoke({"input": text})

        # 응답이 그냥 문자열로 오면 그대로 반환
        if isinstance(resp, str):
            return resp

        # 응답 객체에 text 속성이 있으면 그걸 반환
        summary = getattr(resp, "text", "")
        if summary:
            return summary

        # 그 외엔 응답 전체를 문자열로 바꿔서라도 돌려보냄
        return str(resp)

    except Exception:
        # 어떤 문제가 나도 상위 파이프라인이 멈추지 않게 빈 문자열
        return ""


""" 
입력 텍스트를 LLM으로 3~5문장 수준으로 요약합니다.
실패 시 빈 문자열("")을 반환해 상위 로직이 안전하게 진행되도록 합니다.
"""

    # ----------------------------------------------------------------------------
    # TODO[DAY1-I-02] 구현 지침
    #  - _SUM이 None이면 "" 반환(요약 생략)
    #  - _SUM.invoke({...}) 혹은 단순 텍스트 인자 형태로 호출 가능한 래퍼라면
    #    응답 객체에서 본문 텍스트를 추출하여 반환
    #  - 예외 발생 시 빈 문자열 반환
    # ----------------------------------------------------------------------------


class Day1Agent:
    def __init__(self, tavily_api_key: Optional[str], web_topk: int = DEFAULT_WEB_TOPK, request_timeout: int = DEFAULT_TIMEOUT):
        self.tavily_api_key = tavily_api_key
        self.web_topk = web_topk
        self.request_timeout = request_timeout

        """
        필드 저장만 담당합니다.
        - tavily_api_key: Tavily API 키(없으면 웹 호출 실패 가능)
        - web_topk: 기본 검색 결과 수
        - request_timeout: 각 HTTP 호출 타임아웃(초)
        """
        # ----------------------------------------------------------------------------
        # TODO[DAY1-I-03] 필드 저장
        #  self.tavily_api_key = tavily_api_key
        #  self.web_topk = web_topk
        #  self.request_timeout = request_timeout
        # ----------------------------------------------------------------------------

    def handle(self, query: str, plan: Day1Plan) -> Dict[str, Any]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from dataclasses import asdict

        # 1) 결과 스켈레톤 초기화
        results = {
            "type": "web_results",
            "query": query,
            "analysis": asdict(plan),
            "items": [],
            "tickers": [],
            "errors": [],
            "company_profile": "",
            "profile_sources": [],
        }

        futures = {}

        # 2) 병렬 작업 제출
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # (1) 웹 검색
            if plan.do_web:
                futures[executor.submit(
                    search_tavily,
                    query,
                    self.tavily_api_key,
                    self.web_topk,
                    self.request_timeout
                )] = "web"

            # (2) 주가 조회
            if plan.do_stocks:
                futures[executor.submit(
                    get_quotes,
                    plan.tickers,
                    self.request_timeout
                )] = "stock"

            # (3) 기업 개요
            if plan.tickers or looks_like_ticker(query):
                futures[executor.submit(
                    self._handle_profile,  # 별도 헬퍼 함수
                    query
                )] = "profile"

            # 3) 완료된 결과 수집
            for future in as_completed(futures):
                kind = futures[future]
                try:
                    data = future.result()

                    if kind == "web":
                        results["items"] = data or []
                    elif kind == "stock":
                        results["tickers"] = data or []
                    elif kind == "profile":
                        if isinstance(data, tuple):
                            text, urls = data
                            results["company_profile"] = text
                            results["profile_sources"] = urls
                        else:
                            results["company_profile"] = data
                except Exception as e:
                    results["errors"].append(f"{kind}: {type(e).__name__}: {e}")

        # 4) 결과 병합
        return merge_day1_payload(results)