import type { FormInstance, FormRules } from 'element-plus'

export type { FormInstance, FormRules }

export type FormRuleItem = NonNullable<FormRules[string]>[number]
