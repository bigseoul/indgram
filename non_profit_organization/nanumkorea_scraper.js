/**
 * 1365 기부포털 공익법인 리스트 스크래퍼
 * API 엔드포인트: https://www.nanumkorea.go.kr/nts/cptList.do
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

/**
 * 공익법인 리스트를 가져옵니다
 * @param {Object} options - 검색 옵션
 * @param {string} options.pbcbizTy - 공익사업유형 (전체: '', 교육: '교육', 학술•장학: '학술•장학', 사회복지: '사회복지', 의료: '의료', 예술•문화: '예술•문화', 기타: '기타')
 * @param {string} options.ctbmGrpTy - 기부금단체유형 (전체: '', 법정기부금단체: '법정기부금단체', 지정기부금단체: '지정기부금단체', 기타기부금단체: '기타기부금단체')
 * @param {string} options.cprNm - 공익법인명 (검색어)
 * @param {number} options.pageIndex - 페이지 번호 (기본값: 1)
 * @returns {Promise<Object>} 공익법인 리스트와 총 개수
 */
async function getPublicBenefitCorps(options = {}) {
  const {
    pbcbizTy = '',
    ctbmGrpTy = '',
    cprNm = '',
    pageIndex = 1
  } = options;

  const params = new URLSearchParams({
    pbcbizTy,
    ctbmGrpTy,
    cprNm,
    pageIndex: pageIndex.toString(),
    _: Date.now().toString() // 캐시 방지용 타임스탬프
  });

  const url = `https://www.nanumkorea.go.kr/nts/cptList.do?${params.toString()}`;

  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    };

    https.get(url, options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const result = parseHTMLResponse(data);
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });
    }).on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * HTML 응답을 파싱하여 구조화된 데이터로 변환
 * @param {string} html - HTML 응답 문자열
 * @returns {Object} 파싱된 데이터
 */
function parseHTMLResponse(html) {
  const dom = new JSDOM(html);
  const document = dom.window.document;

  // 총 개수 추출
  const totalsDiv = document.querySelector('.totals');
  const totalMatch = totalsDiv?.textContent.match(/(\d{1,3}(?:,\d{3})*)/);
  const total = totalMatch ? parseInt(totalMatch[1].replace(/,/g, '')) : 0;

  // 테이블 행 추출
  const rows = document.querySelectorAll('table.tbl_list_tax tbody tr');
  const corps = [];

    rows.forEach((row, index) => {
      const cells = row.querySelectorAll('td');
      if (cells.length < 4) return;

      const hiddenInputs = row.querySelectorAll('input[type="hidden"]');
      const data = {};

      hiddenInputs.forEach((input) => {
        const className = input.className;
        const value = input.value;
        if (className === 'bsnmNo') data.bsnmNo = value;
        if (className === 'cratQu') data.cratQu = value;
        if (className === 'pbnfSn') data.pbnfSn = value;
        if (className === 'pbnfDe') data.pbnfDe = value;
        if (className === 'frstPbnf') data.frstPbnf = value;
        if (className === 'bsnsYearEnd') data.bsnsYearEnd = value;
      });

      // 공시정보 컬럼에서 추가 데이터 추출
      const btnCell = cells[4];
      if (btnCell) {
        const summaryBtn = btnCell.querySelector('.sumryPop');
        
        if (summaryBtn) {
          data.summaryIdx = summaryBtn.getAttribute('data-idx') || '';
        }
        // hometaxBsnmNo는 bsnmNo와 중복이므로 제거
      }

      corps.push({
        번호: cells[0]?.textContent.trim() || '',
        공익법인명: cells[1]?.textContent.trim() || '',
        공익사업유형: cells[2]?.textContent.trim() || '',
        기부금단체유형: cells[3]?.textContent.trim() || '',
        ...data
      });
    });

  return {
    total,
    pageIndex: parseInt(new URLSearchParams(html.match(/pageIndex=(\d+)/)?.[0] || 'pageIndex=1').get('pageIndex') || '1'),
    corps
  };
}

/**
 * 모든 페이지의 공익법인 리스트를 가져옵니다
 * @param {Object} searchOptions - 검색 옵션
 * @param {number} maxPages - 최대 페이지 수 (기본값: null, 전체)
 * @returns {Promise<Array>} 모든 공익법인 리스트
 */
