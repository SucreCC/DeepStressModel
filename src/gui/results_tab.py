"""
测试结果显示标签页
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QPushButton, QFileDialog, QMessageBox,
    QDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from src.utils.logger import setup_logger
from src.data.db_manager import db_manager
from src.engine.api_client import APIResponse
from src.engine.test_manager import TestProgress
import time
import os
import csv

logger = setup_logger("results_tab")

class ResultsTab(QWidget):
    """测试结果显示标签页"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_records = {}  # 当前测试会话的记录
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建工具栏
        toolbar = QHBoxLayout()
        
        # 导出按钮
        export_btn = QPushButton("导出记录")
        export_btn.clicked.connect(self._export_records)
        toolbar.addWidget(export_btn)
        
        # 清除日志按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 创建结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(12)
        self.result_table.setHorizontalHeaderLabels([
            "会话名称",
            "完成/总数",
            "成功率",
            "平均响应时间",
            "平均生成速度",
            "当前速度",
            "总字符数",
            "平均TPS",
            "总耗时",
            "模型名称",
            "并发数",
            "操作"
        ])
        
        # 设置表格属性
        header = self.result_table.horizontalHeader()
        # 先设置所有列自适应内容
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置特定列的宽度策略
        min_widths = {
            0: 200,  # 会话名称
            1: 100,  # 完成/总数
            2: 80,   # 成功率
            3: 120,  # 平均响应时间
            4: 120,  # 平均生成速度
            5: 100,  # 当前速度
            6: 100,  # 总字符数
            7: 100,  # 平均TPS
            8: 100,  # 总耗时
            9: 150,  # 模型名称
            10: 80,  # 并发数
            11: 80   # 操作
        }
        
        # 应用最小宽度
        for col, width in min_widths.items():
            self.result_table.setColumnWidth(col, width)
        
        # 设置会话名称列可以自动拉伸
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.result_table)
        
        # 错误信息显示区域
        self.error_text = QTextEdit()
        self.error_text.setPlaceholderText("测试过程中的错误信息将在此显示...")
        self.error_text.setMaximumHeight(100)
        self.error_text.setReadOnly(True)
        layout.addWidget(self.error_text)
        
        self.setLayout(layout)
        
        # 加载历史记录
        self._load_history_records()
    
    def _load_history_records(self):
        """加载历史测试记录"""
        try:
            logger.debug("开始加载历史测试记录")
            records = db_manager.get_test_records()
            logger.debug(f"获取到 {len(records)} 条历史记录")
            
            # 清空现有记录
            self.result_table.clearContents()
            self.result_table.setRowCount(0)
            
            if not records:
                logger.info("没有历史测试记录")
                return
            
            # 设置表格行数
            self.result_table.setRowCount(len(records))
            
            # 添加记录到表格
            for row, record in enumerate(records):
                try:
                    self._add_record_to_table(row, record)
                except Exception as e:
                    logger.error(f"添加第 {row} 行记录失败: {e}", exc_info=True)
                    continue
            
            logger.info(f"成功加载 {len(records)} 条历史记录")
            
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载历史记录失败: {e}")
    
    def _add_record_to_table(self, row: int, record: dict):
        """添加记录到表格"""
        try:
            # 设置会话名称
            self.result_table.setItem(row, 0, QTableWidgetItem(record["session_name"]))
            
            # 设置完成/总数
            completion = f"{record['successful_tasks']}/{record['total_tasks']}"
            self.result_table.setItem(row, 1, QTableWidgetItem(completion))
            
            # 设置成功率
            success_rate = (record['successful_tasks'] / record['total_tasks'] * 100) if record['total_tasks'] > 0 else 0
            self.result_table.setItem(row, 2, QTableWidgetItem(f"{success_rate:.1f}%"))
            
            # 设置平均响应时间
            self.result_table.setItem(row, 3, QTableWidgetItem(f"{record['avg_response_time']:.1f}s"))
            
            # 设置平均生成速度
            self.result_table.setItem(row, 4, QTableWidgetItem(f"{record['avg_generation_speed']:.1f}字/秒"))
            
            # 设置当前速度
            self.result_table.setItem(row, 5, QTableWidgetItem(f"{record['current_speed']:.1f}字/秒"))
            
            # 设置总字符数
            self.result_table.setItem(row, 6, QTableWidgetItem(str(record['total_chars'])))
            
            # 设置平均TPS
            self.result_table.setItem(row, 7, QTableWidgetItem(f"{record['avg_tps']:.1f}"))
            
            # 设置总耗时
            self.result_table.setItem(row, 8, QTableWidgetItem(f"{record['total_time']:.1f}s"))
            
            # 设置模型名称
            self.result_table.setItem(row, 9, QTableWidgetItem(record['model_name']))
            
            # 设置并发数
            self.result_table.setItem(row, 10, QTableWidgetItem(str(record['concurrency'])))
            
            # 创建操作按钮容器
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(2, 2, 2, 2)  # 设置较小的边距
            button_layout.setSpacing(4)  # 设置按钮之间的间距
            
            # 添加日志按钮
            log_btn = QPushButton("日志")
            log_btn.setFixedWidth(40)  # 设置固定宽度
            log_btn.clicked.connect(lambda: self._view_log(record.get('log_file', ''), record['session_name']))
            button_layout.addWidget(log_btn)
            
            # 添加删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setFixedWidth(40)  # 设置固定宽度
            delete_btn.clicked.connect(lambda: self._delete_record(record['session_name']))
            button_layout.addWidget(delete_btn)
            
            button_widget.setLayout(button_layout)
            self.result_table.setCellWidget(row, 11, button_widget)
            
            logger.debug(f"记录已添加到表格第 {row} 行")
            
        except Exception as e:
            logger.error(f"添加记录到表格失败: {e}", exc_info=True)
    
    def _view_log(self, log_file: str, session_name: str):
        """查看日志文件"""
        logger.debug(f"尝试查看日志文件，会话: {session_name}, 日志文件路径: {log_file}")
        
        if not log_file:
            logger.warning(f"会话 {session_name} 的日志文件路径为空")
            QMessageBox.warning(self, "提示", f"未找到会话 {session_name} 的日志文件")
            return
            
        if not os.path.exists(log_file):
            logger.warning(f"日志文件不存在: {log_file}")
            QMessageBox.warning(self, "错误", f"日志文件不存在: {log_file}")
            return
        
        logger.debug(f"开始读取日志文件: {log_file}")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"测试日志 - {session_name}")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # 添加日志内容
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                log_text.setText(content)
                logger.debug(f"成功读取日志文件，内容长度: {len(content)} 字符")
        except Exception as e:
            error_msg = f"读取日志文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            log_text.setText(error_msg)
        
        layout.addWidget(log_text)
        
        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _delete_record(self, session_name: str):
        """删除测试记录"""
        logger.debug(f"尝试删除测试记录，会话: {session_name}")
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话 {session_name} 的测试记录吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                logger.debug(f"开始删除测试记录: {session_name}")
                result = db_manager.delete_test_record(session_name)
                logger.debug(f"删除测试记录结果: {result}")
                
                if result:
                    # 重新加载记录
                    logger.info(f"成功删除测试记录: {session_name}，准备重新加载记录")
                    self._load_history_records()
                    QMessageBox.information(self, "成功", "测试记录已删除")
                else:
                    error_msg = f"删除测试记录失败: {session_name}"
                    logger.error(error_msg)
                    QMessageBox.warning(self, "错误", error_msg)
            except Exception as e:
                error_msg = f"删除测试记录时发生错误: {e}"
                logger.error(error_msg, exc_info=True)
                QMessageBox.critical(self, "错误", error_msg)
    
    def _export_records(self):
        """导出测试记录"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出记录",
            "",
            "CSV文件 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            records = db_manager.get_test_records()
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow([
                    "测试时间", "模型名称", "并发数", "总任务数",
                    "成功任务数", "失败任务数", "平均响应时间(ms)",
                    "平均生成速度(字符/秒)", "总Token数",
                    "平均TPS", "总耗时(ms)"
                ])
                
                # 写入数据
                for record in records:
                    writer.writerow([
                        record["test_time"],
                        record["model_name"],
                        record["concurrency"],
                        record["total_tasks"],
                        record["successful_tasks"],
                        record["failed_tasks"],
                        record["avg_response_time"],
                        record["avg_generation_speed"],
                        record["total_tokens"],
                        record["avg_tps"],
                        record["total_time"]
                    ])
            
            QMessageBox.information(self, "成功", "记录导出成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出记录失败: {e}")
    
    def _clear_logs(self):
        """清除测试日志"""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有测试日志文件吗？\n注意：测试记录将被保留，只清除日志文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.clear_test_logs():
                QMessageBox.information(self, "成功", "日志文件已清除")
            else:
                QMessageBox.warning(self, "警告", "清除日志文件时发生错误")
    
    def prepare_test(self, model_config: dict, concurrency: int, test_task_id: str):
        """准备新的测试会话"""
        # 生成会话名称
        session_name = time.strftime("test_%Y%m%d_%H%M%S")
        
        # 初始化会话记录
        self.current_records = {
            "session_name": session_name,
            "model_name": model_config["name"],
            "concurrency": concurrency,
            "test_task_id": test_task_id,
            "datasets": {}
        }
        
        logger.info(f"准备测试会话: {session_name}")
        
    def _save_test_records(self):
        """保存测试记录"""
        try:
            # 确保必要的字段存在
            if not hasattr(self, 'current_records'):
                logger.error("没有当前测试记录")
                return
            
            # 确保model_name字段存在
            if "model_name" not in self.current_records and "model_config" in self.current_records:
                self.current_records["model_name"] = self.current_records["model_config"]["name"]
            
            # 创建日志文件
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "logs", "tests")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{self.current_records.get('test_task_id', 'unknown')}.log")
            logger.info(f"创建日志文件: {log_file}")
            
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"测试ID: {self.current_records.get('test_task_id', 'unknown')}\n")
                f.write(f"会话名称: {self.current_records.get('session_name', 'unknown')}\n")
                f.write(f"模型名称: {self.current_records.get('model_name', 'unknown')}\n")
                f.write(f"并发数: {self.current_records.get('concurrency', 0)}\n")
                f.write(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.current_records.get('start_time', time.time())))}\n")
                if 'end_time' in self.current_records and self.current_records['end_time']:
                    f.write(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.current_records['end_time']))}\n")
                    duration = self.current_records['end_time'] - self.current_records.get('start_time', 0)
                    f.write(f"总耗时: {duration:.2f}秒\n")
                
                f.write("\n数据集统计信息:\n")
                for dataset_name, stats in self.current_records.get('datasets', {}).items():
                    f.write(f"\n{dataset_name}:\n")
                    f.write(f"  总任务数: {stats.get('total', 0)}\n")
                    f.write(f"  成功数: {stats.get('successful', 0)}\n")
                    f.write(f"  失败数: {stats.get('total', 0) - stats.get('successful', 0)}\n")
                    if stats.get('successful', 0) > 0:
                        success_rate = (stats['successful'] / stats['total']) * 100
                        avg_time = stats.get('total_time', 0) / stats['successful']
                        avg_speed = stats.get('total_chars', 0) / stats.get('total_time', 1)
                        f.write(f"  成功率: {success_rate:.1f}%\n")
                        f.write(f"  平均响应时间: {avg_time:.2f}秒\n")
                        f.write(f"  平均生成速度: {avg_speed:.1f}字/秒\n")
                        f.write(f"  总字符数: {stats.get('total_chars', 0)}\n")
            
            # 计算总体统计信息
            total_tasks = 0
            successful_tasks = 0
            failed_tasks = 0
            total_chars = 0
            total_tokens = 0
            total_time = 0
            
            for stats in self.current_records.get('datasets', {}).values():
                total_tasks += stats.get('total', 0)
                successful_tasks += stats.get('successful', 0)
                failed_tasks += stats.get('total', 0) - stats.get('successful', 0)
                total_chars += stats.get('total_chars', 0)
                total_tokens += stats.get('total_tokens', 0)
                total_time += stats.get('total_time', 0)
            
            # 计算平均值
            avg_response_time = total_time / successful_tasks if successful_tasks > 0 else 0
            avg_generation_speed = total_chars / total_time if total_time > 0 else 0
            avg_tps = total_tokens / total_time if total_time > 0 else 0
            
            # 保存到数据库
            db_record = {
                "test_task_id": self.current_records.get('test_task_id', 'unknown'),
                "session_name": self.current_records.get('session_name', 'unknown'),
                "model_name": self.current_records.get('model_name', 'unknown'),
                "concurrency": self.current_records.get('concurrency', 0),
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "avg_response_time": avg_response_time,
                "avg_generation_speed": avg_generation_speed,
                "total_chars": total_chars,
                "total_tokens": total_tokens,
                "avg_tps": avg_tps,
                "total_time": total_time,
                "current_speed": avg_generation_speed,
                "test_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                "log_file": log_file
            }
            
            success = db_manager.save_test_record(db_record)
            if success:
                logger.info(f"测试记录已保存到数据库: {db_record['test_task_id']}")
            else:
                logger.error("保存测试记录到数据库失败")
            
        except Exception as e:
            logger.error(f"保存测试记录失败: {e}", exc_info=True)
            raise

    def add_result(self, dataset_name: str, response: APIResponse):
        """添加测试结果"""
        try:
            if dataset_name not in self.current_records["datasets"]:
                self.current_records["datasets"][dataset_name] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_time": 0.0,
                    "total_tokens": 0,
                    "total_chars": 0,
                    "start_time": time.time()
                }
            
            stats = self.current_records["datasets"][dataset_name]
            stats["total"] += 1
            
            if response.success:
                stats["successful"] += 1
                stats["total_time"] += response.duration
                stats["total_tokens"] += response.total_tokens
                stats["total_chars"] += response.total_chars
            else:
                stats["failed"] += 1
                if response.error_msg:
                    self.error_text.append(f"数据集 {dataset_name} 错误: {response.error_msg}")
            
            logger.debug(f"已添加数据集 {dataset_name} 的测试结果")
            
        except Exception as e:
            logger.error(f"添加测试结果失败: {e}", exc_info=True)
