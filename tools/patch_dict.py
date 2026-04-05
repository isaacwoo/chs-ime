# tools/patch_dict.py
# -*- coding: utf-8 -*-
"""
Patch data/pinyin_dict.json with proper frequencies for common Chinese
characters and phrases.

The original build_dict.py assigns character frequencies via a phrase-head-count
proxy and phrase frequencies via file-rank (NOT frequency-ordered).  This causes
common words like 个(ge) and phrases like 这个(zhege), 问题(wenti) to receive
artificially low frequencies, making them hard or impossible to type.

Run once on dev machine after building or updating the base dictionary:
    python tools/patch_dict.py

Overwrites data/pinyin_dict.json in place and removes any stale .pkl cache.
"""

import json
import os

DICT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "pinyin_dict.json")
)

# ── Frequency overrides ───────────────────────────────────────────────────────
# Format: (pinyin_no_tone, word, frequency)
# Normal scale: 1–99000 (same as most of the dictionary).
# CRITICAL tier (100001–110000): used for words that MUST rank first and whose
#   pinyin key may also have high-frequency artifacts from the phrase file (which
#   can assign up to 100000 for entries appearing early in the alphabetically-
#   ordered source file).  Using 100001+ ensures our override always wins.
# Sources: Modern Chinese Character Frequency List (北京语言大学 / BCC语料库),
#          HSK vocabulary lists, SUBTLEX-CH (relative ordering used as guide).
# Pinyin: tone-free, ü→v (e.g. 女 nv, 绿 lv).