async function getAllPublicBenefitCorps(searchOptions = {}, maxPages = null) {
  const allCorps = [];
  let pageIndex = 1;
  let hasMore = true;

  let totalPages = null;
  
  while (hasMore) {
    const result = await getPublicBenefitCorps({
      ...searchOptions,
      pageIndex
    });

    // 첫 페이지에서 전체 페이지 수 계산
    if (totalPages === null) {
      const itemsPerPage = result.corps.length;
      totalPages = Math.ceil(result.total / itemsPerPage);
      console.log(`총 ${result.total}건, 페이지당 ${itemsPerPage}건, 총 ${totalPages}페이지`);
    }

    allCorps.push(...result.corps);
    
    // 진행 상황 출력
    const progress = ((pageIndex / totalPages) * 100).toFixed(1);
    console.log(`[${pageIndex}/${totalPages}] 페이지 처리 중... (${allCorps.length}/${result.total}건, ${progress}%)`);

    // 다음 페이지가 있는지 확인
    if (pageIndex >= totalPages || (maxPages && pageIndex >= maxPages)) {
      hasMore = false;
    } else {
      pageIndex++;
      // API 부하 방지를 위한 딜레이 (500ms)
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  return {
    total: allCorps.length,
    corps: allCorps
  };
}

/**
 * 데이터를 JSON 파일로 저장
 * @param {Object} data - 저장할 데이터
 * @param {string} filename - 파일명 (기본값: nanumkorea_corps.json)
 */
function saveToJSON(data, filename = 'nanumkorea_corps.json') {
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const filepath = path.join(outputDir, filename);
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`✓ JSON 파일 저장 완료: ${filepath}`);
  return filepath;
}

/**
 * 데이터를 CSV 파일로 저장
 * @param {Array} corps - 공익법인 리스트
 * @param {string} filename - 파일명 (기본값: nanumkorea_corps.csv)
 */
function saveToCSV(corps, filename = 'nanumkorea_corps.csv') {
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const filepath = path.join(outputDir, filename);
  
  if (corps.length === 0) {
    console.log('저장할 데이터가 없습니다.');
    return null;
  }

  // CSV 헤더 생성
  const headers = Object.keys(corps[0]);
  const csvRows = [headers.join(',')];

  // CSV 데이터 행 생성
  corps.forEach(corp => {
    const values = headers.map(header => {
      const value = corp[header] || '';
      // CSV 형식에 맞게 따옴표와 쉼표 처리
      return `"${String(value).replace(/"/g, '""')}"`;
    });
    csvRows.push(values.join(','));
  });

  fs.writeFileSync(filepath, csvRows.join('\n'), 'utf-8');
  console.log(`✓ CSV 파일 저장 완료: ${filepath}`);
  return filepath;
}

// 사용 예시
if (require.main === module) {
  (async () => {
    try {
      // 전체 공익법인 리스트 가져오기
      console.log('=== 전체 공익법인 리스트 수집 시작 ===');
      console.log('주의: 전체 14,754건을 수집하므로 시간이 오래 걸릴 수 있습니다.');
      console.log('진행 상황은 콘솔에서 확인할 수 있습니다.\n');
      
      const startTime = Date.now();
      const allResult = await getAllPublicBenefitCorps({});
      const endTime = Date.now();
      const duration = ((endTime - startTime) / 1000 / 60).toFixed(2);
      
      console.log(`\n=== 수집 완료 ===`);
      console.log(`총 ${allResult.total}건 수집 완료`);
      console.log(`소요 시간: ${duration}분`);

      // 파일로 저장
      console.log('\n=== 파일 저장 중 ===');
      saveToJSON(allResult, 'nanumkorea_all.json');
      saveToCSV(allResult.corps, 'nanumkorea_all.csv');
      
      console.log('\n✓ 모든 작업 완료!');

    } catch (error) {
      console.error('에러 발생:', error);
      process.exit(1);
    }
  })();
}

module.exports = {
  getPublicBenefitCorps,
  getAllPublicBenefitCorps,
  parseHTMLResponse,
  saveToJSON,
  saveToCSV
};

