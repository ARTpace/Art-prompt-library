# 风格包详细分类表 v1.1（建议稿）

日期：2026-11-01。配套文档：[风格包数据与分类规范](style-pack-spec-v1.md)。

本文是后续整理风格包的目标分类表，不代表当前数据已经完成分类。分类 ID 确认后保持稳定，中文名可以调整。当前程序支持“大类 → 子类 → 条目”的嵌套结构；标签、审核状态和结构化来源的界面支持尚待实现。

## 1. 分类原则

每条提示词保留一个主大类和一个主子类存储位置，可以匹配该大类下多个子类；匹配关系保存在 `classification.subcategories`，不复制条目。可以另有多个标签。按“主要交付物和提示词的核心目的”归属，不按标题中的第一个关键词归属。

- 人像摄影里的复古、胶片、黑白：属于摄影，其他特征作标签。
- 摄影质感的商品广告海报：如果提示词明确要求广告排版、标语或品牌传播，属于商业设计。
- 有动漫角色的实物摆件：如果重点是三维摆件，属于数字 3D，而不是动漫。
- 任意题材可套用的水彩技法模板：属于绘画；以人物故事为目的的动漫插画属于动漫。
- 提示词主要描述可通用的年代、艺术流派或视觉语言时，归艺术风格；出现某个风格词本身不构成归类依据。
- 来源不是分类。ChatGPT、Nano Banana、腾讯元宝、Fooocus、SAI、DIVA 等保存为来源或系列。
- 无法可靠判断的条目进入“待分类”，不归入“通用模板”掩盖问题。

分类表中的例词仅帮助理解，不是机械匹配规则。当前仅按标题分类；大类明确但子类未定进入该大类“待细分”，大类未定进入全局“待分类”。不使用正文、原分类、来源或图片推断；标题分类不等于人工审核。

## 2. 大类总表

| 顺序 | 大类 ID | 名称 | 归属判断 |
|---|---|---|---|
| 10 | `photography` | 摄影 | 以拍摄成片为目标，主体、镜头、布光等摄影表达是核心 |
| 20 | `anime_manga` | 动漫 | 动漫人物、漫画叙事或动画画面是核心 |
| 30 | `painting` | 绘画插画 | 绘画媒介、插画表达或手绘创作是核心 |
| 40 | `digital_3d` | 数字 3D | 三维建模、材质、渲染或数字场景表达是核心 |
| 50 | `commercial` | 商业设计 | 面向品牌、传播、包装、信息传达或界面设计的交付物 |
| 60 | `film_cinema` | 电影叙事 | 电影镜头、叙事场面、分镜或影视制作是核心 |
| 70 | `crafts` | 手工艺 | 纸、布、泥、木等实物工艺的制作形态是核心 |
| 80 | `art_movements` | 艺术风格 | 可跨题材复用的艺术流派、视觉语言和年代造型模板 |
| 90 | `general` | 通用模板 | 明确用于跨题材构图、编辑、提示词组织等通用任务 |
| 999 | `uncategorized` | 待分类 | 信息不足、混合目的难以判断、待人工整理 |

子类 ID 在全库唯一，以 `<大类 ID>_<子类名>` 命名。以下每行是一项可直接登记到风格包的标准子类。

