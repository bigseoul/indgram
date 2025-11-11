/**
 * 수집 진행 상황 확인 스크립트
 */

const fs = require('fs');
const path = require('path');

const outputFile = path.join(__dirname, 'output', 'nanumkorea_all.json');

if (fs.existsSync(outputFile)) {
  const data = JSON.parse(fs.readFileSync(outputFile, 'utf-8'));
  console.log(`✓ 수집 완료!`);
  console.log(`총 ${data.total}건`);
  console.log(`공익법인 수: ${data.corps.length}건`);
  console.log(`파일 크기: ${(fs.statSync(outputFile).size / 1024 / 1024).toFixed(2)} MB`);
} else {
  console.log('아직 수집이 완료되지 않았습니다.');
  console.log('프로세스가 실행 중인지 확인하세요: ps aux | grep nanumkorea_scraper');
}

