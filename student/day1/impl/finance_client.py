# -*- coding: utf-8 -*-
"""
yfinance 가격 조회
- 목표: 티커 리스트에 대해 현재가/통화를 가져와 표준 형태로 반환
"""
from yfinance import Ticker
from typing import List, Dict, Any
import re

# (강의 안내) yfinance는 외부 네트워크 환경에서 동작. 인터넷 불가 환경에선 모킹이 필요할 수 있음.


def _normalize_symbol(s: str) -> str:
    """
    6자리 숫자면 한국거래소(.KS) 보정.
    예:
      '005930' → '005930.KS'
      'AAPL'   → 'AAPL' (그대로)
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-F-01] 구현 지침
    #  - if re.fullmatch(r"\d{6}", s): return f"{s}.KS"
    #  - else: return s
    # ----------------------------------------------------------------------------
    if re.fullmatch(r"\d{6}", s):
        return f"{s}.KS"
    else:
        return s


def get_quotes(symbols: List[str], timeout: int = 20) -> List[Dict[str, Any]]:
    """
    yfinance로 심볼별 시세를 조회해 리스트로 반환합니다.
    반환 예:
      [{"symbol":"AAPL","price":123.45,"currency":"USD"},
       {"symbol":"005930.KS","price":...,"currency":"KRW"}]
    실패시 해당 심볼은 {"symbol":sym, "error":"..."} 형태로 표기.
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-F-02] 구현 지침
    #  1) from yfinance import Ticker 임포트(파일 상단 대신 함수 내부 임포트도 OK)
    #  2) 결과 리스트 out=[]
    #  3) 입력 심볼들을 _normalize_symbol로 보정
    #  4) 각 심볼에 대해:
    #       - t = Ticker(sym)
    #       - 가격: getattr(t.fast_info, "last_price", None) 또는 t.fast_info.get("last_price")
    #       - 통화: getattr(t.fast_info, "currency", None)
    #       - 둘 다 숫자/문자 정상 추출 시 out.append({...})
    #       - 예외/누락 시 out.append({"symbol": sym, "error": "설명"})
    #  5) return out
    # ----------------------------------------------------------------------------
    out = []
    for symbol in symbols:
        symbol = _normalize_symbol(symbol)
        try:
            t = Ticker(symbol)
            price = t.fast_info.get("last_price")
            currency = t.fast_info.get("currency")
            out.append({"symbol": symbol, "price": price, "currency": currency})
        except Exception as e:
            out.append({"symbol": symbol, "error": str(e)})
    return out