## 3. 摄影 `photography`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `photography_portrait` | 人物肖像 | 单人肖像、证件肖像、艺术写真；核心为人物而非衣服销售 |
| `photography_fashion` | 时尚服饰 | 时装大片、穿搭、服饰展示、模特杂志摄影；海报排版归商业 |
| `photography_beauty` | 美妆特写 | 面部、妆容、发型、美甲摄影；化妆品瓶体归产品静物 |
| `photography_family` | 家庭儿童 | 家庭合照、亲子、儿童、婴儿摄影 |
| `photography_wedding` | 婚礼情侣 | 婚礼记录、婚纱写真、情侣写真 |
| `photography_product` | 产品静物 | 商品、珠宝、器物、静物布光；完整广告设计归商业 |
| `photography_food` | 美食饮品 | 菜品、甜点、食材、饮品、餐饮成片 |
| `photography_architecture` | 建筑空间 | 建筑外观、室内、家居、空间摄影；三维空间方案归数字 3D |
| `photography_landscape` | 自然风光 | 山海、森林、湖泊、自然景观摄影 |
| `photography_city` | 城市旅行 | 城市风貌、地标、旅行景点和建筑群的环境记录 |
| `photography_documentary` | 街头纪实 | 以人物活动、生活事件、社会观察为重点的街拍与纪实 |
| `photography_animals` | 动物宠物 | 宠物、野生动物、鸟类的摄影表达 |
| `photography_macro` | 微距细节 | 花蕊、昆虫、材质、液滴等，微距观察是主要意图 |
| `photography_sports` | 运动赛事 | 竞技、健身、舞蹈动作、赛事现场摄影 |
| `photography_vehicles` | 汽车交通 | 汽车、摩托、飞机、列车等交通工具摄影 |
| `photography_astro` | 天文星空 | 星轨、银河、天文观测、夜空摄影；普通夜景不是此类 |
| `photography_other` | 其他摄影 | 明确是摄影，但不属于以上主题；需记录整理理由 |

交叉示例：微距珠宝若目的是卖点展示，选产品静物并加微距标签；若核心是放大观察表面结构，选微距细节。宠物婚礼合照以情侣写真为主要任务时，归婚礼情侣并加宠物标签。

## 4. 动漫 `anime_manga`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `anime_manga_portrait` | 动漫头像 | 动漫头像、半身头像、角色头部表达 |
| `anime_manga_character` | 角色立绘 | 全身立绘、服装设定、单角色展示 |
| `anime_manga_model_sheet` | 角色设定表 | 三视图、转面、表情表、动作表、设定拆解 |
| `anime_manga_illustration` | 主题插画 | 以角色和场景共同叙事的单幅插画 |
| `anime_manga_comic` | 漫画分格 | 分格漫画、条漫、对白与连续画格 |
| `anime_manga_chibi` | Q 版角色 | 以 Q 版比例、萌化人物形态为核心的模板 |
| `anime_manga_scene` | 动漫场景 | 动画背景、校园、城市、奇幻环境，不以单人展示为主 |
| `anime_manga_mecha` | 机甲载具 | 动漫机械、机甲、战斗载具设定 |
| `anime_manga_creature` | 生物怪物 | 动漫生物、魔物、精灵与拟人种族设定 |
| `anime_manga_animation_frame` | 动画画面 | 动画截图感、关键帧、赛璐璐镜头画面 |
| `anime_manga_other` | 其他动漫 | 明确为动漫创作但无法落入以上子类 |

具体画师和角色的专用数据仍由画师库、角色库管理，风格包不复制整份画师或角色数据库。

## 5. 绘画插画 `painting`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `painting_oil` | 油画 | 油彩、厚涂、布面油画技法模板 |
| `painting_watercolor` | 水彩水粉 | 水彩、水粉、透明叠色、晕染 |
| `painting_ink` | 水墨国画 | 水墨、工笔、写意、国画笔墨 |
| `painting_sketch` | 素描速写 | 铅笔、炭笔、结构素描、人物速写 |
| `painting_line` | 线描钢笔 | 线描、钢笔、针管笔、轮廓线表现 |
| `painting_pastel` | 色粉蜡笔 | 粉彩、蜡笔、油画棒、彩铅表现 |
| `painting_gouache_acrylic` | 丙烯装饰画 | 丙烯、平涂装饰性绘画 |
| `painting_digital` | 数字绘画 | 明确以数字笔刷、数字厚涂为核心的绘画模板 |
| `painting_editorial` | 编辑插画 | 文章配图、概念性主题插画、社会议题表达 |
| `painting_children` | 儿童绘本 | 绘本画面、童书故事、儿童叙事插画 |
| `painting_botanical` | 博物图鉴 | 植物、动物、器物的手绘图鉴；信息排版为主则归商业 |
| `painting_printmaking` | 版画拓印 | 木刻、铜版、丝网、套色印刷的绘画技法 |
| `painting_other` | 其他绘画 | 其他可确定的绘画或插画表达 |