FREQ_OVERRIDES: list[tuple[str, str, int]] = [

    # ════════════════════════════════════════════════════════════════════════════
    # CRITICAL tier (>100000): common words that are often buried by phrase-file
    # artifacts.  Set well above the phrase file's maximum (100000).
    # ════════════════════════════════════════════════════════════════════════════
    ("yijing",  "已经",  105000),   # phrase file gives 一境 freq=99454, must beat it
    ("beijing", "北京",  104000),   # high freq for both direct lookup & abbrev 'bj'
    ("shanghai","上海",  103500),
    ("zhongguo","中国",  103000),
    ("women",   "我们",  102500),
    ("nimen",   "你们",  102500),
    ("tamen",   "他们",  102000),
    ("zhege",   "这个",  105000),   # was freq=1, critical common phrase
    ("nage",    "那个",  104500),
    ("yige",    "一个",  105000),
    ("shenme",  "什么",  104000),
    ("meiyou",  "没有",  103500),
    ("wenti",   "问题",  105000),   # was freq=1
    ("gongzuo", "工作",  104500),
    ("nihao",   "你好",  105000),
    ("zaijian", "再见",  104000),
    ("xiexie",  "谢谢",  104500),
    ("xiexi",   "谢谢",  104500),   # alternate romanization in some dicts
    ("duibuqi", "对不起",104000),
    ("meiguanxi","没关系",103500),
    ("buhaoyisi","不好意思",103000),
    ("keyi",    "可以",  103500),
    ("zhidao",  "知道",  103000),
    ("yinwei",  "因为",  102500),
    ("suoyi",   "所以",  102500),
    ("danshi",  "但是",  102000),
    ("ruguo",   "如果",  102000),
    ("feichang","非常",  102000),
    ("yinggai", "应该",  101500),
    ("renwei",  "认为",  101500),
    ("xiwang",  "希望",  101000),
    ("xihuan",  "喜欢",  101000),
    ("xuyao",   "需要",  101500),
    ("liaojie", "了解",  101000),
    ("jiejue",  "解决",  101000),
    ("tigao",   "提高",  101000),
    ("weishenme","为什么",104000),
    ("zenme",   "怎么",  103000),
    ("zheyang", "这样",  102000),
    ("nayang",  "那样",  101500),
    ("xianzai", "现在",  103000),
    ("yiqian",  "以前",  102000),
    ("yihou",   "以后",  102000),
    ("ranhou",  "然后",  101500),
    ("zuihou",  "最后",  101000),
    ("meitian", "每天",  101000),
    ("jintian", "今天",  102000),
    ("mingtian","明天",  101500),
    ("zuotian", "昨天",  101000),
    ("shangwu", "上午",  101000),
    ("xiawu",   "下午",  101500),
    ("wanshang","晚上",  101000),
    ("zaoshang","早上",  101000),
    ("tianqi",  "天气",  101000),
    ("shouji",  "手机",  103000),
    ("diannao", "电脑",  102500),
    ("dianhua", "电话",  102000),
    ("wangluo", "网络",  102000),
    ("xitong",  "系统",  101500),
    ("ruanjian","软件",  101000),

    # ════════════════════════════════════════════════════════════════════════════
    # SINGLE CHARACTERS  (top ~150 by usage frequency)
    # ════════════════════════════════════════════════════════════════════════════
    ("de",    "的",  99000),
    ("yi",    "一",  98500),
    ("shi",   "是",  98000),
    ("bu",    "不",  97500),
    ("le",    "了",  97000),
    ("ren",   "人",  96500),
    ("wo",    "我",  96000),
    ("zai",   "在",  95500),
    ("you",   "有",  95000),
    ("ta",    "他",  94500),
    ("zhe",   "这",  94000),
    ("wei",   "为",  93500),
    ("zhi",   "之",  93000),
    ("da",    "大",  92500),
    ("lai",   "来",  92000),
    ("yi",    "以",  91500),
    ("ge",    "个",  91000),   # ← was rank 7, pruned by old BEAM_WIDTH=5
    ("zhong", "中",  90500),
    ("shang", "上",  90000),
    ("men",   "们",  89500),
    ("dao",   "到",  89000),
    ("shuo",  "说",  88500),
    ("guo",   "国",  88000),
    ("he",    "和",  87500),
    ("di",    "地",  87000),
    ("ye",    "也",  86500),
    ("zi",    "子",  86000),
    ("shi",   "时",  85500),
    ("dao",   "道",  85000),
    ("chu",   "出",  84500),
    ("er",    "而",  84000),
    ("yao",   "要",  83500),
    ("yu",    "于",  83000),
    ("jiu",   "就",  82500),
    ("dou",   "都",  82000),
    ("qu",    "去",  81500),
    ("neng",  "能",  81000),
    ("hao",   "好",  80500),
    ("duo",   "多",  80000),
    ("hai",   "还",  79500),
    ("dui",   "对",  79000),
    ("zhe",   "着",  78500),
    ("mei",   "没",  78000),
    ("nian",  "年",  77500),
    ("tong",  "同",  77000),
    ("hou",   "后",  76500),
    ("kan",   "看",  76000),
    ("fa",    "发",  75500),
    ("xia",   "下",  75000),
    ("li",    "里",  74500),
    ("fang",  "方",  74000),
    ("ke",    "可",  73500),
    ("ni",    "你",  73000),
    ("na",    "那",  72500),
    ("zi",    "自",  72000),
    ("dong",  "动",  71500),
    ("xiao",  "小",  71000),
    ("cheng", "成",  70500),
    ("yu",    "与",  70000),
    ("hui",   "会",  69500),
    ("xin",   "心",  69000),
    ("sheng", "生",  68500),
    ("guo",   "过",  68000),
    ("xiang", "想",  67500),
    ("yong",  "用",  67000),
    ("li",    "力",  66500),
    ("zhi",   "知",  66000),
    ("qing",  "情",  65500),
    ("wen",   "问",  65000),
    ("ti",    "题",  64500),
    ("gong",  "工",  64000),
    ("zuo",   "作",  63500),
    ("shou",  "手",  63000),
    ("min",   "民",  62500),
    ("gao",   "高",  62000),
    ("chang", "长",  61500),
    ("fen",   "分",  61000),
    ("da",    "打",  60500),
    ("xing",  "行",  60000),
    ("ri",    "日",  59500),
    ("yue",   "月",  59000),
    ("dong",  "东",  58500),
    ("xi",    "西",  58000),
    ("nan",   "南",  57500),
    ("bei",   "北",  57000),
    ("qian",  "前",  56500),
    ("zuo",   "左",  56000),
    ("you",   "右",  55500),
    ("jing",  "经",  55000),
    ("yi",    "已",  54500),
    ("suo",   "所",  54000),
    ("mian",  "面",  53500),
    ("cong",  "从",  53000),
    ("fa",    "法",  52500),
    ("shi",   "事",  52000),
    ("kai",   "开",  51500),
    ("ta",    "它",  51000),
    ("ta",    "她",  50500),
    ("zhe",   "者",  50000),
    ("ran",   "然",  49500),
    ("dang",  "当",  49000),
    ("jia",   "家",  48500),
    ("jian",  "见",  46500),
    ("xian",  "先",  46000),
    ("jian",  "间",  45500),
    ("hua",   "话",  45000),
    ("ma",    "吗",  44500),
    ("ne",    "呢",  44000),
    ("ba",    "吧",  43500),
    ("a",     "啊",  43000),
    ("ya",    "呀",  42500),
    ("na",    "哪",  41000),
    ("an",    "安",  38500),
    ("ding",  "定",  38000),
    ("she",   "设",  37000),
    ("bei",   "被",  36500),
    ("ying",  "应",  36000),
    ("gei",   "给",  35500),
    ("rang",  "让",  35000),
    ("ba",    "把",  34500),
    ("xue",   "学",  34000),
    ("jiao",  "叫",  33500),
    ("zuo",   "做",  33000),
    ("zhi",   "只",  32500),
    ("dian",  "点",  32000),
    ("ai",    "爱",  31500),
    ("jie",   "解",  28000),
    ("ti",    "提",  27500),
    ("jian",  "建",  26500),
    ("she",   "社",  26000),
    ("hui",   "回",  25500),
    ("jin",   "进",  25000),
    ("wen",   "文",  24500),
    ("hua",   "化",  24000),
    ("ke",    "科",  23000),
    ("ji",    "技",  22500),
    ("ji",    "机",  22000),
    ("dian",  "电",  21500),
    ("wang",  "网",  21000),
    ("shang", "商",  20000),
    ("ting",  "听",  30000),
    ("xie",   "写",  29500),

    # ════════════════════════════════════════════════════════════════════════════
    # MULTI-CHARACTER PHRASES
    # ════════════════════════════════════════════════════════════════════════════

    # Greetings & basics
    ("nihao",       "你好",     95000),
    ("zaijian",     "再见",     88500),
    ("xièxiè",      "谢谢",     89000),
    ("xiexie",      "谢谢",     89000),
    ("duibuqi",     "对不起",   88000),
    ("meiguanxi",   "没关系",   87000),
    ("buhaoyisi",   "不好意思", 86000),
    ("zaoshanghao", "早上好",   80000),
    ("wanshanghao", "晚上好",   79000),
    ("xinniankuaile","新年快乐", 71000),
    ("shengrikuaile","生日快乐", 72000),
    ("xinnianhao",  "新年好",   70000),
    ("qingwen",     "请问",     70000),
    ("buyongxie",   "不用谢",   75000),

    # Pronouns / basic words
    ("women",   "我们",  96000),
    ("nimen",   "你们",  96000),
    ("tamen",   "他们",  95500),
    ("tamen",   "她们",  94000),
    ("ziji",    "自己",  82000),
    ("dajia",   "大家",  80000),
    ("meige",   "每个",  61500),
    ("yige",    "一个",  95000),

    # Demonstratives
    ("zhege",   "这个",  95000),   # ← was freq=1
    ("nage",    "那个",  94500),
    ("zhexie",  "这些",  82500),
    ("naxie",   "那些",  82000),
    ("zheli",   "这里",  81500),
    ("nali",    "那里",  81000),
    ("nali",    "哪里",  77500),
    ("zheyang", "这样",  80500),
    ("nayang",  "那样",  80000),

    # Question words
    ("shenme",      "什么",     94000),
    ("zenme",       "怎么",     79500),
    ("zenyang",     "怎样",     78500),
    ("weishenme",   "为什么",   79000),
    ("ruhe",        "如何",     78000),
    ("sheme",       "什么",     93500),  # colloquial spelling variant

    # Common auxiliaries / connectives
    ("yinwei",  "因为",  90000),
    ("suoyi",   "所以",  89500),
    ("danshi",  "但是",  89000),
    ("ruguo",   "如果",  88500),
    ("yijing",  "已经",  88000),
    ("suiran",  "虽然",  87500),
    ("bingqie", "并且",  87000),
    ("huozhe",  "或者",  86500),
    ("erqie",   "而且",  86000),
    ("yinci",   "因此",  85500),
    ("suoyi",   "所以",  89500),
    ("ranhou",  "然后",  85000),
    ("tongguo", "通过",  84500),
    ("anzhao",  "按照",  84000),
    ("genju",   "根据",  83500),
    ("duiyu",   "对于",  83000),
    ("guanyu",  "关于",  82500),
    ("youyu",   "由于",  82000),
    ("zhiyou",  "只有",  81500),
    ("zhiyao",  "只要",  81000),
    ("zhishi",  "只是",  80500),
    ("jinguan", "尽管",  80000),
    ("buguan",  "不管",  79500),
    ("wulun",   "无论",  79000),
    ("renhe",   "任何",  78500),
    ("suoyou",  "所有",  85000),

    # Common adjectives / adverbs
    ("xuyao",    "需要",  87500),
    ("feichang", "非常",  87000),
    ("yinggai",  "应该",  86500),
    ("yiding",   "一定",  84500),
    ("yiyang",   "一样",  85500),
    ("yiban",    "一般",  85000),
    ("yixie",    "一些",  86000),
    ("daduoshu", "大多数",75000),
    ("dabufen",  "大部分",74000),
    ("quanbu",   "全部",  80500),
    ("bufen",    "部分",  80000),
    ("wanquan",  "完全",  79000),
    ("zhongyao", "重要",  82000),
    ("jiben",    "基本",  81500),
    ("zhuyao",   "主要",  81000),
    ("qishi",    "其实",  80000),
    ("daodi",    "到底",  78000),
    ("jiujing",  "究竟",  76000),
    ("haode",    "好的",  70000),
    ("shide",    "是的",  77000),
    ("bushi",    "不是",  76500),
    ("meicuo",   "没错",  74500),
    ("bucuo",    "不错",  75000),

    # Time words
    ("jintian",  "今天",  80500),
    ("zuotian",  "昨天",  80000),
    ("mingtian", "明天",  79500),
    ("xianzai",  "现在",  87000),
    ("yiqian",   "以前",  86500),
    ("yihou",    "以后",  86000),
    ("zuijin",   "最近",  84500),
    ("weilai",   "未来",  82000),
    ("guoqu",    "过去",  82000),
    ("muqian",   "目前",  85000),
    ("dangqian", "当前",  84000),
    ("jianglai", "将来",  83000),
    ("meitian",  "每天",  81000),
    ("shangwu",  "上午",  78000),
    ("xiawu",    "下午",  77500),
    ("wanshang", "晚上",  77000),
    ("zaoshang", "早上",  76500),
    ("zhongwu",  "中午",  76000),
    ("xingqi",   "星期",  75000),
    ("zhoumo",   "周末",  74000),

    # Quantifiers / measures
    ("yici",    "一次",  77500),
    ("yixia",   "一下",  87000),
    ("yiqi",    "一起",  86500),
    ("yigong",  "一共",  84000),
    ("yiqie",   "一切",  83500),
    ("yizhong", "一种",  83000),
    ("yidian",  "一点",  82000),
    ("zuida",   "最大",  74000),
    ("zuihao",  "最好",  83500),
    ("zuishao", "最少",  73000),
    ("zuiduo",  "最多",  72500),
    ("zuihou",  "最后",  85000),

    # Common phrases (everyday conversation)
    ("meiyou",    "没有",    93500),
    ("keyi",      "可以",    93000),
    ("zhidao",    "知道",    92500),
    ("juede",     "觉得",    85500),
    ("renwei",    "认为",    86000),
    ("xiwang",    "希望",    85000),
    ("xihuan",    "喜欢",    84500),
    ("zhengzai",  "正在",    80000),
    ("hao吧",     "好吧",    73500),  # will likely not match due to Chinese char
    ("haoba",     "好吧",    73500),
    ("zhende",    "真的",    73000),
    ("meishi",    "没事",    69500),
    ("gaoxing",   "高兴",    68500),
    ("kaixin",    "开心",    68000),
    ("haokan",    "好看",    60000),
    ("haochi",    "好吃",    60000),
    ("laoban",    "老板",    65000),
    ("laoshi",    "老师",    73000),
    ("xuesheng",  "学生",    73500),
    ("pengyou",   "朋友",    72500),
    ("tongxue",   "同学",    72000),
    ("tongshi",   "同事",    71500),
    ("xiansheng", "先生",    72500),
    ("xiaojie",   "小姐",    72000),
    ("tongzhi",   "同志",    70000),

    # Problem + work vocabulary
    ("wenti",    "问题",   92000),   # ← was freq=1
    ("gongzuo",  "工作",   91500),
    ("shijian",  "时间",   91000),
    ("guojia",   "国家",   81500),
    ("fazhan",   "发展",   82500),
    ("shehui",   "社会",   82000),
    ("wenhua",   "文化",   81000),
    ("jingji",   "经济",   80500),
    ("jishu",    "技术",   80000),
    ("jiaoyu",   "教育",   79500),
    ("yiyuan",   "医院",   79000),
    ("chanpin",  "产品",   76000),
    ("yonghu",   "用户",   75500),
    ("xiangmu",  "项目",   76500),
    ("tuandui",  "团队",   77000),
    ("fangan",   "方案",   80000),
    ("jihua",    "计划",   79500),
    ("mubiao",   "目标",   79000),
    ("jiegou",   "结构",   78500),
    ("liucheng", "流程",   78000),
    ("fangfa",   "方法",   77500),
    ("gongneng", "功能",   80000),
    ("xingneng", "性能",   75000),
    ("youhua",   "优化",   74000),
    ("gaijin",   "改进",   73000),
    ("wanshan",  "完善",   72000),
    ("chuli",    "处理",   78000),
    ("yunxing",  "运行",   75000),
    ("qidong",   "启动",   74000),
    ("guanbi",   "关闭",   73000),
    ("shezhi",   "设置",   75000),
    ("peizhi",   "配置",   74000),
    ("canshu",   "参数",   73000),
    ("ceshi",    "测试",   71500),
    ("baogao",   "报告",   70500),
    ("fenxi",    "分析",   74000),
    ("zongjie",  "总结",   73000),
    ("jieguo",   "结果",   72500),
    ("neirong",  "内容",   72000),
    ("xinxi",    "信息",   70500),
    ("shuju",    "数据",   70000),
    ("wenjian",  "文件",   67500),
    ("wendang",  "文档",   67000),
    ("chengxu",  "程序",   69500),
    ("ruanjian", "软件",   69000),
    ("yingjian", "硬件",   68500),
    ("xitong",   "系统",   68000),
    ("wangluo",  "网络",   77000),
    ("hulianwang","互联网", 76500),
    ("dianhua",  "电话",   78500),
    ("diannao",  "电脑",   78000),
    ("shouji",   "手机",   77500),
    ("jianpan",  "键盘",   68500),
    ("shubiao",  "鼠标",   68000),
    ("pingmu",   "屏幕",   67500),
    ("anquan",   "安全",   75500),
    ("mima",     "密码",   65000),
    ("zhanghu",  "账户",   64500),
    ("denglu",   "登录",   64000),
    ("zhuce",    "注册",   63500),
    ("queren",   "确认",   65000),
    ("wancheng", "完成",   80000),
    ("jinxing",  "进行",   80000),
    ("zhichi",   "支持",   80000),
    ("fuwu",     "服务",   80000),
    ("zhiliang", "质量",   75000),
    ("bangzhu",  "帮助",   74000),
    ("liaojie",  "了解",   84000),
    ("tigao",    "提高",   83500),
    ("jiejue",   "解决",   83000),

    # Technology / internet
    ("sousu",    "搜索",   73000),
    ("sousuo",   "搜索",   73000),
    ("dianji",   "点击",   77000),
    ("xiazai",   "下载",   67000),
    ("shangchuan","上传",   66000),
    ("anzhuang", "安装",   65000),
    ("fuzhi",    "复制",   69500),
    ("zhantie",  "粘贴",   69000),
    ("shanchu",  "删除",   70000),
    ("baocun",   "保存",   70500),
    ("quxiao",   "取消",   71000),
    ("queding",  "确定",   71500),
    ("xuanze",   "选择",   72000),
    ("fasong",   "发送",   75500),
    ("jieshou",  "接收",   75000),
    ("xiaoxi",   "消息",   74500),
    ("tongzhi",  "通知",   74000),
    ("youjian",  "邮件",   76000),
    ("pinglun",  "评论",   73000),
    ("fenxiang", "分享",   72000),
    ("guanzhu",  "关注",   70000),
    ("dianzan",  "点赞",   69000),
    ("shoucan",  "收藏",   68000),

    # Countries / places
    ("zhongguo", "中国",   76000),
    ("beijing",  "北京",   75500),
    ("shanghai", "上海",   75000),
    ("riben",    "日本",   67000),
    ("meiguo",   "美国",   66000),
    ("yingguo",  "英国",   65500),
    ("faguo",    "法国",   65000),
    ("deguo",    "德国",   64500),
    ("hanguo",   "韩国",   64000),
    ("shijie",   "世界",   80000),
    ("quanqiu",  "全球",   79000),
    ("tianqi",   "天气",   80000),
    ("kongqi",   "空气",   75000),
    ("huanjing", "环境",   80000),
    ("ziran",    "自然",   80000),

    # Communication
    ("liaotian", "聊天",   75000),
    ("shuohua",  "说话",   74500),
    ("huida",    "回答",   75000),
    ("huifu",    "回复",   74000),
    ("lianxi",   "联系",   72500),
    ("hezuo",    "合作",   72000),
    ("jiaoliu",  "交流",   71500),
    ("shuoming", "说明",   74000),
    ("cankao",   "参考",   70000),
    ("yanjiu",   "研究",   75000),
    ("jiancha",  "检查",   71000),
    ("yanzheng", "验证",   70000),
    ("tijiao",   "提交",   74000),
    ("shenqing", "申请",   73000),
    ("pizhun",   "批准",   71000),
    ("luoshi",   "落实",   73000),
    ("zhixing",  "执行",   72000),
    ("jiankong", "监控",   70000),
    ("weihu",    "维护",   72000),

    # School / knowledge
    ("xuexiao",  "学校",   74000),
    ("kaoshi",   "考试",   75000),
    ("chengji",  "成绩",   74000),
    ("fenshu",   "分数",   74000),
    ("dengji",   "等级",   73000),
    ("jiben",    "基本",   81500),
    ("biaozhun", "标准",   71500),
    ("guize",    "规则",   71000),
    ("celue",    "策略",   70500),
    ("shichang", "市场",   74500),
    ("gongsi",   "公司",   74500),
    ("lingdao",  "领导",   71000),
    ("guanli",   "管理",   70500),
    ("chuangxin","创新",   73500),
    ("diaocha",  "调查",   71000),
    ("tongji",   "统计",   70000),
]


