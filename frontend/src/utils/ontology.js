/* eslint-disable */
// ============================================================================
// 【生成文件，禁止手改】由 backend/common/export_ontology.py 从 backend/common/ontology.py 生成
// 重新生成：python -m backend.common.export_ontology
// 七类实体 / 十类关系 / 中文名 / 色值 / 头尾约束 / 属性定义 / 枚举 / 七个历史时期（全站唯一来源镜像）
// ============================================================================

export const LABELS = [
  "Person",
  "Organization",
  "Event",
  "Meeting",
  "Location",
  "Document",
  "Period"
]

export const LABEL_ZH = {
  "Person": "人物",
  "Organization": "组织",
  "Event": "事件",
  "Meeting": "会议",
  "Location": "地点",
  "Document": "文献",
  "Period": "时期"
}

export const LABEL_COLOR = {
  "Person": "#C0392B",
  "Organization": "#E67E22",
  "Event": "#2E86C1",
  "Meeting": "#8E44AD",
  "Location": "#27AE60",
  "Document": "#B7950B",
  "Period": "#7F8C8D"
}

export const PROPS = {
  "Person": [
    {
      "name": "name",
      "zh": "姓名",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "birth_year",
      "zh": "出生年",
      "required": false,
      "kind": "number",
      "derived": false
    },
    {
      "name": "death_year",
      "zh": "逝世年",
      "required": false,
      "kind": "number",
      "derived": false
    },
    {
      "name": "birthplace",
      "zh": "籍贯",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "intro",
      "zh": "简介",
      "required": true,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "Organization": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "found_time_text",
      "zh": "成立时间",
      "required": false,
      "kind": "time",
      "derived": false
    },
    {
      "name": "time_sort",
      "zh": "排序键",
      "required": false,
      "kind": "text",
      "derived": true
    },
    {
      "name": "org_type",
      "zh": "组织类型",
      "required": true,
      "kind": "enum",
      "derived": false,
      "enum": [
        "政党",
        "军队",
        "群团",
        "机构"
      ]
    },
    {
      "name": "intro",
      "zh": "简介",
      "required": true,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "Event": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "time_text",
      "zh": "时间",
      "required": true,
      "kind": "time",
      "derived": false
    },
    {
      "name": "time_sort",
      "zh": "排序键",
      "required": true,
      "kind": "text",
      "derived": true
    },
    {
      "name": "time_precision",
      "zh": "时间精度",
      "required": true,
      "kind": "enum",
      "derived": true,
      "enum": [
        "day",
        "month",
        "year"
      ]
    },
    {
      "name": "content",
      "zh": "主要内容",
      "required": false,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "meaning",
      "zh": "历史意义",
      "required": false,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "intro",
      "zh": "简介",
      "required": true,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "Meeting": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "time_text",
      "zh": "时间",
      "required": true,
      "kind": "time",
      "derived": false
    },
    {
      "name": "time_sort",
      "zh": "排序键",
      "required": true,
      "kind": "text",
      "derived": true
    },
    {
      "name": "time_precision",
      "zh": "时间精度",
      "required": true,
      "kind": "enum",
      "derived": true,
      "enum": [
        "day",
        "month",
        "year"
      ]
    },
    {
      "name": "content",
      "zh": "主要内容",
      "required": false,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "meaning",
      "zh": "历史意义",
      "required": false,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "intro",
      "zh": "简介",
      "required": true,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "Location": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "modern_name",
      "zh": "今地名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": false,
      "kind": "text",
      "derived": false
    }
  ],
  "Document": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "alias",
      "zh": "别名",
      "required": false,
      "kind": "text",
      "derived": false
    },
    {
      "name": "pub_time_text",
      "zh": "发表时间",
      "required": false,
      "kind": "time",
      "derived": false
    },
    {
      "name": "time_sort",
      "zh": "排序键",
      "required": false,
      "kind": "text",
      "derived": true
    },
    {
      "name": "doc_type",
      "zh": "文献类型",
      "required": false,
      "kind": "enum",
      "derived": false,
      "enum": [
        "著作",
        "报告",
        "决议",
        "宣言",
        "章程"
      ]
    },
    {
      "name": "intro",
      "zh": "简介",
      "required": false,
      "kind": "longtext",
      "derived": false
    },
    {
      "name": "source",
      "zh": "来源",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "Period": [
    {
      "name": "name",
      "zh": "名称",
      "required": true,
      "kind": "text",
      "derived": false
    },
    {
      "name": "start_year",
      "zh": "起始年",
      "required": true,
      "kind": "number",
      "derived": false
    },
    {
      "name": "end_year",
      "zh": "结束年",
      "required": false,
      "kind": "number",
      "derived": false
    },
    {
      "name": "order",
      "zh": "序号(1-7)",
      "required": true,
      "kind": "number",
      "derived": false
    }
  ]
}