## 6. 数字 3D `digital_3d`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `digital_3d_character` | 三维角色 | 三维人物、虚拟角色、卡通角色渲染 |
| `digital_3d_toy` | 潮玩手办 | 手办、盲盒、公仔、收藏摆件的数字设计 |
| `digital_3d_product` | 产品渲染 | 工业产品、电子设备、器物的三维渲染 |
| `digital_3d_architecture` | 建筑室内 | 建筑可视化、室内效果图、空间设计渲染 |
| `digital_3d_environment` | 场景环境 | 游戏场景、数字世界、奇幻环境 |
| `digital_3d_diorama` | 微缩等距 | 微缩场景、等距房间、立体沙盘 |
| `digital_3d_material` | 材质纹理 | PBR 外观、无缝纹理、材质球、表面研究；不承诺生成完整 PBR 通道 |
| `digital_3d_abstract` | 抽象装置 | 流体、几何装置、程序造型、抽象三维构成 |
| `digital_3d_assets` | 游戏资产 | 明确面向模型资产展示的道具、武器、模块组件 |
| `digital_3d_other` | 其他三维 | 其他以建模或渲染为核心的三维表达 |

## 7. 商业设计 `commercial`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `commercial_brand` | 品牌标识 | Logo、品牌识别、标志及品牌视觉系统 |
| `commercial_poster` | 海报广告 | 营销海报、宣传广告、活动主视觉 |
| `commercial_ecommerce` | 电商详情 | 电商主图、详情页、促销商品信息图 |
| `commercial_packaging` | 包装设计 | 包装盒、标签、袋装、瓶贴设计；只拍包装归摄影 |
| `commercial_social` | 社交封面 | 社媒配图、视频封面、缩略图、内容平台封面 |
| `commercial_editorial` | 书刊出版 | 书籍封面、杂志排版、画册和出版物版式 |
| `commercial_infographic` | 信息图表 | 信息图、知识卡、数据图、说明图、图解排版 |
| `commercial_ui` | 界面设计 | 网页、应用、仪表盘、界面视觉方案 |
| `commercial_icon` | 图标符号 | 应用图标、功能图标、符号系统 |
| `commercial_typography` | 字体字效 | 艺术字、字体设计、文字视觉效果 |
| `commercial_ip` | IP 吉祥物 | 品牌吉祥物、商业 IP 角色方案；重点是品牌用途 |
| `commercial_merch` | 文创周边 | 贴纸、徽章、服装印花、文具等商品设计 |
| `commercial_presentation` | 演示展示 | 演示页、展板、方案板、作品集版式 |
| `commercial_other` | 其他商业 | 其他明确用于设计交付的视觉方案 |

## 8. 电影叙事 `film_cinema`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `film_cinema_shot` | 单镜头画面 | 电影剧照感、叙事单帧、导演镜头模板 |
| `film_cinema_storyboard` | 分镜故事板 | 多镜头分镜、故事板、镜头规划 |
| `film_cinema_character` | 影视人物 | 以电影角色造型、服化道、戏剧性人物塑造为核心 |
| `film_cinema_environment` | 影视场景 | 片场、美术场景、叙事空间设计 |
| `film_cinema_action` | 动作场面 | 追逐、战斗、灾难等动态叙事情境 |
| `film_cinema_mood` | 电影氛围 | 可套用的电影布光、色彩、画幅和情绪镜头语言 |
| `film_cinema_other` | 其他影视 | 其他以影视制作或叙事为核心的模板 |

“赛博朋克、科幻、惊悚、西部”等可同时出现在多个子类，作为题材或情绪标签，不重复建子类。