def patch(dict_path: str) -> None:
    print(f"Loading {dict_path} ...")
    with open(dict_path, "r", encoding="utf-8") as f:
        data: dict[str, list[dict]] = json.load(f)

    updates = 0
    inserts = 0

    for pinyin, word, freq in FREQ_OVERRIDES:
        if not pinyin or not word:
            continue
        # Skip entries with non-ASCII pinyin keys (typos in this list)
        if not pinyin.isascii():
            continue
        entries = data.setdefault(pinyin, [])
        found = False
        for entry in entries:
            if entry["word"] == word:
                if entry["freq"] < freq:
                    entry["freq"] = freq
                    updates += 1
                found = True
                break
        if not found:
            entries.append({"word": word, "freq": freq})
            inserts += 1

    # Re-sort all modified entry lists by freq desc
    for entries in data.values():
        entries.sort(key=lambda e: -e["freq"])

    print(f"  {updates} frequencies updated, {inserts} new entries inserted")

    print("Writing patched dictionary ...")
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(dict_path) / 1024 / 1024
    print(f"  Done. File size: {size_mb:.1f} MB")

    # Remove stale pickle cache so the app rebuilds from fresh JSON
    pkl_path = os.path.splitext(dict_path)[0] + ".pkl"
    if os.path.exists(pkl_path):
        os.remove(pkl_path)
        print(f"  Deleted stale cache: {pkl_path}")
    else:
        print("  No cache file to delete.")


if __name__ == "__main__":
    patch(DICT_PATH)
