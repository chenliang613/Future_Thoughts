"""生成"行业智能化第一性原理"信息图（v3 - 五条第一性原理）

内容与《行业智能化发展第一性原理.md》保持一致：
① 价值守恒  ② 行业知识密度  ③ 标杆-规模化路径  ④ 场景可批量复制  ⑤ 边际成本递减
共同支撑「倒金字塔」产业终局：应用层捕获 100 倍价值。
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'STHeiti', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(18, 10), dpi=150)
ax.set_xlim(0, 18)
ax.set_ylim(0, 10)
ax.axis('off')

# 配色
C_TITLE = '#1a2238'
C_GOAL = '#0B6E4F'
C_GOAL_BG = '#E1F0E8'
# 五条原理各自配色
COLORS = ['#2E86AB', '#A23B72', '#F18F01', '#3B8C6E', '#6A4C93']
BG = ['#E8F1F8', '#F5E6EE', '#FDF1DD', '#E4F0EA', '#ECE6F2']

# === 标题 ===
ax.text(9, 9.5, '行业智能化第一性原理', fontsize=30, fontweight='bold',
        ha='center', va='center', color=C_TITLE)
ax.text(9, 8.9, '剥离行业外壳后，任何智能化项目都绕不过的五条底层规律',
        fontsize=15, ha='center', va='center', color='#555', style='italic')

# === 五条原理卡片 ===
principles = [
    ('1', '价值守恒', '正 ROI 是底线',
     '被替代成本 + 新红利\n>\n推理 + 部署 + 变革成本'),
    ('2', '行业知识密度', '模型是地板·SOP 是天花板',
     '行业级智能体 =\n通用大模型 ×\n行业知识密度\n（本体论 / Skill / 语料）'),
    ('3', '标杆-规模化路径', '先打灯塔·再批量复制',
     'PoC（验可行）\n→ 灯塔（验 ROI）\n→ 规模复制（验产业化）'),
    ('4', '场景可批量复制', '标准化即规模化',
     '抽象成标准模板\n在行业中\n可重复落地'),
    ('5', '边际成本递减', '第 N 次部署趋近零',
     '1 次开发\n服务 1000 客户\n→ 应用层 ×100 价值'),
]

n = len(principles)
margin = 0.5
gap = 0.38
card_w = (18 - 2 * margin - (n - 1) * gap) / n   # ≈ 3.1
card_h = 4.7
card_y = 2.7

for i, (num, title, sub, body) in enumerate(principles):
    x = margin + i * (card_w + gap)
    color = COLORS[i]
    # 卡片
    card = FancyBboxPatch((x, card_y), card_w, card_h,
                          boxstyle="round,pad=0.04,rounding_size=0.13",
                          linewidth=2.2, edgecolor=color, facecolor=BG[i])
    ax.add_patch(card)
    # 顶部色条
    ax.add_patch(FancyBboxPatch((x, card_y + card_h - 0.12), card_w, 0.12,
                 boxstyle="round,pad=0.0,rounding_size=0.05",
                 linewidth=0, facecolor=color))
    # 编号圆
    cx, cy = x + 0.5, card_y + card_h - 0.6
    ax.add_patch(mpatches.Circle((cx, cy), 0.32, facecolor=color, edgecolor='none', zorder=3))
    ax.text(cx, cy, num, fontsize=16, fontweight='bold',
            ha='center', va='center', color='white', zorder=4)
    # 标题
    ax.text(x + card_w / 2 + 0.18, cy, title, fontsize=15, fontweight='bold',
            ha='center', va='center', color=color)
    # 副标题
    ax.text(x + card_w / 2, card_y + card_h - 1.25, sub, fontsize=11,
            ha='center', va='center', color='#333', fontweight='bold')
    # 正文公式块
    inner = FancyBboxPatch((x + 0.22, card_y + 0.4), card_w - 0.44, 2.55,
                           boxstyle="round,pad=0.04,rounding_size=0.1",
                           linewidth=1, edgecolor=color, facecolor='white')
    ax.add_patch(inner)
    ax.text(x + card_w / 2, card_y + 0.4 + 2.55 / 2, body, fontsize=10.5,
            ha='center', va='center', color='#222', linespacing=1.5)

# === 五条 → 终局的汇聚箭头 ===
for i in range(n):
    x = margin + i * (card_w + gap) + card_w / 2
    arr = FancyArrowPatch((x, card_y - 0.05), (9, 1.95),
                          arrowstyle='-|>', mutation_scale=14,
                          linewidth=1.1, color='#999', linestyle='--',
                          connectionstyle="arc3,rad=0.0")
    ax.add_patch(arr)

# === 底部产业终局条 ===
goal_box = FancyBboxPatch((2.0, 0.5), 14.0, 1.4,
                          boxstyle="round,pad=0.05,rounding_size=0.2",
                          linewidth=2.5, edgecolor=C_GOAL, facecolor=C_GOAL_BG)
ax.add_patch(goal_box)
ax.text(9, 1.42, '倒金字塔产业终局：应用层捕获 100 倍价值',
        fontsize=18, fontweight='bold', ha='center', va='center', color=C_GOAL)
ax.text(9, 0.85, '硬件 ×1     →     模型 ×10     →     行业应用 ×100',
        fontsize=13, ha='center', va='center', color='#444')

# === 署名 ===
ax.text(17.55, 0.12, '行业智能化发展第一性原理 · 2026',
        fontsize=9, ha='right', va='bottom', color='#999', style='italic')

plt.tight_layout()
output_path = '/Users/apple/Future_Thoughts/行业智能化第一性原理.jpg'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
print(f'已生成：{output_path}')
