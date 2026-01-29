# -*- coding: utf-8 -*-
"""
《功德轮回：众生百态》v4.7 打印制作包生成器
生成A4纸张PDF，可直接打印剪裁
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Frame, FrameBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import os

# 尝试注册中文字体
try:
    # Windows 系统字体路径
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
    ]
    font_registered = False
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', fp))
                font_registered = True
                break
            except:
                continue
    if not font_registered:
        print("警告: 未找到中文字体，使用默认字体")
        FONT_NAME = 'Helvetica'
    else:
        FONT_NAME = 'ChineseFont'
except Exception as e:
    print(f"字体注册错误: {e}")
    FONT_NAME = 'Helvetica'

# 页面设置
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm

# 卡牌尺寸（标准扑克牌尺寸 63x88mm）
CARD_WIDTH = 63 * mm
CARD_HEIGHT = 88 * mm
CARD_MARGIN = 3 * mm

# 每页卡牌数量
CARDS_PER_ROW = 3
CARDS_PER_COL = 3

def create_styles():
    """创建文字样式"""
    styles = {}
    
    styles['title'] = ParagraphStyle(
        'Title',
        fontName=FONT_NAME,
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    
    styles['subtitle'] = ParagraphStyle(
        'Subtitle',
        fontName=FONT_NAME,
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    
    styles['heading'] = ParagraphStyle(
        'Heading',
        fontName=FONT_NAME,
        fontSize=14,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=8,
        spaceBefore=12,
    )
    
    styles['body'] = ParagraphStyle(
        'Body',
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    
    styles['small'] = ParagraphStyle(
        'Small',
        fontName=FONT_NAME,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )
    
    styles['card_title'] = ParagraphStyle(
        'CardTitle',
        fontName=FONT_NAME,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    
    styles['card_body'] = ParagraphStyle(
        'CardBody',
        fontName=FONT_NAME,
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )
    
    return styles

class GamePrintPack:
    def __init__(self, filename="功德轮回_v4.7_打印包.pdf"):
        self.filename = filename
        self.styles = create_styles()
        
    def draw_card_border(self, c, x, y, width, height, title="", bg_color=colors.white):
        """绘制卡牌边框"""
        # 背景
        c.setFillColor(bg_color)
        c.rect(x, y, width, height, fill=1, stroke=0)
        
        # 边框
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height, fill=0, stroke=1)
        
        # 内边框
        c.setLineWidth(0.5)
        c.rect(x + 2*mm, y + 2*mm, width - 4*mm, height - 4*mm, fill=0, stroke=1)
        
    def draw_text_in_card(self, c, x, y, width, height, lines, title_size=11, body_size=8):
        """在卡牌内绘制文字"""
        c.setFont(FONT_NAME, title_size)
        current_y = y + height - 8*mm
        
        for i, line in enumerate(lines):
            if i == 0:  # 标题
                c.setFont(FONT_NAME, title_size)
                c.drawCentredString(x + width/2, current_y, line)
                current_y -= title_size + 4
            else:  # 正文
                c.setFont(FONT_NAME, body_size)
                # 自动换行
                text = line
                max_chars = int((width - 8*mm) / (body_size * 0.6))
                while len(text) > 0:
                    display = text[:max_chars]
                    text = text[max_chars:]
                    c.drawString(x + 4*mm, current_y, display)
                    current_y -= body_size + 2
                current_y -= 2
    
    def generate(self):
        """生成完整PDF"""
        c = canvas.Canvas(self.filename, pagesize=A4)
        
        # 封面
        self.draw_cover(c)
        c.showPage()
        
        # 目录
        self.draw_toc(c)
        c.showPage()
        
        # 规则摘要
        self.draw_rules_summary(c)
        c.showPage()
        
        # 角色板 (4张)
        self.draw_role_boards(c)
        
        # 发愿卡 (8张)
        self.draw_vow_cards(c)
        
        # 菩萨行愿卡 (4张)
        self.draw_bodhisattva_cards(c)
        
        # 集体事件卡 (12张)
        self.draw_collective_event_cards(c)
        
        # 个人事件卡 (32张)
        self.draw_personal_event_cards(c)
        
        # 众生卡 (10张)
        self.draw_being_cards(c)
        
        # 行动提示卡 (4张)
        self.draw_action_cards(c)
        
        # A/B选择卡 (4套=8张)
        self.draw_ab_cards(c)
        
        # 轨道和标记
        self.draw_tracks(c)
        
        # 资源标记
        self.draw_resource_tokens(c)
        
        c.save()
        print(f"PDF已生成: {self.filename}")
    
    def draw_cover(self, c):
        """绘制封面"""
        c.setFont(FONT_NAME, 36)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 100*mm, "功德轮回")
        
        c.setFont(FONT_NAME, 24)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 120*mm, "众生百态")
        
        c.setFont(FONT_NAME, 14)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 145*mm, "v4.7 精简版（最终平衡版）")
        
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 170*mm, "打印制作包")
        
        c.setFont(FONT_NAME, 10)
        info = [
            "游戏人数：2-4人",
            "游戏时长：30-45分钟",
            "游戏类型：半合作策略",
            "",
            "包含内容：",
            "- 角色板 4张",
            "- 发愿卡 8张 + 菩萨行愿卡 4张",
            "- 集体事件卡 12张",
            "- 个人事件卡 32张",
            "- 众生卡 10张",
            "- 行动提示卡 4张",
            "- A/B选择卡 8张",
            "- 轨道板 1张",
            "- 资源标记（需自备或剪裁）",
            "",
            "打印说明：",
            "- A4纸张，单面打印",
            "- 卡牌页建议使用较厚纸张（200g以上）",
            "- 沿虚线剪裁",
        ]
        
        y = PAGE_HEIGHT - 200*mm
        for line in info:
            c.drawCentredString(PAGE_WIDTH/2, y, line)
            y -= 14
    
    def draw_toc(self, c):
        """绘制目录"""
        c.setFont(FONT_NAME, 20)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 40*mm, "目录")
        
        c.setFont(FONT_NAME, 12)
        items = [
            ("1. 规则摘要", "第3页"),
            ("2. 角色板（4张）", "第4-5页"),
            ("3. 发愿卡（8张）", "第6-7页"),
            ("4. 菩萨行愿卡（4张）", "第8页"),
            ("5. 集体事件卡（12张）", "第9-11页"),
            ("6. 个人事件卡（32张）", "第12-19页"),
            ("7. 众生卡（10张）", "第20-21页"),
            ("8. 行动提示卡（4张）", "第22页"),
            ("9. A/B选择卡（8张）", "第23页"),
            ("10. 轨道板", "第24页"),
            ("11. 资源标记", "第25页"),
        ]
        
        y = PAGE_HEIGHT - 70*mm
        for name, page in items:
            c.drawString(50*mm, y, name)
            c.drawRightString(PAGE_WIDTH - 50*mm, y, page)
            y -= 16
    
    def draw_rules_summary(self, c):
        """绘制规则摘要"""
        c.setFont(FONT_NAME, 18)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 30*mm, "规则摘要")
        
        c.setFont(FONT_NAME, 10)
        
        rules = [
            "【游戏目标】",
            "团队胜利：劫难≤12 且 渡化众生≥5",
            "个人胜利：团队胜利后，福+慧最高者获胜",
            "",
            "【回合流程】（共6回合）",
            "0. 发愿奖励阶段 - 获得发愿卡的每回合奖励",
            "1. 集体事件阶段 - 翻1张集体事件卡",
            "2. 个人事件阶段 - 奇数回合每人抽1张",
            "3. 众生阶段 - 超时众生消失，新众生出现",
            "4. 行动阶段 - 每人执行2个行动",
            "5. 结算阶段 - 偶数回合扣1财富或1福",
            "",
            "【可用行动】",
            "劳作：+3财富（农夫+4，不皈依者再+1）",
            "修行：+2慧（学者+4）",
            "布施：-2财富，+2福（商人+4福），劫难-1",
            "渡化：需慧≥5，支付众生卡的财富成本",
            "护法：-2财富，+1福，劫难-2",
            "",
            "【v4.7平衡配置】",
            "农夫：财5福2慧2，劳作+1，发愿每回合+1福",
            "商人：财9福2慧1，布施+2福",
            "学者：财4福2慧5，修行+2慧",
            "僧侣：财1福5慧5，可用福代财",
            "",
            "【发愿条件】",
            "勤劳致福：福≥24（+12分）",
            "贫女一灯：福≥30且财≤5（+18分）",
            "阿罗汉果：慧≥14（+12分）",
        ]
        
        y = PAGE_HEIGHT - 50*mm
        for line in rules:
            if line.startswith("【"):
                c.setFont(FONT_NAME, 11)
                y -= 4
            else:
                c.setFont(FONT_NAME, 9)
            c.drawString(25*mm, y, line)
            y -= 12
    
    def draw_role_boards(self, c):
        """绘制角色板（大尺寸，2张/页）"""
        roles = [
            {
                "name": "农夫",
                "quote": "耕读传家，勤劳致福",
                "init": "财富5 | 福2 | 慧2",
                "passive": "【被动·勤劳致富】劳作时+1财富（共+4）",
                "active": "【主动·分享收成】每局2次\n给1名玩家2财富，双方各+1福",
                "color": colors.Color(0.9, 0.95, 0.8),  # 浅绿
            },
            {
                "name": "商人",
                "quote": "千金散尽还复来",
                "init": "财富9 | 福2 | 慧1",
                "passive": "【被动·广结善缘】布施时+2福（共+4）\n首次渡化后+2财富",
                "active": "【主动·慷慨宴请】每局2次\n-3财富，全体+1福，劫难-1",
                "color": colors.Color(1.0, 0.95, 0.8),  # 浅金
            },
            {
                "name": "学者",
                "quote": "学而不厌，诲人不倦",
                "init": "财富4 | 福2 | 慧5",
                "passive": "【被动·博学多闻】修行时+2慧（共+4）\n个人事件可弃掉重抽1次/局",
                "active": "【主动·讲学传道】每局2次\n选2人各+1慧，自己+1福",
                "color": colors.Color(0.85, 0.9, 1.0),  # 浅蓝
            },
            {
                "name": "僧侣",
                "quote": "万法皆空，慈悲度世",
                "init": "财富1 | 福5 | 慧5",
                "passive": "【被动·化缘度日】渡化时可用福代财（每次≤2）\n渡化成本-1",
                "active": "【主动·加持祈福】每局2次\n给1人转移≤2福，对方额外+1福",
                "color": colors.Color(1.0, 0.9, 0.85),  # 浅橙
            },
        ]
        
        board_width = 85 * mm
        board_height = 120 * mm
        
        for i, role in enumerate(roles):
            if i % 2 == 0:
                c.showPage()
                c.setFont(FONT_NAME, 12)
                c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, f"角色板 ({i+1}-{min(i+2, 4)}/4) - 沿边框剪裁")
            
            # 计算位置
            col = i % 2
            x = MARGIN + col * (board_width + 10*mm)
            y = PAGE_HEIGHT - 35*mm - board_height
            
            # 绘制角色板
            c.setFillColor(role["color"])
            c.rect(x, y, board_width, board_height, fill=1, stroke=0)
            c.setStrokeColor(colors.black)
            c.setLineWidth(2)
            c.rect(x, y, board_width, board_height, fill=0, stroke=1)
            
            # 标题
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 18)
            c.drawCentredString(x + board_width/2, y + board_height - 15*mm, role["name"])
            
            # 引言
            c.setFont(FONT_NAME, 9)
            c.drawCentredString(x + board_width/2, y + board_height - 25*mm, f"「{role['quote']}」")
            
            # 分隔线
            c.setLineWidth(1)
            c.line(x + 5*mm, y + board_height - 30*mm, x + board_width - 5*mm, y + board_height - 30*mm)
            
            # 初始资源
            c.setFont(FONT_NAME, 11)
            c.drawCentredString(x + board_width/2, y + board_height - 40*mm, role["init"])
            
            # 被动技能
            c.setFont(FONT_NAME, 9)
            passive_lines = role["passive"].split("\n")
            py = y + board_height - 55*mm
            for pl in passive_lines:
                c.drawString(x + 5*mm, py, pl)
                py -= 12
            
            # 主动技能
            c.setFont(FONT_NAME, 9)
            active_lines = role["active"].split("\n")
            ay = py - 8
            for al in active_lines:
                c.drawString(x + 5*mm, ay, al)
                ay -= 12
            
            # 资源放置区
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.grey)
            
            # 财富区
            c.rect(x + 5*mm, y + 5*mm, 25*mm, 25*mm, fill=0, stroke=1)
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + 17.5*mm, y + 32*mm, "财富")
            
            # 福区
            c.rect(x + 32*mm, y + 5*mm, 25*mm, 25*mm, fill=0, stroke=1)
            c.drawCentredString(x + 44.5*mm, y + 32*mm, "福")
            
            # 慧区
            c.rect(x + 59*mm, y + 5*mm, 25*mm, 25*mm, fill=0, stroke=1)
            c.drawCentredString(x + 71.5*mm, y + 32*mm, "慧")
    
    def draw_vow_cards(self, c):
        """绘制发愿卡"""
        vows = [
            # 农夫
            {"name": "勤劳致福", "role": "农夫", "type": "简单",
             "effect": "每回合：福+1",
             "condition": "结束时福≥24",
             "reward": "+12分", "penalty": "-4分"},
            {"name": "贫女一灯", "role": "农夫", "type": "困难",
             "effect": "每回合：福+1",
             "condition": "结束时福≥30\n且财富≤5",
             "reward": "+18分", "penalty": "-6分"},
            # 商人
            {"name": "财施功德", "role": "商人", "type": "简单",
             "effect": "每回合：财富+1",
             "condition": "本局布施≥3次",
             "reward": "+12分", "penalty": "-4分"},
            {"name": "大商人之心", "role": "商人", "type": "困难",
             "effect": "每回合：慧+1",
             "condition": "结束时福≥16\n且渡化≥2次",
             "reward": "+16分", "penalty": "-6分"},
            # 学者
            {"name": "传道授业", "role": "学者", "type": "简单",
             "effect": "每回合：慧+1",
             "condition": "结束时慧≥16",
             "reward": "+12分", "penalty": "-4分"},
            {"name": "万世师表", "role": "学者", "type": "困难",
             "effect": "每回合：慧+1",
             "condition": "结束时福≥12\n且慧≥18",
             "reward": "+16分", "penalty": "-6分"},
            # 僧侣
            {"name": "阿罗汉果", "role": "僧侣", "type": "简单",
             "effect": "每回合：慧+1",
             "condition": "结束时慧≥14",
             "reward": "+12分", "penalty": "-4分"},
            {"name": "菩萨道", "role": "僧侣", "type": "困难",
             "effect": "每回合：福+1",
             "condition": "结束时福≥16\n且渡化≥3次",
             "reward": "+18分", "penalty": "-8分"},
        ]
        
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "发愿卡 (1-6/8) - 沿边框剪裁")
        
        for i, vow in enumerate(vows):
            if i == 6:  # 第7张开始新页
                c.showPage()
                c.setFont(FONT_NAME, 12)
                c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "发愿卡 (7-8/8) - 沿边框剪裁")
            
            row = (i % 6) // 3
            col = (i % 6) % 3
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (CARD_HEIGHT + CARD_MARGIN)
            
            # 背景色
            if vow["type"] == "简单":
                bg = colors.Color(0.95, 1.0, 0.95)  # 浅绿
            else:
                bg = colors.Color(1.0, 0.95, 0.9)  # 浅橙
            
            self.draw_card_border(c, x, y, CARD_WIDTH, CARD_HEIGHT, bg_color=bg)
            
            # 内容
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 10*mm, vow["name"])
            
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 18*mm, f"【{vow['role']}·{vow['type']}】")
            
            c.setFont(FONT_NAME, 8)
            c.drawString(x + 4*mm, y + CARD_HEIGHT - 30*mm, f"每回合效果：")
            c.drawString(x + 4*mm, y + CARD_HEIGHT - 38*mm, vow["effect"])
            
            c.drawString(x + 4*mm, y + CARD_HEIGHT - 50*mm, f"达成条件：")
            cond_lines = vow["condition"].split("\n")
            cy = y + CARD_HEIGHT - 58*mm
            for cl in cond_lines:
                c.drawString(x + 4*mm, cy, cl)
                cy -= 10
            
            c.setFont(FONT_NAME, 9)
            c.drawString(x + 4*mm, y + 12*mm, f"成功：{vow['reward']}")
            c.drawString(x + 4*mm, y + 4*mm, f"失败：{vow['penalty']}")
    
    def draw_bodhisattva_cards(self, c):
        """绘制菩萨行愿卡"""
        cards = [
            {"name": "地藏愿", 
             "quote": "地狱不空，誓不成佛",
             "effect": "基础分-10\n团队胜利时+15分",
             "condition": "团队获胜"},
            {"name": "观音愿",
             "quote": "千处祈求千处应",
             "effect": "布施改为：\n给他人2财富，自己+2福",
             "condition": "帮助≥3名不同玩家"},
            {"name": "普贤愿",
             "quote": "礼敬诸佛，广修供养",
             "effect": "每回合结束：\n1财富放入众生区",
             "condition": "累计供养≥5财富"},
            {"name": "文殊愿",
             "quote": "以智慧剑斩烦恼",
             "effect": "修行时-1慧\n（基础收益）",
             "condition": "2名以上玩家慧≥15"},
        ]
        
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "菩萨行愿卡 (4张) - 大乘发心者专用 - 沿边框剪裁")
        
        for i, card in enumerate(cards):
            row = i // 3
            col = i % 3
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (CARD_HEIGHT + CARD_MARGIN)
            
            bg = colors.Color(1.0, 0.95, 1.0)  # 浅紫
            self.draw_card_border(c, x, y, CARD_WIDTH, CARD_HEIGHT, bg_color=bg)
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 11)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 10*mm, card["name"])
            
            c.setFont(FONT_NAME, 7)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 18*mm, f"「{card['quote']}」")
            
            c.setFont(FONT_NAME, 8)
            c.drawString(x + 4*mm, y + CARD_HEIGHT - 30*mm, "持续效果：")
            eff_lines = card["effect"].split("\n")
            ey = y + CARD_HEIGHT - 38*mm
            for el in eff_lines:
                c.drawString(x + 4*mm, ey, el)
                ey -= 10
            
            c.drawString(x + 4*mm, y + 12*mm, "达成条件：")
            c.drawString(x + 4*mm, y + 4*mm, card["condition"])
    
    def draw_collective_event_cards(self, c):
        """绘制集体事件卡"""
        events = [
            # 天灾共业 (4张) - 红色
            {"name": "旱魃肆虐", "type": "天灾", "color": colors.Color(1.0, 0.9, 0.9),
             "effect": "劫难+4\n每人选择：\nA:财-2，福+1\nB:财-1",
             "note": "全A:劫难-2全体+1福"},
            {"name": "洪水滔天", "type": "天灾", "color": colors.Color(1.0, 0.9, 0.9),
             "effect": "劫难+4\n每人选择：\nA:财-2，福+1\nB:财-1",
             "note": "全B:劫难+3"},
            {"name": "瘟疫流行", "type": "天灾", "color": colors.Color(1.0, 0.9, 0.9),
             "effect": "劫难+4\n每人选择：\nA:财-2，福+1\nB:财-1",
             "note": "使用A/B卡同时揭示"},
            {"name": "蝗灾蔽日", "type": "天灾", "color": colors.Color(1.0, 0.9, 0.9),
             "effect": "劫难+4\n每人选择：\nA:财-2，福+1\nB:财-1",
             "note": "合作者越多劫难越少"},
            # 人祸共业 (2张) - 橙色
            {"name": "苛政如虎", "type": "人祸", "color": colors.Color(1.0, 0.95, 0.85),
             "effect": "劫难+3\n所有人财富-1",
             "note": ""},
            {"name": "战火将至", "type": "人祸", "color": colors.Color(1.0, 0.95, 0.85),
             "effect": "劫难+3\n所有人财富-1",
             "note": ""},
            # 共同福报 (6张) - 绿色
            {"name": "风调雨顺", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "所有人财富+1",
             "note": ""},
            {"name": "国泰民安", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "劫难-2",
             "note": ""},
            {"name": "浴佛盛会", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "所有人福+1\n皈依者额外+1福",
             "note": ""},
            {"name": "盂兰盆节", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "所有人福+1",
             "note": ""},
            {"name": "高僧讲经", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "所有人慧+1\n皈依者额外+1慧",
             "note": ""},
            {"name": "舍利现世", "type": "福报", "color": colors.Color(0.9, 1.0, 0.9),
             "effect": "劫难-1\n所有人福+1",
             "note": ""},
        ]
        
        page_num = 0
        for i, event in enumerate(events):
            if i % 6 == 0:
                c.showPage()
                page_num += 1
                c.setFont(FONT_NAME, 12)
                start = i + 1
                end = min(i + 6, len(events))
                c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, f"集体事件卡 ({start}-{end}/12) - 沿边框剪裁")
            
            row = (i % 6) // 3
            col = (i % 6) % 3
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (CARD_HEIGHT + CARD_MARGIN)
            
            self.draw_card_border(c, x, y, CARD_WIDTH, CARD_HEIGHT, bg_color=event["color"])
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 10*mm, event["name"])
            
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 18*mm, f"【{event['type']}】")
            
            c.setFont(FONT_NAME, 8)
            eff_lines = event["effect"].split("\n")
            ey = y + CARD_HEIGHT - 30*mm
            for el in eff_lines:
                c.drawString(x + 4*mm, ey, el)
                ey -= 10
            
            if event["note"]:
                c.setFont(FONT_NAME, 7)
                c.drawString(x + 4*mm, y + 4*mm, event["note"])
    
    def draw_personal_event_cards(self, c):
        """绘制个人事件卡"""
        events = [
            # 经典故事 (8张)
            {"name": "贫女一灯", "type": "故事", "effect": "若财≥2：财-2，福+3\n否则：福+1"},
            {"name": "割肉喂鹰", "type": "故事", "effect": "福+2，财-1"},
            {"name": "舍身饲虎", "type": "故事", "effect": "福+2"},
            {"name": "目连救母", "type": "故事", "effect": "福+2"},
            {"name": "须达拏太子", "type": "故事", "effect": "财-1，福+2"},
            {"name": "鹿王本生", "type": "故事", "effect": "福+1，慧+1"},
            {"name": "九色鹿", "type": "故事", "effect": "福+2"},
            {"name": "释迦牟尼苦行", "type": "故事", "effect": "慧+2，财-1"},
            # 职业专属 (8张)
            {"name": "丰年收成", "type": "农夫专属", "effect": "农夫：财+3\n其他：财+1"},
            {"name": "歉收之年", "type": "农夫专属", "effect": "农夫：财-2，福+1\n其他：财-1"},
            {"name": "大宗交易", "type": "商人专属", "effect": "商人：财+4\n其他：财+1"},
            {"name": "海上风暴", "type": "商人专属", "effect": "商人：掷骰\n4+:财+3 1-3:财-2"},
            {"name": "弟子求教", "type": "学者专属", "effect": "学者：慧+2，福+1\n其他：慧+1"},
            {"name": "焚书之劫", "type": "学者专属", "effect": "学者：慧-1，福+2\n其他：慧-1"},
            {"name": "皇帝供养", "type": "僧侣专属", "effect": "僧侣：财+3，福+2\n其他：福+1"},
            {"name": "破戒边缘", "type": "僧侣专属", "effect": "僧侣：选择\n财-2福+1 或 福-2"},
            # 抉择类 (8张)
            {"name": "一念之间", "type": "抉择", "effect": "选择：\n慧+2福-1 或 福+2慧-1"},
            {"name": "神秘访客", "type": "抉择", "effect": "若财≥2可选：\n财-2，福+3"},
            {"name": "拾金不昧", "type": "抉择", "effect": "选择：\n福+2 或 财+3福-1"},
            {"name": "舍财救人", "type": "抉择", "effect": "选择：\n财-3，福+4 或 无"},
            {"name": "诱惑考验", "type": "抉择", "effect": "选择：\n财+2慧-1 或 慧+1"},
            {"name": "见死不救", "type": "抉择", "effect": "选择：\n无 或 财-2福+3"},
            {"name": "施舍乞丐", "type": "抉择", "effect": "若财≥1可选：\n财-1，福+2"},
            {"name": "智慧传承", "type": "抉择", "effect": "选择：\n慧-1给他人 福+1"},
            # 机遇命运 (4张)
            {"name": "发现伏藏", "type": "机遇", "effect": "掷骰：\n5-6:慧+3福+2\n3-4:慧+1\n1-2:无"},
            {"name": "遇见高人", "type": "机遇", "effect": "掷骰：\n4+:慧+2\n1-3:福+1"},
            {"name": "命运之轮", "type": "机遇", "effect": "掷骰：\n5-6:福+2慧+2\n1-2:财-1福-1"},
            {"name": "奇遇仙人", "type": "机遇", "effect": "掷骰：\n6:全部资源+2\n1:全部资源-1"},
            # 互动类 (4张)
            {"name": "求助他人", "type": "互动", "effect": "请求任一玩家\n给你1财富\n对方若同意+1福"},
            {"name": "共修因缘", "type": "互动", "effect": "选1名玩家\n双方各+1慧"},
            {"name": "布施供养", "type": "互动", "effect": "给任一玩家1财\n双方各+1福"},
            {"name": "切磋论道", "type": "互动", "effect": "选1名玩家\n双方各+1慧+1福"},
        ]
        
        for i, event in enumerate(events):
            if i % 6 == 0:
                c.showPage()
                c.setFont(FONT_NAME, 12)
                start = i + 1
                end = min(i + 6, len(events))
                c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, f"个人事件卡 ({start}-{end}/32) - 沿边框剪裁")
            
            row = (i % 6) // 3
            col = (i % 6) % 3
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (CARD_HEIGHT + CARD_MARGIN)
            
            # 根据类型选择颜色
            if "故事" in event["type"]:
                bg = colors.Color(0.95, 0.95, 1.0)  # 浅蓝
            elif "专属" in event["type"]:
                bg = colors.Color(1.0, 1.0, 0.9)  # 浅黄
            elif "抉择" in event["type"]:
                bg = colors.Color(1.0, 0.95, 0.95)  # 浅红
            elif "机遇" in event["type"]:
                bg = colors.Color(0.95, 1.0, 0.95)  # 浅绿
            else:
                bg = colors.Color(1.0, 0.95, 1.0)  # 浅紫
            
            self.draw_card_border(c, x, y, CARD_WIDTH, CARD_HEIGHT, bg_color=bg)
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 10*mm, event["name"])
            
            c.setFont(FONT_NAME, 7)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 18*mm, f"【{event['type']}】")
            
            c.setFont(FONT_NAME, 8)
            eff_lines = event["effect"].split("\n")
            ey = y + CARD_HEIGHT - 30*mm
            for el in eff_lines:
                c.drawString(x + 4*mm, ey, el)
                ey -= 10
    
    def draw_being_cards(self, c):
        """绘制众生卡"""
        beings = [
            {"name": "饥民", "cost": 2, "fu": 2, "hui": 1, "desc": "饥寒交迫的流民"},
            {"name": "病者", "cost": 2, "fu": 2, "hui": 1, "desc": "身染重疾的病人"},
            {"name": "孤儿", "cost": 3, "fu": 3, "hui": 1, "desc": "无依无靠的孤儿"},
            {"name": "寡妇", "cost": 3, "fu": 2, "hui": 2, "desc": "失去丈夫的妇人"},
            {"name": "落魄书生", "cost": 3, "fu": 1, "hui": 3, "desc": "穷困潦倒的读书人"},
            {"name": "迷途商贾", "cost": 4, "fu": 2, "hui": 2, "desc": "破产失落的商人"},
            {"name": "悔过恶人", "cost": 4, "fu": 4, "hui": 1, "desc": "幡然悔悟的恶人"},
            {"name": "垂死老者", "cost": 5, "fu": 3, "hui": 3, "desc": "行将就木的老人"},
            {"name": "被弃婴儿", "cost": 2, "fu": 3, "hui": 0, "desc": "被遗弃的婴儿"},
            {"name": "绝望猎人", "cost": 4, "fu": 2, "hui": 2, "desc": "陷入绝望的猎户"},
        ]
        
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "众生卡 (1-6/10) - 沿边框剪裁")
        
        for i, being in enumerate(beings):
            if i == 6:
                c.showPage()
                c.setFont(FONT_NAME, 12)
                c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "众生卡 (7-10/10) - 沿边框剪裁")
            
            row = (i % 6) // 3
            col = (i % 6) % 3
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (CARD_HEIGHT + CARD_MARGIN)
            
            bg = colors.Color(0.9, 0.9, 0.9)  # 浅灰
            self.draw_card_border(c, x, y, CARD_WIDTH, CARD_HEIGHT, bg_color=bg)
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 12)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 12*mm, being["name"])
            
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 22*mm, being["desc"])
            
            c.setLineWidth(0.5)
            c.line(x + 5*mm, y + CARD_HEIGHT - 28*mm, x + CARD_WIDTH - 5*mm, y + CARD_HEIGHT - 28*mm)
            
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 40*mm, f"渡化成本：{being['cost']}财富")
            
            c.setFont(FONT_NAME, 9)
            c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT - 55*mm, f"奖励：福+{being['fu']}  慧+{being['hui']}")
            
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + CARD_WIDTH/2, y + 8*mm, "2回合不渡化则消失")
            c.drawCentredString(x + CARD_WIDTH/2, y + 0*mm + 4*mm, "劫难+4")
    
    def draw_action_cards(self, c):
        """绘制行动提示卡"""
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "行动提示卡 (4张，每人1张) - 沿边框剪裁")
        
        for i in range(4):
            row = i // 2
            col = i % 2
            
            card_w = 80 * mm
            card_h = 100 * mm
            
            x = MARGIN + col * (card_w + 10*mm)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (card_h + 5*mm)
            
            bg = colors.Color(0.98, 0.98, 0.98)
            c.setFillColor(bg)
            c.rect(x, y, card_w, card_h, fill=1, stroke=0)
            c.setStrokeColor(colors.black)
            c.setLineWidth(1.5)
            c.rect(x, y, card_w, card_h, fill=0, stroke=1)
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 11)
            c.drawCentredString(x + card_w/2, y + card_h - 10*mm, "行动提示卡")
            
            actions = [
                ("劳作", "+3财富（农夫+4）"),
                ("修行", "+2慧（学者+4）"),
                ("布施", "-2财，+2福（商人+4）"),
                ("渡化", "需慧≥5，支付成本"),
                ("护法", "-2财，+1福，劫难-2"),
            ]
            
            c.setFont(FONT_NAME, 9)
            ay = y + card_h - 25*mm
            for name, effect in actions:
                c.setFont(FONT_NAME, 10)
                c.drawString(x + 5*mm, ay, f"【{name}】")
                c.setFont(FONT_NAME, 8)
                c.drawString(x + 25*mm, ay, effect)
                ay -= 14
            
            c.setLineWidth(0.5)
            c.line(x + 5*mm, ay + 5*mm, x + card_w - 5*mm, ay + 5*mm)
            
            c.setFont(FONT_NAME, 8)
            c.drawString(x + 5*mm, ay - 5*mm, "每回合可执行2个行动")
            c.drawString(x + 5*mm, ay - 15*mm, "同一行动可重复执行")
    
    def draw_ab_cards(self, c):
        """绘制A/B选择卡"""
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "A/B选择卡 (4套×2张=8张) - 用于天灾抉择同时揭示")
        
        for i in range(8):
            row = i // 4
            col = i % 4
            
            card_w = 45 * mm
            card_h = 60 * mm
            
            x = MARGIN + col * (card_w + 5*mm)
            y = PAGE_HEIGHT - 35*mm - (row + 1) * (card_h + 5*mm)
            
            is_a = (i % 2 == 0)
            
            if is_a:
                bg = colors.Color(0.8, 0.9, 1.0)  # 蓝色A
                letter = "A"
                meaning = "合作\n牺牲"
            else:
                bg = colors.Color(1.0, 0.85, 0.85)  # 红色B
                letter = "B"
                meaning = "自保\n背叛"
            
            c.setFillColor(bg)
            c.rect(x, y, card_w, card_h, fill=1, stroke=0)
            c.setStrokeColor(colors.black)
            c.setLineWidth(2)
            c.rect(x, y, card_w, card_h, fill=0, stroke=1)
            
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 36)
            c.drawCentredString(x + card_w/2, y + card_h/2 + 5*mm, letter)
            
            c.setFont(FONT_NAME, 9)
            lines = meaning.split("\n")
            my = y + 15*mm
            for line in lines:
                c.drawCentredString(x + card_w/2, my, line)
                my -= 10
    
    def draw_tracks(self, c):
        """绘制轨道板"""
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "轨道板 - 沿边框剪裁")
        
        # 劫难轨道
        track_x = MARGIN
        track_y = PAGE_HEIGHT - 50*mm
        track_w = PAGE_WIDTH - 2*MARGIN
        track_h = 30*mm
        
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.5)
        c.rect(track_x, track_y, track_w, track_h, fill=0, stroke=1)
        
        c.setFont(FONT_NAME, 14)
        c.drawString(track_x + 5*mm, track_y + track_h - 10*mm, "劫难轨道")
        
        # 刻度 0-20
        cell_w = (track_w - 10*mm) / 21
        for i in range(21):
            cx = track_x + 5*mm + i * cell_w
            cy = track_y + 5*mm
            
            if i >= 12:
                c.setFillColor(colors.Color(1.0, 0.8, 0.8))
            else:
                c.setFillColor(colors.white)
            
            c.rect(cx, cy, cell_w - 1*mm, 15*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 9)
            c.drawCentredString(cx + cell_w/2, cy + 5*mm, str(i))
        
        c.setFont(FONT_NAME, 8)
        c.drawString(track_x + 5*mm, track_y - 5*mm, "≤12胜利 | ≥20失败")
        
        # 渡化计数
        track_y2 = track_y - 50*mm
        c.rect(track_x, track_y2, track_w, track_h, fill=0, stroke=1)
        
        c.setFont(FONT_NAME, 14)
        c.drawString(track_x + 5*mm, track_y2 + track_h - 10*mm, "渡化计数")
        
        cell_w2 = (track_w - 10*mm) / 11
        for i in range(11):
            cx = track_x + 5*mm + i * cell_w2
            cy = track_y2 + 5*mm
            
            if i >= 5:
                c.setFillColor(colors.Color(0.8, 1.0, 0.8))
            else:
                c.setFillColor(colors.white)
            
            c.rect(cx, cy, cell_w2 - 1*mm, 15*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 9)
            c.drawCentredString(cx + cell_w2/2, cy + 5*mm, str(i))
        
        c.setFont(FONT_NAME, 8)
        c.drawString(track_x + 5*mm, track_y2 - 5*mm, "≥5才能胜利")
        
        # 回合轨道
        track_y3 = track_y2 - 50*mm
        c.rect(track_x, track_y3, track_w/2, track_h, fill=0, stroke=1)
        
        c.setFont(FONT_NAME, 14)
        c.drawString(track_x + 5*mm, track_y3 + track_h - 10*mm, "回合")
        
        cell_w3 = (track_w/2 - 10*mm) / 6
        for i in range(1, 7):
            cx = track_x + 5*mm + (i-1) * cell_w3
            cy = track_y3 + 5*mm
            
            c.setFillColor(colors.white)
            c.rect(cx, cy, cell_w3 - 1*mm, 15*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 11)
            c.drawCentredString(cx + cell_w3/2, cy + 5*mm, str(i))
    
    def draw_resource_tokens(self, c):
        """绘制资源标记"""
        c.showPage()
        c.setFont(FONT_NAME, 12)
        c.drawCentredString(PAGE_WIDTH/2, PAGE_HEIGHT - 15*mm, "资源标记 - 剪裁后可折叠立起使用")
        
        # 财富标记（金色）
        c.setFont(FONT_NAME, 10)
        c.drawString(MARGIN, PAGE_HEIGHT - 35*mm, "财富标记（建议30个）")
        
        token_size = 15 * mm
        for i in range(30):
            row = i // 10
            col = i % 10
            x = MARGIN + col * (token_size + 2*mm)
            y = PAGE_HEIGHT - 55*mm - row * (token_size + 2*mm)
            
            c.setFillColor(colors.Color(1.0, 0.85, 0.4))
            c.circle(x + token_size/2, y + token_size/2, token_size/2 - 1*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + token_size/2, y + token_size/2 - 3*mm, "财")
        
        # 福标记（红色）
        c.setFont(FONT_NAME, 10)
        c.drawString(MARGIN, PAGE_HEIGHT - 115*mm, "福标记（建议30个）")
        
        for i in range(30):
            row = i // 10
            col = i % 10
            x = MARGIN + col * (token_size + 2*mm)
            y = PAGE_HEIGHT - 135*mm - row * (token_size + 2*mm)
            
            c.setFillColor(colors.Color(1.0, 0.6, 0.6))
            c.circle(x + token_size/2, y + token_size/2, token_size/2 - 1*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + token_size/2, y + token_size/2 - 3*mm, "福")
        
        # 慧标记（蓝色）
        c.setFont(FONT_NAME, 10)
        c.drawString(MARGIN, PAGE_HEIGHT - 195*mm, "慧标记（建议30个）")
        
        for i in range(30):
            row = i // 10
            col = i % 10
            x = MARGIN + col * (token_size + 2*mm)
            y = PAGE_HEIGHT - 215*mm - row * (token_size + 2*mm)
            
            c.setFillColor(colors.Color(0.6, 0.7, 1.0))
            c.circle(x + token_size/2, y + token_size/2, token_size/2 - 1*mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + token_size/2, y + token_size/2 - 3*mm, "慧")
        
        # 皈依/大乘标记
        c.setFont(FONT_NAME, 10)
        c.drawString(MARGIN, PAGE_HEIGHT - 260*mm, "皈依标记（4个）和大乘标记（4个）")
        
        for i in range(4):
            x = MARGIN + i * (token_size + 5*mm)
            y = PAGE_HEIGHT - 280*mm
            
            c.setFillColor(colors.Color(0.9, 0.9, 0.5))
            c.rect(x, y, token_size, token_size, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + token_size/2, y + token_size/2 - 2*mm, "皈依")
        
        for i in range(4):
            x = MARGIN + (i + 5) * (token_size + 5*mm)
            y = PAGE_HEIGHT - 280*mm
            
            c.setFillColor(colors.Color(0.9, 0.7, 0.9))
            c.rect(x, y, token_size, token_size, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(x + token_size/2, y + token_size/2 - 2*mm, "大乘")

def main():
    print("=" * 50)
    print("《功德轮回》v4.7 打印制作包生成器")
    print("=" * 50)
    
    # 检查reportlab
    try:
        from reportlab.lib.pagesizes import A4
        print("reportlab 已安装")
    except ImportError:
        print("正在安装 reportlab...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab"], check=True)
        print("reportlab 安装完成")
    
    pack = GamePrintPack()
    pack.generate()

if __name__ == "__main__":
    main()