export const SYSTEM_PROPS = [
  "checked",
  "updated_at"
]

export const RELATIONS = [
  "LED",
  "PARTICIPATED_IN",
  "AUTHORED",
  "HELD_POSITION",
  "HELD_IN",
  "OCCURRED_IN",
  "PRODUCED",
  "FOUNDED",
  "REORGANIZED_TO",
  "BELONGS_TO"
]

export const RELATION_ZH = {
  "LED": "领导",
  "PARTICIPATED_IN": "参加",
  "AUTHORED": "创作",
  "HELD_POSITION": "任职",
  "HELD_IN": "召开于",
  "OCCURRED_IN": "发生于",
  "PRODUCED": "形成",
  "FOUNDED": "创建",
  "REORGANIZED_TO": "改编为",
  "BELONGS_TO": "属于时期"
}

export const RELATION_CONSTRAINTS = {
  "LED": [
    [
      "Person",
      "Event"
    ],
    [
      "Organization",
      "Event"
    ]
  ],
  "PARTICIPATED_IN": [
    [
      "Person",
      "Meeting"
    ]
  ],
  "AUTHORED": [
    [
      "Person",
      "Document"
    ]
  ],
  "HELD_POSITION": [
    [
      "Person",
      "Organization"
    ]
  ],
  "HELD_IN": [
    [
      "Meeting",
      "Location"
    ]
  ],
  "OCCURRED_IN": [
    [
      "Event",
      "Location"
    ]
  ],
  "PRODUCED": [
    [
      "Meeting",
      "Document"
    ]
  ],
  "FOUNDED": [
    [
      "Meeting",
      "Organization"
    ],
    [
      "Event",
      "Organization"
    ]
  ],
  "REORGANIZED_TO": [
    [
      "Organization",
      "Organization"
    ]
  ],
  "BELONGS_TO": [
    [
      "Event",
      "Period"
    ],
    [
      "Meeting",
      "Period"
    ]
  ]
}

export const RELATION_PROPS = {
  "HELD_POSITION": [
    {
      "name": "position",
      "zh": "职务",
      "required": true,
      "kind": "text",
      "derived": false
    }
  ],
  "REORGANIZED_TO": [
    {
      "name": "time_text",
      "zh": "改编时间",
      "required": false,
      "kind": "time",
      "derived": false
    }
  ]
}

export const ENUMS = {
  "org_type": [
    "政党",
    "军队",
    "群团",
    "机构"
  ],
  "doc_type": [
    "著作",
    "报告",
    "决议",
    "宣言",
    "章程"
  ],
  "time_precision": [
    "day",
    "month",
    "year"
  ]
}

export const PERIODS = [
  {
    "name": "建党初期与大革命时期",
    "order": 1,
    "start_year": 1921,
    "end_year": 1927,
    "start_sort": "19210701"
  },
  {
    "name": "土地革命战争时期",
    "order": 2,
    "start_year": 1927,
    "end_year": 1937,
    "start_sort": "19270801"
  },
  {
    "name": "全民族抗日战争时期",
    "order": 3,
    "start_year": 1937,
    "end_year": 1945,
    "start_sort": "19370707"
  },
  {
    "name": "解放战争时期",
    "order": 4,
    "start_year": 1945,
    "end_year": 1949,
    "start_sort": "19450903"
  },
  {
    "name": "社会主义革命和建设时期",
    "order": 5,
    "start_year": 1949,
    "end_year": 1978,
    "start_sort": "19491001"
  },
  {
    "name": "改革开放和社会主义现代化建设新时期",
    "order": 6,
    "start_year": 1978,
    "end_year": 2012,
    "start_sort": "19781218"
  },
  {
    "name": "中国特色社会主义新时代",
    "order": 7,
    "start_year": 2012,
    "end_year": null,
    "start_sort": "20121108"
  }
]


export const labelZh = (label) => LABEL_ZH[label] || label
export const labelColor = (label) => LABEL_COLOR[label] || '#999999'
export const relationZh = (rel) => RELATION_ZH[rel] || rel
export const formProps = (label) => (PROPS[label] || []).filter((p) => !p.derived)
export const requiredProps = (label) => formProps(label).filter((p) => p.required).map((p) => p.name)
export const allowedRelations = (headLabel) =>
  RELATIONS.filter((r) => RELATION_CONSTRAINTS[r].some(([h]) => h === headLabel))
export const allowedTails = (headLabel, rel) =>
  (RELATION_CONSTRAINTS[rel] || []).filter(([h]) => h === headLabel).map(([, t]) => t)
export const isAllowed = (headLabel, rel, tailLabel) =>
  (RELATION_CONSTRAINTS[rel] || []).some(([h, t]) => h === headLabel && t === tailLabel)
