# 1365 기부포털 공익법인 리스트 스크래퍼

1365 기부포털(https://www.nanumkorea.go.kr)에서 공익법인 리스트를 가져오는 JavaScript 스크립트입니다.

## 발견된 API 엔드포인트

```
GET https://www.nanumkorea.go.kr/nts/cptList.do
```

### 파라미터

- `pbcbizTy`: 공익사업유형
  - `''` (전체)
  - `'교육'`
  - `'학술•장학'`
  - `'사회복지'`
  - `'의료'`
  - `'예술•문화'`
  - `'기타'`

- `ctbmGrpTy`: 기부금단체유형
  - `''` (전체)
  - `'법정기부금단체'`
  - `'지정기부금단체'`
  - `'기타기부금단체'`

- `cprNm`: 공익법인명 (검색어)

- `pageIndex`: 페이지 번호 (기본값: 1)

- `_`: 타임스탬프 (캐시 방지용)

### 응답 형식

API는 HTML 형식으로 응답을 반환합니다. 스크립트는 이를 파싱하여 구조화된 데이터로 변환합니다.

## 설치

```bash
npm install
```

## 사용 방법

### 기본 사용

```javascript
const { getPublicBenefitCorps } = require('./nanumkorea_scraper');

// 첫 페이지 가져오기
const result = await getPublicBenefitCorps({
  pbcbizTy: '',
  ctbmGrpTy: '',
  cprNm: '',
  pageIndex: 1
});

console.log(`총 ${result.total}건`);
console.log(result.corps);
```

### 검색 옵션 사용

```javascript
// 교육 관련 공익법인 검색
const result = await getPublicBenefitCorps({
  pbcbizTy: '교육',
  pageIndex: 1
});

// 특정 이름으로 검색
const result = await getPublicBenefitCorps({
  cprNm: '삼성',
  pageIndex: 1
});
```

### 모든 페이지 가져오기

```javascript
const { getAllPublicBenefitCorps } = require('./nanumkorea_scraper');

// 처음 10페이지만 가져오기
const result = await getAllPublicBenefitCorps({}, 10);

// 전체 가져오기 (주의: 시간이 오래 걸릴 수 있음)
const allResult = await getAllPublicBenefitCorps({});
```

## 실행

```bash
node nanumkorea_scraper.js
```

또는

```bash
npm start
```

## 응답 데이터 구조

```javascript
{
  total: 14754,  // 전체 개수
  pageIndex: 1,  // 현재 페이지
  corps: [
    {
      번호: "14754",
      공익법인명: "사단법인 한국예술심리상담협회",
      공익사업유형: "교육",
      기부금단체유형: "지정기부금단체",
      bsnmNo: "A462270810B62C47755E12E10FC1EAE2",  // 사업자번호
      cratQu: "2024",  // 생성 분기
      pbnfSn: "3469",  // 공익법인 순번
      pbnfDe: "",  // 공익법인 등록일
      frstPbnf: "",  // 최초 공익법인 등록일
      bsnsYearEnd: ""  // 사업연도 종료일
    },
    // ...
  ]
}
```

## 주의사항

1. **API 부하 방지**: 여러 페이지를 가져올 때는 적절한 딜레이를 두세요 (기본 500ms)
2. **이용약관 준수**: 사이트의 이용약관을 확인하고 준수하세요
3. **데이터 업데이트**: 이 데이터는 연 2회 업데이트되므로 최신성에 주의하세요
4. **Rate Limiting**: 과도한 요청은 IP 차단을 받을 수 있습니다

## 브라우저에서 직접 사용하기

브라우저 콘솔에서도 사용할 수 있습니다:

```javascript
// 브라우저 콘솔에서 실행
async function fetchPublicBenefitCorps(pageIndex = 1) {
  const url = `https://www.nanumkorea.go.kr/nts/cptList.do?pbcbizTy=&ctbmGrpTy=&cprNm=&pageIndex=${pageIndex}&_=${Date.now()}`;
  
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'X-Requested-With': 'XMLHttpRequest'
    }
  });
  
  const html = await response.text();
  
  // HTML 파싱 로직 (DOM 조작)
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  
  const rows = doc.querySelectorAll('table.tbl_list_tax tbody tr');
  const corps = [];
  
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    corps.push({
      번호: cells[0]?.textContent.trim(),
      공익법인명: cells[1]?.textContent.trim(),
      공익사업유형: cells[2]?.textContent.trim(),
      기부금단체유형: cells[3]?.textContent.trim()
    });
  });
  
  return corps;
}

// 사용
fetchPublicBenefitCorps(1).then(corps => console.log(corps));
```

