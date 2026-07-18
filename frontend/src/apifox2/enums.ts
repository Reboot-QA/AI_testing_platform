// 从 Apifox-UI (React) 1:1 移植。因项目启用 isolatedModules，const enum 改为普通 enum。

/** HTTP 请求方法。 */
export enum HttpMethod {
  Get = 'GET',
  Post = 'POST',
  Put = 'PUT',
  Delete = 'DELETE',
  Head = 'HEAD',
  Options = 'OPTIONS',
  Patch = 'PATCH',
  Trace = 'TRACE',
}

/** API 状态。 */
export enum ApiStatus {
  Designing = 'designing',
  Pending = 'pending',
  Developing = 'developing',
  Obsolete = 'obsolete',
  Integrating = 'integrating',
  Testing = 'testing',
  Tested = 'tested',
  Released = 'released',
  Deprecated = 'deprecated',
  Exception = 'exception',
}

/** 接口菜单顶级目录的分类类型。 */
export enum CatalogType {
  /** 项目概况。 */
  Overview = 'overview',
  /** 接口。 */
  Http = 'http',
  /** 数据模型。 */
  Schema = 'schema',
  /** 快捷请求。 */
  Request = 'request',
  /** 回收站。 */
  Recycle = 'recycle',
  /** Markdown 文件。 */
  Markdown = 'markdown',
}

export enum MenuItemType {
  ApiDetail = 'apiDetail',
  ApiDetailFolder = 'apiDetailFolder',
  ApiSchema = 'apiSchema',
  ApiSchemaFolder = 'apiSchemaFolder',
  RequestFolder = 'requestFolder',
  HttpRequest = 'httpRequest',
  Doc = 'doc',
}

export enum MenuId {
  默认分组 = '.0',
  嵌套分组 = '.0.1',
  xx = '.0.1.0',
  示例接口 = '.0.1.1',
  示例接口2 = '.0.1.2',
  宠物店 = '.1',
  查询宠物详情 = '.1.2',
  新建宠物信息 = '.1.3',
  文档 = '.2',
  宠物店S = ',1',
  SchemaPet = ',1.1',
  SchemaCategory = ',1.2',
  SchemaTag = ',1.3',
  引用模型 = ',2',
  Request = '/1',
  Request2 = '/1.1',
}

export enum ParamType {
  Integer = 'integer',
  String = 'string',
  Boolean = 'boolean',
  Number = 'number',
  Array = 'array',
}

export enum ContentType {
  JSON = 'json',
  XML = 'xml',
  HTML = 'html',
  Raw = 'raw',
  Binary = 'binary',
}

export enum BodyType {
  None = 'none',
  FormData = 'multipart/form-data',
  UrlEncoded = 'application/x-www-form-urlencoded',
  Json = 'application/json',
  Xml = 'application/xml',
  Raw = 'text/plain',
  Binary = 'application/octet-stream',
}
