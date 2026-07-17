"""JS 脚本执行的 node 运行时模板（前置 / 后置）。

在原生 variables/console/response 之外，额外注入 Postman/Apifox 风格的 pm.* 兼容层，
覆盖脚本里最常用的子集：pm.variables/environment/globals（读写变量，与平台单一变量袋共享）、
pm.response.json/text/code/headers、pm.test、pm.expect（精简 chai）、pm.response.to.have.status。
未覆盖的 pm.* 属性访问会自然抛错——这是与真实 Postman 的差异，非平台 bug。

抽成独立模块：避免 script_runner.py 膨胀，JS 与编排职责分离。
"""

# pm 兼容层：被前置/后置运行时共用。依赖外层已定义的 variables / logs（及后置的 response）。
_PM_PRELUDE = r"""
function _pmMakeExpect(actual) {
  function build(negate) {
    const assert = (ok, msg) => { if (negate ? ok : !ok) throw new Error(msg); };
    const self = {};
    ['to', 'be', 'been', 'is', 'that', 'which', 'has', 'have', 'with', 'at', 'of', 'same', 'and']
      .forEach((w) => Object.defineProperty(self, w, { get: () => self }));
    Object.defineProperty(self, 'not', { get: () => build(!negate) });
    self.equal = (v) => assert(actual === v, `期望 ${JSON.stringify(actual)} 等于 ${JSON.stringify(v)}`);
    self.eql = (v) => assert(JSON.stringify(actual) === JSON.stringify(v), `期望 ${JSON.stringify(actual)} 深度等于 ${JSON.stringify(v)}`);
    self.above = (v) => assert(actual > v, `期望 ${actual} 大于 ${v}`);
    self.below = (v) => assert(actual < v, `期望 ${actual} 小于 ${v}`);
    self.least = (v) => assert(actual >= v, `期望 ${actual} 不小于 ${v}`);
    self.most = (v) => assert(actual <= v, `期望 ${actual} 不大于 ${v}`);
    self.include = (v) => assert(
      actual != null && (typeof actual === 'string' ? actual.includes(v) : Array.isArray(actual) ? actual.includes(v) : false),
      `期望 ${JSON.stringify(actual)} 包含 ${JSON.stringify(v)}`,
    );
    self.property = (p) => assert(actual != null && Object.prototype.hasOwnProperty.call(actual, p), `期望对象含属性 ${p}`);
    self.lengthOf = (n) => assert(actual != null && actual.length === n, `期望长度 ${actual == null ? 'null' : actual.length} 等于 ${n}`);
    self.a = self.an = (t) => (t === undefined ? self : assert(typeof actual === t, `期望类型 ${typeof actual} 为 ${t}`));
    Object.defineProperty(self, 'ok', { get: () => (assert(!!actual, `期望 ${JSON.stringify(actual)} 为真值`), self) });
    Object.defineProperty(self, 'true', { get: () => (assert(actual === true, `期望 ${actual} 为 true`), self) });
    Object.defineProperty(self, 'false', { get: () => (assert(actual === false, `期望 ${actual} 为 false`), self) });
    Object.defineProperty(self, 'null', { get: () => (assert(actual === null, `期望 ${actual} 为 null`), self) });
    Object.defineProperty(self, 'undefined', { get: () => (assert(actual === undefined, '期望为 undefined'), self) });
    Object.defineProperty(self, 'empty', {
      get: () => (assert(
        actual == null || actual.length === 0 || (typeof actual === 'object' && Object.keys(actual).length === 0),
        '期望为空',
      ), self),
    });
    return self;
  }
  return build(false);
}

function _pmResponseTo(resp) {
  const to = {};
  ['to', 'be', 'been', 'is', 'that', 'which', 'has', 'have', 'with']
    .forEach((w) => Object.defineProperty(to, w, { get: () => to }));
  to.status = (code) => { if (resp.code !== code) throw new Error(`期望响应状态码 ${resp.code} 等于 ${code}`); };
  Object.defineProperty(to, 'ok', {
    get: () => {
      if (!(resp.code >= 200 && resp.code < 300)) throw new Error(`期望响应成功(2xx)，实际 ${resp.code}`);
      return to;
    },
  });
  return to;
}

function _pmBuild(variables, response, logs) {
  const bag = (b) => ({
    get: (k) => b[k],
    set: (k, v) => { b[k] = v == null ? '' : String(v); },
    has: (k) => Object.prototype.hasOwnProperty.call(b, k),
    unset: (k) => { delete b[k]; },
    toObject: () => Object.assign({}, b),
    clear: () => { Object.keys(b).forEach((k) => delete b[k]); },
  });
  const vars = bag(variables);
  const pm = {
    variables: vars,
    environment: vars,
    globals: vars,
    collectionVariables: vars,
    expect: _pmMakeExpect,
    test: (name, fn) => {
      try { fn(); logs.push('✓ ' + name); }
      catch (e) { logs.push('✗ ' + name + ' | ' + (e && e.message ? e.message : String(e))); }
    },
  };
  if (response) {
    const rawHeaders = response.headers || {};
    const lower = {};
    Object.keys(rawHeaders).forEach((k) => { lower[k.toLowerCase()] = rawHeaders[k]; });
    const resp = {
      code: response.status,
      responseTime: 0,
      text: () => response.body || '',
      json: () => JSON.parse(response.body || 'null'),
      headers: { get: (name) => lower[String(name).toLowerCase()] },
    };
    resp.to = _pmResponseTo(resp);
    pm.response = resp;
  }
  return pm;
}
"""

_PRE_HEAD = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const variables = input.variables;
const logs = [];
const console = { log: (...args) => logs.push(args.map((item) => String(item)).join(' ')) };
"""

_PRE_TAIL = r"""
const pm = _pmBuild(variables, null, logs);
try {
  const runner = new Function('variables', 'console', 'pm', input.script);
  runner(variables, console, pm);
  process.stdout.write(JSON.stringify({ ok: true, variables, logs }));
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(err), variables, logs }));
}
"""

_POST_HEAD = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
const variables = input.variables;
const response = input.response || { body: '', status: 0, headers: {} };
const logs = [];
const console = { log: (...args) => logs.push(args.map((item) => String(item)).join(' ')) };
"""

_POST_TAIL = r"""
const pm = _pmBuild(variables, response, logs);
try {
  const runner = new Function('variables', 'console', 'response', 'pm', input.script);
  runner(variables, console, response, pm);
  process.stdout.write(JSON.stringify({ ok: true, variables, logs }));
} catch (err) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(err), variables, logs }));
}
"""

PRE_RUNNER = _PRE_HEAD + _PM_PRELUDE + _PRE_TAIL
POST_RUNNER = _POST_HEAD + _PM_PRELUDE + _POST_TAIL
