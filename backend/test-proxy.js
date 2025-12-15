const https = require('https');

// 尝试访问外部API
const req = https.get('https://api.github.com', (res) => {
  console.log('状态码:', res.statusCode);
  res.on('data', (d) => {
    console.log('成功访问外部API');
  });
});

req.on('error', (e) => {
  console.error('错误:', e.message);
  console.log('这可能是代理问题');
});

req.end();