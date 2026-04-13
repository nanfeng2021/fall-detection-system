"""
数据分析面板 - 跌倒事件统计与可视化

功能:
- 趋势分析（日/周/月）
- 热力图（高发区域）
- 时间段分布
- 人员活动规律
- 报表导出
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px


@dataclass
class FallEvent:
    """跌倒事件记录"""
    timestamp: datetime
    event_type: str  # 'fall_confirmed', 'fall_suspected'
    location: str
    confidence: float
    cluster_id: int
    duration_seconds: float = 0.0
    video_filepath: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'location': self.location,
            'confidence': self.confidence,
            'cluster_id': self.cluster_id,
            'duration_seconds': self.duration_seconds,
            'video_filepath': self.video_filepath
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FallEvent':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=data['event_type'],
            location=data.get('location', '未知'),
            confidence=data.get('confidence', 0.0),
            cluster_id=data.get('cluster_id', 0),
            duration_seconds=data.get('duration_seconds', 0.0),
            video_filepath=data.get('video_filepath')
        )


class AnalyticsEngine:
    """分析引擎 - 处理和分析跌倒事件数据"""
    
    def __init__(self, data_dir: str = "analytics_data"):
        """
        初始化分析引擎
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.events_file = self.data_dir / "fall_events.json"
        self.events: List[FallEvent] = []
        
        # 加载已有数据
        self._load_events()
    
    def _load_events(self):
        """加载事件数据"""
        if self.events_file.exists():
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events = [FallEvent.from_dict(e) for e in data]
                print(f"✅ 已加载 {len(self.events)} 条事件记录")
            except Exception as e:
                print(f"❌ 加载事件数据失败：{e}")
                self.events = []
    
    def _save_events(self):
        """保存事件数据"""
        try:
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump([e.to_dict() for e in self.events], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存事件数据失败：{e}")
    
    def add_event(self, event: FallEvent):
        """添加事件记录"""
        self.events.append(event)
        self._save_events()
    
    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[str] = None
    ) -> List[FallEvent]:
        """获取指定时间范围内的事件"""
        filtered = []
        
        for event in self.events:
            if start_date <= event.timestamp <= end_date:
                if event_type is None or event.event_type == event_type:
                    filtered.append(event)
        
        return filtered
    
    def get_statistics(self) -> Dict:
        """获取总体统计信息"""
        if not self.events:
            return {
                'total_events': 0,
                'confirmed_falls': 0,
                'suspected_falls': 0,
                'average_confidence': 0.0,
                'first_event': None,
                'last_event': None,
                'unique_locations': 0,
                'locations': []
            }
        
        confirmed = sum(1 for e in self.events if e.event_type == 'fall_confirmed')
        suspected = sum(1 for e in self.events if e.event_type == 'fall_suspected')
        locations = list(set(e.location for e in self.events))
        
        return {
            'total_events': len(self.events),
            'confirmed_falls': confirmed,
            'suspected_falls': suspected,
            'average_confidence': sum(e.confidence for e in self.events) / len(self.events),
            'first_event': min(e.timestamp for e in self.events),
            'last_event': max(e.timestamp for e in self.events),
            'unique_locations': len(locations),
            'locations': locations
        }


