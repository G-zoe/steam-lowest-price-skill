# steam-lowest-price-skill

Steam 游戏折扣/史低监控技能（OpenClaw）。

## 现在这版已修复的关键点

- ✅ **价格源改为 Steam 官方国区接口**（`store.steampowered.com/api/appdetails`）
- ✅ 价格以 **人民币（CNY）** 计算与展示
- ✅ 触发规则支持：
  - 关注游戏**只要在打折就触发**
  - 或达到你设置的目标价（`target`）触发
- ✅ 提醒内容包含：
  - 当前价
  - 原价
  - 史低价（已观测）
  - 差价
  - 折扣
  - Steam 商店链接

> 说明：`史低价`目前是该技能运行以来对该游戏的**已观测最低价**。

---

## 功能列表

1. 添加监控游戏（按游戏名搜索）
2. 删除监控游戏（按 AppID）
3. 列出监控列表
4. 执行价格检查并输出触发项
5. 支持目标价（人民币）

---

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

---

## 使用方式

### 1) 添加关注

```bash
python3 scripts/steam_watch.py add --query "The Riftbreaker"
```

带目标价（人民币）：

```bash
python3 scripts/steam_watch.py add --query "Battlefield V" --target 29.9
```

### 2) 查看关注列表

```bash
python3 scripts/steam_watch.py list
```

### 3) 删除关注

```bash
python3 scripts/steam_watch.py remove --appid 1238810
```

### 4) 执行检查（手动）

```bash
python3 scripts/steam_watch.py check
```

如果命中，会输出类似：

```text
🎮 Battlefield V
当前价: ¥11.40
原价: ¥228.00
史低价: ¥11.40
差价: ¥0.00
折扣: 95%
链接: https://store.steampowered.com/app/1238810/
```

---

## OpenClaw 定时推送示例

每 6 小时检查并推送：

```bash
openclaw cron add \
  --name "steam-price-monitor" \
  --every "6h" \
  --session isolated \
  --announce \
  --channel qqbot \
  --to "qqbot:c2c:<YOUR_OPENID>" \
  --message "运行 python3 /path/to/steam-lowest-price-skill/scripts/steam_watch.py check 。如果有打折游戏，原样输出并推送；无触发则回复本轮无触发。"
```

---

## 数据文件

- `data/watchlist.json`：关注列表
- `data/state.json`：运行状态与已观测低价

已在 `.gitignore` 忽略这些本地状态文件。