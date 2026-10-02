#!/usr/bin/env python3
"""validate.py — taste-gate AI 内容生产计划七维校验器

输入: AI 内容生产计划 JSON（schema 见 tests/sample_good.json）
  {
    "project": {
      "name": "项目名",
      "reference_board": 4,                 // 风格参考板张数（3–5）
      "negative_list": ["不用饱和滤镜", "不做AI味运镜"],   // 负面清单（非空）
      "acceptance_sample_passed": true      // 已通过的验收样例
    },
    "consistency": {
      "character_cards": [
        {"name": "角色A", "traits": "性格关键词", "habit_actions": "习惯动作",
         "catchphrases": "口头禅", "turning_point": "第8幕从冷转暖"}   // 四要素必填
      ],
      "asset_library": [
        {"name": "服装A", "shot_scales": ["远","全","中","近","特"],
         "three_view": true, "in_library": true}   // 景别+三视图资产化
      ]
    },
    "volume": {
      "key_shot_min_candidates": 120,        // 关键镜头候选下限（≥100）
      "normal_shot_min_candidates": 20,      // 普通镜头候选下限（≥20）
      "enforced": true                       // 硬工序：没跑够不进下一环
    },
    "timebox": {
      "per_shot_minutes": 30,                // 每镜头时间盒（分钟，>0）
      "max_attempts": 20,                    // 次数上限（>0）
      "on_timeout": "改分镜或改景别"          // 到点动作（必须含"换方案"语义）
    },
    "assets": {
      "bet_on_workflow": false,              // 不押注两月保质期工作流
      "migratable_assets": ["设定卡","资产库","风格库","验收标准"]  // 非空
    },
    "investment": {
      "meme_hours_weekly": 6,                // 模因投入（拉片/阅片，>0）
      "tool_hours_weekly": 1                 // 工具学习时间（≤ 模因的 20%）
    },
    "roles": [
      {"title": "AI导演", "role_type": "decision", "taste_weight": 0.85, "knows_cinematography": true},
      {"title": "生成师", "role_type": "execution", "taste_weight": 0.30, "knows_cinematography": true}
    ]
  }

七维校验（任一 FAIL → exit 1）：
  D1 立项三件套: reference_board ∈ [3,5] 且 negative_list 非空 且
     acceptance_sample_passed=true（三缺一 = 品控无裁判依据）
  D2 一致性前移: character_cards 非空且每项四要素（traits/habit_actions/
     catchphrases/turning_point）全非空；asset_library 非空且每项景别覆盖
     远/全/中/近/特 中至少 3 种 且 three_view=true 且 in_library=true
  D3 数量下限: key_shot_min_candidates≥100 且 normal_shot_min_candidates≥20
     且 enforced=true（跑一两次就收工 = 没有比较就没有选择权）
  D4 时间盒强制: per_shot_minutes>0 且 max_attempts>0 且 on_timeout 含"换"
     语义（死磕=成本失控）
  D5 轻流程重资产: bet_on_workflow=false 且 migratable_assets 非空
     （押注两月保质期工作流 = 把会过期的当护城河）
  D6 能力投资方向: meme_hours_weekly>0 且 tool_hours_weekly ≤ 20%×meme
     （追工具教程超过模因投入两成 = 时间花在半衰期两个月的东西上）
  D7 审美权重显性化: roles 非空；decision 位 taste_weight≥0.7；
     execution 位 knows_cinematography=true（不懂镜头语言=废卡率高）；
     taste_weight 须为 (0,1] 数值

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

SCALES = {"远", "全", "中", "近", "特"}
CARD_FIELDS = ("traits", "habit_actions", "catchphrases", "turning_point")
ROLE_TYPES = {"decision", "execution"}


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def is_nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def validate(plan):
    checks = []

    # D1 立项三件套
    pr = plan.get("project") or {}
    rb = pr.get("reference_board")
    if not isinstance(rb, int) or not (3 <= rb <= 5):
        fail(checks, "D1", f"风格参考板 {rb!r}——须 3–5 张参考图/参考片，锚点强度不够")
    else:
        nl = pr.get("negative_list") or []
        if not any(is_nonempty_str(x) for x in nl):
            fail(checks, "D1", "负面清单为空——只说了要什么没说不要什么，品控无裁判依据")
        elif pr.get("acceptance_sample_passed") is not True:
            fail(checks, "D1", "验收样例未通过——标准本身没被验证，不许开工")
        else:
            ok(checks, "D1", f"立项三件套齐全（参考板 {rb} 张 + 负面清单 {len(nl)} 条 + 验收样例已通过）")

    # D2 一致性前移
    cons = plan.get("consistency") or {}
    cards = cons.get("character_cards") or []
    libs = cons.get("asset_library") or []
    bad_cards = []
    for c in cards:
        missing = [f for f in CARD_FIELDS if not is_nonempty_str(c.get(f))]
        if missing:
            bad_cards.append(f"{c.get('name', '?')}缺{list(missing)}")
    bad_libs = []
    for a in libs:
        scales = {s for s in (a.get("shot_scales") or []) if s in SCALES}
        if len(scales) < 3 or a.get("three_view") is not True or a.get("in_library") is not True:
            bad_libs.append(f"{a.get('name', '?')}(景别<{3}种/三视图/入库 未满足)")
    if not cards:
        fail(checks, "D2", "character_cards 为空——没有角色设定卡，一致性赌博留给量产")
    elif bad_cards:
        fail(checks, "D2", f"角色卡四要素不全: {bad_cards}——只锁脸不锁人物=纸片人")
    elif not libs or bad_libs:
        fail(checks, "D2", f"资产库不合规: {bad_libs if bad_libs else 'asset_library 为空'}——须按景别+三视图资产化")
    else:
        ok(checks, "D2", f"一致性前移（{len(cards)} 角色卡四要素齐全 + {len(libs)} 项资产入库）")

    # D3 数量下限
    vol = plan.get("volume") or {}
    key_min = vol.get("key_shot_min_candidates")
    norm_min = vol.get("normal_shot_min_candidates")
    if not isinstance(key_min, int) or key_min < 100:
        fail(checks, "D3", f"关键镜头候选下限 {key_min!r}——须 ≥100（1000选1 的最低比较量）")
    elif not isinstance(norm_min, int) or norm_min < 20:
        fail(checks, "D3", f"普通镜头候选下限 {norm_min!r}——须 ≥20（比较是质量的前提）")
    elif vol.get("enforced") is not True:
        fail(checks, "D3", "enforced=false——候选下限没写成硬工序，跑一两次就收工")
    else:
        ok(checks, "D3", f"数量下限硬工序（关键≥{key_min} / 普通≥{norm_min}，没跑够不进下一环）")

    # D4 时间盒强制
    tb = plan.get("timebox") or {}
    mins, att = tb.get("per_shot_minutes"), tb.get("max_attempts")
    if not isinstance(mins, (int, float)) or mins <= 0:
        fail(checks, "D4", f"per_shot_minutes={mins!r}——每镜头时间盒必须 >0，无限抽=成本失控")
    elif not isinstance(att, int) or att <= 0:
        fail(checks, "D4", f"max_attempts={att!r}——次数上限必须 >0")
    elif not is_nonempty_str(tb.get("on_timeout")) or "换" not in tb.get("on_timeout", ""):
        fail(checks, "D4", f"on_timeout={tb.get('on_timeout')!r}——到点必须换方案（改分镜/景别/叙事），死磕=成本失控")
    else:
        ok(checks, "D4", f"时间盒强制（{mins} 分钟/{att} 次上限，到点{tb['on_timeout']}）")

    # D5 轻流程重资产
    asr = plan.get("assets") or {}
    if asr.get("bet_on_workflow") is not False:
        fail(checks, "D5", "bet_on_workflow=true——押注两月保质期工作流，模型一更新就作废")
    else:
        ma = asr.get("migratable_assets") or []
        if not any(is_nonempty_str(x) for x in ma):
            fail(checks, "D5", "migratable_assets 为空——没有可迁移资产（设定卡/资产库/风格库/验收标准），工具换皮资产清零")
        else:
            ok(checks, "D5", f"轻流程重资产（{len(ma)} 类可迁移资产）")

    # D6 能力投资方向
    inv = plan.get("investment") or {}
    meme, tool = inv.get("meme_hours_weekly"), inv.get("tool_hours_weekly")
    if not isinstance(meme, (int, float)) or meme <= 0:
        fail(checks, "D6", f"meme_hours_weekly={meme!r}——模因投入（拉片/阅片/素材库）必须 >0，这是唯一不会过期的资产")
    elif not isinstance(tool, (int, float)) or tool < 0:
        fail(checks, "D6", f"tool_hours_weekly={tool!r}——非法值")
    elif tool > 0.2 * meme:
        fail(checks, "D6", f"工具学习 {tool}h > 模因 {meme}h 的 20%——时间花在半衰期两个月的东西上，应挪去攒模因")
    else:
        ok(checks, "D6", f"投资方向正确（模因 {meme}h/周，工具 {tool}h/周 ≤ 20%）")

    # D7 审美权重显性化
    roles = plan.get("roles") or []
    if not roles:
        fail(checks, "D7", "roles 为空——没声明岗位审美权重，'卖判断力还是卖产能'没答")
    else:
        bad_roles = []
        for r in roles:
            t = r.get("role_type")
            tw = r.get("taste_weight")
            if t not in ROLE_TYPES:
                bad_roles.append(f"{r.get('title', '?')}(role_type 非法)")
                continue
            if not isinstance(tw, (int, float)) or not (0 < tw <= 1):
                bad_roles.append(f"{r.get('title', '?')}(taste_weight 须 (0,1])")
                continue
            if t == "decision" and tw < 0.7:
                bad_roles.append(f"{r.get('title', '?')}(决策位审美权重 {tw} < 70%)")
            elif t == "execution" and r.get("knows_cinematography") is not True:
                bad_roles.append(f"{r.get('title', '?')}(执行位不懂镜头语言=废卡率高、成本控不住)")
        if bad_roles:
            fail(checks, "D7", "岗位审美权重: " + "；".join(bad_roles))
        else:
            ok(checks, "D7", f"{len(roles)} 个岗位审美权重显性化且合规")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