class DashboardBuilder:
    """仪表板构建器 - 生成各种可视化图表"""
    
    def __init__(self, engine: AnalyticsEngine):
        """
        初始化仪表板构建器
        
        Args:
            engine: 分析引擎实例
        """
        self.engine = engine
    
    def create_trend_chart(
        self,
        period: str = 'day',
        days: int = 30
    ) -> go.Figure:
        """
        创建趋势图
        
        Args:
            period: 时间粒度 ('hour', 'day', 'week', 'month')
            days: 显示天数
            
        Returns:
            Plotly Figure
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        events = self.engine.get_events_in_range(start_date, end_date)
        
        if not events:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font_size=20)
            return fig
        
        # 按时间分组统计
        time_groups = defaultdict(lambda: {'confirmed': 0, 'suspected': 0})
        
        for event in events:
            if period == 'hour':
                key = event.timestamp.strftime("%Y-%m-%d %H:00")
            elif period == 'week':
                week_start = event.timestamp - timedelta(days=event.timestamp.weekday())
                key = week_start.strftime("%Y-%m-%d")
            elif period == 'month':
                key = event.timestamp.strftime("%Y-%m")
            else:  # day
                key = event.timestamp.strftime("%Y-%m-%d")
            
            if event.event_type == 'fall_confirmed':
                time_groups[key]['confirmed'] += 1
            else:
                time_groups[key]['suspected'] += 1
        
        # 排序
        sorted_keys = sorted(time_groups.keys())
        
        confirmed_values = [time_groups[k]['confirmed'] for k in sorted_keys]
        suspected_values = [time_groups[k]['suspected'] for k in sorted_keys]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=sorted_keys,
            y=confirmed_values,
            name='确认摔倒',
            marker_color='#f44336'
        ))
        
        fig.add_trace(go.Bar(
            x=sorted_keys,
            y=suspected_values,
            name='疑似摔倒',
            marker_color='#ff9800'
        ))
        
        fig.update_layout(
            title=f"跌倒事件趋势 ({period})",
            xaxis_title="时间",
            yaxis_title="事件数",
            barmode='stack',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
    
    def create_heatmap(self) -> go.Figure:
        """
        创建位置热力图
        
        Returns:
            Plotly Figure
        """
        stats = self.engine.get_statistics()
        
        if stats['total_events'] == 0:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font_size=20)
            return fig
        
        # 统计各位置事件数
        location_counts = defaultdict(int)
        location_confirmed = defaultdict(int)
        
        for event in self.engine.events:
            location_counts[event.location] += 1
            if event.event_type == 'fall_confirmed':
                location_confirmed[event.location] += 1
        
        locations = list(location_counts.keys())
        counts = [location_counts[loc] for loc in locations]
        confirmed = [location_confirmed[loc] for loc in locations]
        
        fig = go.Figure(data=[
            go.Table(
                header=dict(
                    values=['位置', '总事件数', '确认摔倒', '疑似摔倒', '占比'],
                    fill_color='#1976d2',
                    align='center',
                    font=dict(color='white', size=14)
                ),
                cells=dict(
                    values=[
                        locations,
                        counts,
                        confirmed,
                        [c - cf for c, cf in zip(counts, confirmed)],
                        [f"{c/sum(counts)*100:.1f}%" for c in counts]
                    ],
                    fill_color='#fafafa',
                    align='center'
                )
            )
        ])
        
        fig.update_layout(
            title="📍 位置分布统计",
            height=400
        )
        
        return fig
    
    def create_time_distribution(self) -> go.Figure:
        """
        创建时间段分布图（24 小时）
        
        Returns:
            Plotly Figure
        """
        events = self.engine.events
        
        if not events:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font_size=20)
            return fig
        
        # 按小时统计
        hour_counts = defaultdict(int)
        
        for event in events:
            hour = event.timestamp.hour
            hour_counts[hour] += 1
        
        hours = list(range(24))
        counts = [hour_counts[h] for h in hours]
        
        # 确定时段标签
        def get_period_label(hour):
            if 5 <= hour < 9:
                return "早晨"
            elif 9 <= hour < 12:
                return "上午"
            elif 12 <= hour < 14:
                return "中午"
            elif 14 <= hour < 18:
                return "下午"
            elif 18 <= hour < 22:
                return "晚上"
            else:
                return "深夜"
        
        colors = ['#64b5f6' if 6 <= h <= 22 else '#90caf9' for h in hours]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=hours,
            y=counts,
            marker_color=colors,
            name='事件数'
        ))
        
        fig.update_layout(
            title="⏰ 24 小时事件分布",
            xaxis_title="小时",
            yaxis_title="事件数",
            height=400
        )
        
        # 添加时段分区线
        for hour in [9, 12, 14, 18, 22]:
            fig.add_shape(
                type="line",
                x0=hour, y0=0, x1=hour, y1=max(counts) * 1.1,
                line=dict(color="gray", width=1, dash="dash")
            )
        
        return fig
    
    def create_weekday_distribution(self) -> go.Figure:
        """
        创建星期分布图
        
        Returns:
            Plotly Figure
        """
        events = self.engine.events
        
        if not events:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font_size=20)
            return fig
        
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday_counts = defaultdict(int)
        
        for event in events:
            weekday = event.timestamp.weekday()
            weekday_counts[weekday] += 1
        
        weekdays = list(range(7))
        counts = [weekday_counts[w] for w in weekdays]
        
        # 区分工作日和周末
        colors = ['#4caf50' if w < 5 else '#ff9800' for w in weekdays]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=weekday_names,
            y=counts,
            marker_color=colors,
            name='事件数'
        ))
        
        fig.update_layout(
            title="📅 星期分布",
            xaxis_title="星期",
            yaxis_title="事件数",
            height=400
        )
        
        return fig
    
    def create_confidence_distribution(self) -> go.Figure:
        """
        创建置信度分布图
        
        Returns:
            Plotly Figure
        """
        events = self.engine.events
        
        if not events:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False, font_size=20)
            return fig
        
        confidences = [e.confidence for e in events]
        
        # 分组：高 (>0.8), 中 (0.5-0.8), 低 (<0.5)
        high = sum(1 for c in confidences if c > 0.8)
        medium = sum(1 for c in confidences if 0.5 <= c <= 0.8)
        low = sum(1 for c in confidences if c < 0.5)
        
        fig = go.Figure(data=[
            go.Pie(
                labels=['高置信度 (>80%)', '中置信度 (50-80%)', '低置信度 (<50%)'],
                values=[high, medium, low],
                hole=0.3,
                marker_colors=['#4caf50', '#ff9800', '#f44336']
            )
        ])
        
        fig.update_layout(
            title="📊 置信度分布",
            height=400
        )
        
        return fig
    
    def create_summary_cards(self) -> List[Dict]:
        """
        创建摘要卡片数据
        
        Returns:
            list: 卡片数据列表
        """
        stats = self.engine.get_statistics()
        
        cards = [
            {
                'title': '总事件数',
                'value': stats['total_events'],
                'icon': '📈',
                'color': '#1976d2'
            },
            {
                'title': '确认摔倒',
                'value': stats['confirmed_falls'],
                'icon': '🚨',
                'color': '#f44336'
            },
            {
                'title': '疑似摔倒',
                'value': stats['suspected_falls'],
                'icon': '⚠️',
                'color': '#ff9800'
            },
            {
                'title': '平均置信度',
                'value': f"{stats['average_confidence']*100:.1f}%",
                'icon': '🎯',
                'color': '#4caf50'
            },
            {
                'title': '监控位置',
                'value': stats['unique_locations'],
                'icon': '📍',
                'color': '#9c27b0'
            }
        ]
        
        # 运行时长
        if stats['first_event'] and stats['last_event']:
            duration = stats['last_event'] - stats['first_event']
            days = duration.days
            
            cards.append({
                'title': '监控天数',
                'value': max(1, days),
                'icon': '📅',
                'color': '#00bcd4'
            })
        
        return cards
    
    def export_report(self, format: str = 'json') -> str:
        """
        导出报表
        
        Args:
            format: 导出格式 ('json', 'csv')
            
        Returns:
            str: 文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'json':
            filepath = self.engine.data_dir / f"report_{timestamp}.json"
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'statistics': self.engine.get_statistics(),
                'events': [e.to_dict() for e in self.engine.events]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return str(filepath)
        
        elif format == 'csv':
            filepath = self.engine.data_dir / f"report_{timestamp}.csv"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 表头
                f.write("时间，类型，位置，置信度，人员 ID，持续时间，视频文件\n")
                
                # 数据行
                for event in self.engine.events:
                    f.write(f"{event.timestamp.strftime('%Y-%m-%d %H:%M:%S')},"
                           f"{event.event_type},"
                           f"{event.location},"
                           f"{event.confidence},"
                           f"{event.cluster_id},"
                           f"{event.duration_seconds},"
                           f"{event.video_filepath or ''}\n")
            
            return str(filepath)
        
        else:
            raise ValueError(f"不支持的格式：{format}")


def create_analytics_engine() -> AnalyticsEngine:
    """创建分析引擎单例"""
    return AnalyticsEngine()


def create_dashboard_builder(engine: AnalyticsEngine) -> DashboardBuilder:
    """创建仪表板构建器"""
    return DashboardBuilder(engine)