## 9. 手工艺 `crafts`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `crafts_paper` | 纸艺剪纸 | 折纸、剪纸、衍纸、纸雕、纸模型 |
| `crafts_textile` | 纺织刺绣 | 刺绣、编织、针织、布艺、织毯 |
| `crafts_clay` | 陶瓷黏土 | 陶瓷、黏土、软陶及其手作质感 |
| `crafts_wood` | 木作雕刻 | 木雕、木工、木质手作 |
| `crafts_metal` | 金属工艺 | 金工、珐琅、手作首饰、锻造 |
| `crafts_glass` | 玻璃工艺 | 彩绘玻璃、玻璃吹制、琉璃工艺 |
| `crafts_fiber` | 毛毡绳结 | 羊毛毡、绳结、绳编、纤维造型 |
| `crafts_mixed` | 综合手作 | 混合材料、拼贴、综合工艺；不作为普通未分类入口 |
| `crafts_other` | 其他手工艺 | 其他明确可识别的工艺形态 |

## 10. 艺术风格 `art_movements`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `art_movements_classical` | 古典学院 | 古典主义、学院派、巴洛克等通用视觉语言 |
| `art_movements_impressionism` | 印象表现 | 印象派、后印象派、表现主义等流派模板 |
| `art_movements_surrealism` | 超现实 | 梦境、超现实主义、现实错置的通用造型方法 |
| `art_movements_abstract` | 抽象构成 | 几何抽象、构成主义、色域与形式研究 |
| `art_movements_pop` | 波普欧普 | 波普、欧普、视觉错觉和大众图像语言 |
| `art_movements_art_nouveau` | 新艺术装饰 | 新艺术、装饰艺术及通用装饰语汇 |
| `art_movements_minimalism` | 极简主义 | 以极简视觉体系为核心、可跨题材套用的模板 |
| `art_movements_traditional` | 传统装饰 | 民族纹样、传统图案、地域装饰体系；不按人物国籍归类 |
| `art_movements_retro` | 年代复古 | 以某个年代的整体造型体系为目的的通用模板 |
| `art_movements_experimental` | 实验艺术 | 故障艺术、拼贴实验、跨媒介视觉实验 |
| `art_movements_other` | 其他艺术风格 | 其他可确定的艺术流派或视觉语言 |

年代复古只收录“复古风格本身”的模板。复古照片仍在摄影，复古广告仍在商业设计。

## 11. 通用模板 `general`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `general_composition` | 构图视角 | 可跨摄影、绘画等媒介使用的构图和视角模板 |
| `general_lighting` | 光影配色 | 不绑定具体媒介的光影、配色、氛围控制模板 |
| `general_editing` | 图片编辑 | 保留主体、替换背景、局部修改等通用编辑指令 |
| `general_consistency` | 一致性控制 | 主体、人物、构图等一致性任务模板 |
| `general_layout` | 多图编排 | 网格、对照、拼图、接触印样等通用编排任务 |
| `general_prompting` | 提示词模板 | 可填变量、提示词组织、参数化生成指令 |
| `general_other` | 其他通用 | 确认可跨媒介复用但不属于以上任务的模板 |

通用模板不是垃圾桶；没有明确通用任务的内容必须进待分类。

## 12. 待分类 `uncategorized`

| 子类 ID | 名称 | 收录范围与边界 |
|---|---|---|
| `uncategorized_pending` | 待人工判断 | 有可读内容，但归属尚未确定 |
| `uncategorized_incomplete` | 信息不足 | 标题、正文或上下文不足以判断 |
| `uncategorized_mixed` | 多任务待拆分 | 一条含多个独立生成任务，需判断是否拆条 |

待分类条目保留可见并单独统计。空正文、结构损坏、危险路径等属于校验失败，不通过“待分类”绕过导入校验。

### 12.1 各大类的待细分子类（v1.1 新增）

以下是正式保留子类，和现有内容子类并列。`pending` 表示证据不足或尚未细分；`other` 表示已经判断但不属于现有内容子类。不能为了让待处理数归零，把 pending 批量转为 other。

| 子类 ID | 名称 | 所属大类 |
|---|---|---|
| `photography_pending` | 待细分 | 摄影 |
| `anime_manga_pending` | 待细分 | 动漫 |
| `painting_pending` | 待细分 | 绘画插画 |
| `digital_3d_pending` | 待细分 | 数字 3D |
| `commercial_pending` | 待细分 | 商业设计 |
| `film_cinema_pending` | 待细分 | 电影叙事 |
| `crafts_pending` | 待细分 | 手工艺 |
| `art_movements_pending` | 待细分 | 艺术风格 |
| `general_pending` | 待细分 | 通用模板 |

