"""生成"行业智能化第一性原理"信息图（v2 - 标杆 → 标准化 → 规模复制）"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'STHeiti', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(18, 11.5), dpi=150)
ax.set_xlim(0, 18)
ax.set_ylim(0, 11.5)
ax.axis('off')

# 配色
C_TITLE = '#1a2238'
C_S1 = '#2E86AB'      # 树立标杆 - 深蓝
C_S2 = '#A23B72'      # 标准化场景 - 紫红
C_S3 = '#F18F01'      # 规模复制 - 橙
C_BG1 = '#E8F1F8'
C_BG2 = '#F5E6EE'
C_BG3 = '#FDF1DD'
C_AXIS = '#5C6B7A'    # 主轴灰
C_AXIS_BG = '#EEF1F5'
C_GOAL = '#0B6E4F'
C_GOAL_BG = '#E1F0E8'

# === 标题 ===
ax.text(9, 10.95, '行业智能化第一性原理', fontsize=28, fontweight='bold',
        ha='center', va='center', color=C_TITLE)
ax.text(9, 10.4, '先树立标杆  →  再标准化场景  →  最后规模复制',
        fontsize=15, ha='center', va='center', color='#555', style='italic')

# === 三阶段大容器 ===
def stage_box(x, y, w, h, color_bg, color_edge):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.2",
                         linewidth=2.5, edgecolor=color_edge, facecolor=color_bg, alpha=0.95)
    ax.add_patch(box)

stage_box(0.4, 3.4, 6.0, 6.4, C_BG1, C_S1)
stage_box(6.7, 3.4, 4.6, 6.4, C_BG2, C_S2)
stage_box(11.6, 3.4, 5.95, 6.4, C_BG3, C_S3)

# 阶段标题
ax.text(3.4, 9.35, '① 先树立标杆', fontsize=20, fontweight='bold', ha='center', color=C_S1)
ax.text(3.4, 8.85, '跑通单点 · 打造灯塔', fontsize=12, ha='center', color='#444')

ax.text(9.0, 9.35, '② 再标准化场景', fontsize=20, fontweight='bold', ha='center', color=C_S2)
ax.text(9.0, 8.85, '抽象模板 · 打开复制空间', fontsize=12, ha='center', color='#444')

ax.text(14.575, 9.35, '③ 最后规模复制', fontsize=20, fontweight='bold', ha='center', color=C_S3)
ax.text(14.575, 8.85, '边际归零 · 释放规模红利', fontsize=12, ha='center', color='#444')

# === 原理卡片 ===
def principle_card(x, y, w, h, num, title, subtitle, color):
    card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.13",
                          linewidth=1.8, edgecolor=color, facecolor='white')
    ax.add_patch(card)
    circle = mpatches.Circle((x + 0.45, y + h - 0.42), 0.30, facecolor=color, edgecolor='none', zorder=3)
    ax.add_patch(circle)
    ax.text(x + 0.45, y + h - 0.42, num, fontsize=14, fontweight='bold',
            ha='center', va='center', color='white', zorder=4)
    ax.text(x + w/2 + 0.18, y + h - 0.42, title, fontsize=13, fontweight='bold',
            ha='center', va='center', color=color)
    ax.text(x + w/2, y + 0.4, subtitle, fontsize=10.5, ha='center', va='center', color='#333')

# 阶段一：3 个原理
principle_card(0.75, 7.0, 5.3, 1.25, '1', '价值守恒', '正 ROI 是底线', C_S1)
principle_card(0.75, 5.55, 5.3, 1.25, '2', '数据流喂养', '数据是燃料 · 实时可调度', C_S1)
principle_card(0.75, 4.10, 5.3, 1.25, '3', '行业知识密度', 'Skill / SOP 是灵魂', C_S1)

# 阶段二：1 个原理（卡片做大、居中）
principle_card(7.0, 5.6, 4.0, 1.7, '4', '场景可批量复制',
               '标准化即规模化\n抽象成模板\n跨企业可重复落地', C_S2)

# 阶段三：1 个原理
principle_card(11.95, 5.6, 5.25, 1.7, '5', '边际成本递减',
               '第 N 次部署趋近零成本\nSkill 复用率 > 70%\n释放产业级规模红利', C_S3)

# === 阶段输出（每个阶段底部的产出标签）===
def output_tag(x, y, w, text, color):
    tag = FancyBboxPatch((x, y), w, 0.55, boxstyle="round,pad=0.02,rounding_size=0.1",
                         linewidth=1.5, edgecolor=color, facecolor='white')
    ax.add_patch(tag)
    ax.text(x + w/2, y + 0.275, text, fontsize=11, fontweight='bold',
            ha='center', va='center', color=color)

output_tag(1.2, 3.65, 4.4, '产出：灯塔标杆项目', C_S1)
output_tag(7.2, 3.65, 3.6, '产出：标准模板 / Skill 库', C_S2)
output_tag(12.3, 3.65, 4.55, '产出：规模化复制曲线', C_S3)

# === 阶段间箭头 ===
def stage_arrow(x1, x2, y, color):
    arrow = FancyArrowPatch((x1, y), (x2, y),
                            arrowstyle='-|>', mutation_scale=30,
                            linewidth=4, color=color)
    ax.add_patch(arrow)

stage_arrow(6.35, 6.75, 6.3, '#888')
stage_arrow(11.25, 11.65, 6.3, '#888')

# === 贯穿三阶段的主轴：原理 6 ===
axis_box = FancyBboxPatch((0.4, 1.95), 17.15, 1.05,
                          boxstyle="round,pad=0.04,rounding_size=0.18",
                          linewidth=2, edgecolor=C_AXIS, facecolor=C_AXIS_BG)
ax.add_patch(axis_box)

# 原理6 编号圆
circle6 = mpatches.Circle((1.0, 2.475), 0.34, facecolor=C_AXIS, edgecolor='none', zorder=3)
ax.add_patch(circle6)
ax.text(1.0, 2.475, '6', fontsize=15, fontweight='bold',
        ha='center', va='center', color='white', zorder=4)

ax.text(1.55, 2.78, '原理 6 · 标杆-规模化路径（贯穿主轴）',
        fontsize=13, fontweight='bold', va='center', color=C_AXIS)
ax.text(1.55, 2.20, 'PoC（验证可行性） →  灯塔（验证 ROI） →  同心圆复制 →  产业化规模',
        fontsize=11.5, va='center', color='#333')

# 三个阶段到主轴的虚线
for sx in [3.4, 9.0, 14.575]:
    arr = FancyArrowPatch((sx, 3.4), (sx, 3.05),
                          arrowstyle='-|>', mutation_scale=16,
                          linewidth=1.3, color='#888', linestyle='--')
    ax.add_patch(arr)

# === 底部产业终局条 ===
goal_box = FancyBboxPatch((0.4, 0.45), 17.15, 1.2,
                          boxstyle="round,pad=0.05,rounding_size=0.2",
                          linewidth=2.5, edgecolor=C_GOAL, facecolor=C_GOAL_BG)
ax.add_patch(goal_box)
ax.text(9, 1.30, '倒金字塔产业终局：应用层捕获 100 倍价值',
        fontsize=17, fontweight='bold', ha='center', va='center', color=C_GOAL)
ax.text(9, 0.75, '硬件 ×1   →   模型 ×10   →   行业应用 ×100',
        fontsize=12, ha='center', va='center', color='#444')

# 主轴指向产业终局
arr_main = FancyArrowPatch((9, 1.95), (9, 1.65),
                           arrowstyle='-|>', mutation_scale=20,
                           linewidth=1.8, color=C_AXIS)
ax.add_patch(arr_main)

# === 右下角署名 ===
ax.text(17.55, 0.12, '行业智能化项目方法论 · 2026',
        fontsize=8.5, ha='right', va='bottom', color='#999', style='italic')

plt.tight_layout()
output_path = '/Users/apple/Future_Thoughts/行业智能化第一性原理.jpg'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
print(f'已生成：{output_path}')
