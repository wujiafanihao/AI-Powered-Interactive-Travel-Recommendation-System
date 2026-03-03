# 用户推荐分析脚本使用说明

## 📋 脚本功能

### 1. `analyze_user_scores.py` - 批量分析所有用户
**功能**：分析数据库中所有用户的画像匹配评分指标

**使用方法**：
```bash
cd /Users/mac/Desktop/Project/Python/xianyu/1/backend
/opt/anaconda3/envs/workspace/bin/python3 scripts/analyze_user_scores.py
```

**输出内容**：
- 每个用户的详细信息（城市、偏好、推荐景点数）
- 匹配分范围（最高分、最低分、平均分）
- 不同分数段的景点数量（高分 60%+、中等 40-60%、低分<40%）
- 前 5 个推荐景点详情
- 总体统计（所有用户的分数分布）

---

### 2. `query_user_recommendations.py` - 单用户详细分析
**功能**：通过账号密码登录后查看某个用户的详细推荐结果

**使用方法**：
1. 编辑脚本，修改配置区域的账号密码：
```python
USERNAME = "test_admin"  # 用户名
PASSWORD = "123456"      # 密码
```

2. 运行脚本：
```bash
cd /Users/mac/Desktop/Project/Python/xianyu/1/backend
/opt/anaconda3/envs/workspace/bin/python3 scripts/query_user_recommendations.py
```

**输出内容**：
- 用户画像信息（昵称、城市、年龄、性别、旅行偏好）
- 混合推荐结果 Top15（包含景点名称、城市、类型、评分、匹配分、总分、推荐来源）
- 匹配分分布统计（平均分、最高分、最低分、各分数段数量）
- 推荐原因分析（画像匹配、行为偏好、内容相似、协同过滤的数量）
- 同城景点统计

---

## 🔧 如何获取真实用户账号

### 方法 1：查看数据库
```bash
cd /Users/mac/Desktop/Project/Python/xianyu/1/backend
sqlite3 data/travel.db "SELECT id, username, city FROM users WHERE id > 140;"
```

### 方法 2：使用 Python 查询
```bash
cd /Users/mac/Desktop/Project/Python/xianyu/1/backend
/opt/anaconda3/envs/workspace/bin/python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('data/travel.db')
cursor = conn.cursor()
cursor.execute("SELECT id, username, city FROM users WHERE id > 140 ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, 用户名：{row[1]}, 城市：{row[2]}")
conn.close()
EOF
```

### 已知测试用户
| 用户名 | 密码 | 城市 | 旅行偏好 |
|--------|------|------|----------|
| test_admin | 123456 | 北京 | 自然风光，历史文化 |
| 13510496170 | (需要查看注册时的密码) | 南京 | 历史文化，美食，摄影 |
| testuser1 | (需要查看注册时的密码) | 南京 | 自然风光 |

---

## 📊 输出示例

### analyze_user_scores.py 输出示例
```
👤 用户：13510496170 (ID: 154)
   城市：南京
   旅行偏好：["历史文化", "美食", "摄影"]
   推荐景点数：100
   匹配分范围：40.0% - 70.0%
   平均匹配分：57.2%
   高分景点 (60%+): 64 个
   中等景点 (40-60%): 36 个
   低分景点 (<40%): 0 个
   前 5 个推荐景点:
      1. 牛首山文化旅游区 (南京) - 70.0%
      2. 夫子庙 (南京) - 70.0%
      3. 侵华日军南京大屠杀遇难同胞纪念馆 (南京) - 70.0%
```

### query_user_recommendations.py 输出示例
```
========================================================================================================================
🎯 混合推荐结果 Top15:
========================================================================================================================
序号   名字                                  城市           类型                   评分     匹配分      总分         来源      
------------------------------------------------------------------------------------------------------------------------
1    中国航空博物馆                         北京           自然风光                 4.4      50.0%    0.4300     profile  🏠
2    故宫博物院                             北京           历史文化                 4.0      65.0%    0.5200     hybrid 🏠
...

📊 匹配分分布统计:
   平均匹配分：55.3%
   最高分：70.0%
   最低分：30.0%
   🟢 高分景点 (60%+): 8 个 (53.3%)
   🟡 中等景点 (40-60%): 6 个 (40.0%)
   🔴 低分景点 (<40%): 1 个 (6.7%)

💡 推荐原因分析:
   • 画像匹配：10 个景点
   • 行为偏好：3 个景点
   • 协同过滤：2 个景点

🏠 同城景点：12/15 (80.0%)
```

---

## 🎯 使用场景

1. **算法调试**：查看推荐算法是否正常工作，匹配分是否合理
2. **用户分析**：了解特定用户的推荐结果和匹配原因
3. **数据验证**：验证画像数据是否正确影响推荐结果
4. **毕业报告**：生成推荐系统的效果数据和统计图表

---

## ⚠️ 注意事项

1. 脚本需要使用项目的 Python 环境（`/opt/anaconda3/envs/workspace/bin/python3`）
2. 确保数据库文件存在：`backend/data/travel.db`
3. 推荐引擎首次运行需要加载模型，可能需要几秒钟
4. 如需分析大量用户，建议使用 `analyze_user_scores.py` 批量分析
