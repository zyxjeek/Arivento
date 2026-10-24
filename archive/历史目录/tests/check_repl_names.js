const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'reference/yail.js'), 'utf8');
const ctx = { AI: { Yail: { YAIL_RENAME_COMPONENT: '(rename-component ', YAIL_SPACER: ' ', YAIL_CLOSE_BLOCK: ')' } } };
vm.createContext(ctx);
for (const name of ['quotifyForREPL', 'getComponentRenameString']) {
  const start = source.indexOf('AI.Yail.' + name + ' = function');
  assert(start >= 0);
  const end = source.indexOf('\n};', start) + 3;
  vm.runInContext(source.slice(start, end), ctx);
}
const previous = ctx.AI.Yail.getComponentRenameString('Screen1', '制谱设置');
assert(previous.includes('\\u5236\\u8c31\\u8bbe\\u7f6e'));
const folder = path.join(root, 'native/Rail4K_CompanionFix/src/appinventor/ai_me/Rail4K_0905');
const result = [];
for (const file of fs.readdirSync(folder).filter(n => n.endsWith('.scm'))) {
  const data = fs.readFileSync(path.join(folder, file), 'utf8');
  const name = JSON.parse(data.split('$JSON')[1].split('|#')[0]).Properties.$Name;
  const generated = ctx.AI.Yail.getComponentRenameString('Screen1', name);
  assert(/^[A-Za-z][A-Za-z0-9_]*$/.test(name));
  assert(!generated.includes('\\u'));
  result.push({name, generated});
}
fs.writeFileSync(path.join(root, 'docs/伴侣屏幕名称检查.json'), JSON.stringify({previous, current: result, note: '执行官方 YAIL 名称生成函数，未连接真实 AI 伴侣'}, null, 2));
console.log('PASS: official YAIL screen rename generation, four ASCII screen identities');
