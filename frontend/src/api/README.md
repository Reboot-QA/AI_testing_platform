# API 层结构（US-04）

按域拆分，`@/api` 导入路径不变（`index.ts` 桶式再导出）。

```
request.ts        axios 实例 + 拦截器 + get<T>/post<T>/put<T>/patch<T>/del<T> 泛型封装 + streamSSE 公共封装 + Id 别名
types.ts          export type Schemas = components['schemas']（引用生成类型）
schema.d.ts       openapi-typescript 生成产物（勿手改；`pnpm gen:api-types` 重生成）
<domain>.ts       auth / project / requirement / testcase / settings / assistant /
                  department / user / apifox / testExecution / logs
index.ts          桶式再导出（保持 @/api 不变）
```

类型来源：后端 `backend/scripts/export_openapi.py` 离线导出 `backend/openapi.json` → `pnpm gen:api-types` 生成 `schema.d.ts`。**不手写类型**。

## 技术债：后端补 `response_model`

以下接口后端未声明 `response_model`，前端只能用 `any` 弱类型占位（非 `unknown`）。后端补齐后，前端把对应方法的 `any` 换成生成类型即可，无需改调用方。

- **DELETE 类**（返回 `{ok}`/`{message}`）：projects、requirements、requirements/testcases、testcases、departments、users、settings/llm/providers、test-executions，以及 apifox 下 folders / endpoints / environments / environment-servers / env-variables / global-variables / cases / schemas / scripts / global-params / scenarios / scenario-folders / suites / datasets / env-databases / schedules。
- **PUT 类**：`/auth/password`、`/users/{id}/password`、`/projects/preferences/order`。
- **GET 列表/自由结构**：`/requirements`、`/testcases`、`/test-executions/available-cases/list`、`/logs/sources`、`/logs/tail`、`/logs/errors/summary`、`/logs/errors/tail`。
- **POST 操作**：`/apifox/env-databases/{cid}/test`、`/apifox/projects/{pid}/tree/reorder`。

> 注：文件导出（`export/*`、`runs/{rid}/export`）返回 `Blob`、SSE 流方法返回 `void`，均为准确类型，非技术债。