全局待整理沿用 `uncategorized_pending`，不额外创建含义相同的大类。v1.1 共 10 个大类、111 个子类（原 102 个加 9 个待细分子类），既有 ID 不变。

## 13. 标签字典与使用建议

标签采用 `维度:值`，保存稳定英文值，界面显示中文映射。v1 建议每条 0–12 个，重复值去重；标签不参与主分类总数计算。

| 维度 | 示例值 | 中文含义与约束 |
|---|---|---|
| `medium` | `photo`, `watercolor`, `oil`, `ink`, `digital_painting`, `3d_render` | 媒介；可补充主分类未表达的表现手段 |
| `subject` | `person`, `animal`, `food`, `vehicle`, `building`, `object` | 主体；可多选，明确画面主体 |
| `look` | `realistic`, `stylized`, `chibi`, `minimal`, `surreal`, `pixel` | 表现特征 |
| `era` | `1920s`, `1950s`, `1980s`, `1990s`, `y2k` | 年代；不把复古作为所有内容的主分类 |
| `color` | `monochrome`, `pastel`, `warm`, `cool`, `high_contrast` | 色彩特征 |
| `lighting` | `natural`, `studio`, `backlight`, `neon`, `low_key` | 光照特征 |
| `shot` | `closeup`, `full_body`, `wide`, `macro`, `aerial`, `isometric` | 景别、视角与观察尺度 |
| `mood` | `calm`, `romantic`, `dramatic`, `dark`, `playful` | 情绪氛围 |
| `setting` | `indoor`, `outdoor`, `urban`, `nature`, `space` | 环境 |
| `purpose` | `advertising`, `editorial`, `avatar`, `wallpaper`, `concept` | 使用意图，不代替主分类 |

作品名、画师名、模型名和来源平台不塞入通用视觉标签；分别使用关联字段、模型建议和来源字段。新增词先登记再使用，不同时出现 `black-white`、`bw`、`monochrome` 三种同义值。

## 14. 旧分类迁移表

| 当前分类 | 目标处理 |
|---|---|
| `photography`、`anime_manga`、`painting`、`digital_3d`、`commercial`、`film_cinema`、`crafts`、`art_movements` | 保留大类 ID，逐条补标准子类；不能只按原大类批量猜测 |
| `retro` | 按实际任务迁至摄影、商业等；纯复古模板迁 `art_movements_retro`，补年代标签 |
| `misc` | 逐条整理至标准大类；通用任务进 `general`，不能确定的进 `uncategorized` |
| `fooocus_*` | 把原系列名保存为来源系列；仅按条目标题分类，不按 Fooocus 名称分组 |
| `yuanbao`、`yuanbao_*` | 来源保存为腾讯元宝；分类按具体内容重分，旧随机子类 ID 保留在迁移记录 |
| 临时 `photography-*` 展示分组 | 仅作为初步建议；复核后转为本表 `photography_*` ID，不能直接视为已审核 |

## 15. 分类审核与后续维护

1. 仅按标题批量分类，明确项归标准分类，大类明确项归该大类待细分，其余进全局待分类；不读取正文或图片补充判断。
2. 对跨类、低把握和缺少上下文的条目人工复核，不能虚构“已审核”。
3. 同一 ID 的重复条目采用同一分类；分类争议记录到审核表，不靠包加载顺序决定。
4. 每个正常大类允许一个 `other` 和一个 `pending`，分别表示已判定的其他内容与未解决项；标题明确分类抽样复核，发现问题再按歧义模式扩展检查。
5. 大量条目积累在同一个子类时，先检查是否分错，再考虑新增稳定子类；不为了均分数量硬拆。
6. 子类有新增需求时更新本表和分类版本，已发布 ID 不复用为其他含义。

建议首批重点审核“摄影”和“综合”，再整理来源型分类。当前包数量、声明条数和去重后实际条数是不同统计口径，迁移验收以条目 ID 和内容核对为准。
