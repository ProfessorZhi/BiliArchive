# -*- coding: utf-8 -*-
"""
PySide6 客户端界面。
"""

from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config
from app_service import SaveOptions, SaveResult, save_bilibili_video


ICON_PATH = os.path.join(PROJECT_ROOT, "assets", "app_icon.ico")


class MinimaxSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("MiniMax 设置")
        self.setModal(True)
        self.resize(520, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        api_key, model = config.get_minimax_settings()

        self.api_key_input = QLineEdit(api_key)
        self.api_key_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.api_key_input.setPlaceholderText("输入 MiniMax API Key")

        self.model_input = QLineEdit(model)
        self.model_input.setPlaceholderText("例如: MiniMax-M2.7")

        form.addRow("API Key", self.api_key_input)
        form.addRow("模型名", self.model_input)
        layout.addLayout(form)

        hint = QLabel("设置会保存在项目根目录的 .biliarchive.local.json，仅本地使用。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        config.save_minimax_settings(
            self.api_key_input.text(),
            self.model_input.text(),
        )
        super().accept()


class SaveWorker(QThread):
    progress = Signal(str, int)
    success = Signal(object)
    failure = Signal(str)

    def __init__(self, video_input: str, options: SaveOptions):
        super().__init__()
        self.video_input = video_input
        self.options = options

    def run(self) -> None:
        try:
            result = save_bilibili_video(
                self.video_input,
                options=self.options,
                progress_callback=self.progress.emit,
            )
        except Exception as exc:
            self.failure.emit(str(exc))
            return
        self.success.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker: SaveWorker | None = None
        self.last_output_dir = ""
        self.setWindowTitle(config.APP_NAME)
        self.resize(860, 680)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("输入 Bilibili 视频链接或 BV 号")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1d232f;")
        layout.addWidget(title)

        hint = QLabel("BiliArchive 支持评论预扫描、字幕导出、视频下载和 AI 点评。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(hint)

        input_row = QHBoxLayout()
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText(
            "例如: BV1xx411c7mD 或 https://www.bilibili.com/video/BV..."
        )
        self.start_button = QPushButton("开始保存")
        self.start_button.clicked.connect(self.start_save)
        input_row.addWidget(self.video_input, 1)
        input_row.addWidget(self.start_button)
        layout.addLayout(input_row)

        options_row = QHBoxLayout()
        self.max_comments_input = QSpinBox()
        self.max_comments_input.setRange(0, 1_000_000)
        self.max_comments_input.setValue(0)
        self.max_comments_input.setSpecialValueText("全部")

        self.download_checkbox = QCheckBox("同时下载视频")
        self.download_checkbox.toggled.connect(self.on_download_toggled)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["360p", "480p", "720p", "1080p", "best"])
        self.quality_combo.setCurrentText("720p")
        self.quality_combo.setEnabled(False)

        self.ai_checkbox = QCheckBox("生成 AI 点评")
        self.ai_checkbox.setChecked(True)

        self.ai_settings_button = QPushButton("AI 设置")
        self.ai_settings_button.clicked.connect(self.open_ai_settings)

        options_row.addWidget(self.max_comments_input)
        options_row.addWidget(self.download_checkbox)
        options_row.addWidget(self.quality_combo)
        options_row.addWidget(self.ai_checkbox)
        options_row.addWidget(self.ai_settings_button)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: none;
                border-radius: 3px;
                background: #e8eef6;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background: #2f7cf6;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("状态: 等待输入")
        self.status_label.setStyleSheet("color: #0f5c8a;")
        layout.addWidget(self.status_label)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.title_value = QLineEdit()
        self.title_value.setReadOnly(True)
        self.output_value = QLineEdit()
        self.output_value.setReadOnly(True)
        self.json_value = QLineEdit()
        self.json_value.setReadOnly(True)
        self.markdown_value = QLineEdit()
        self.markdown_value.setReadOnly(True)

        form.addRow("视频标题", self.title_value)
        form.addRow("输出目录", self.output_value)
        form.addRow("JSON 文件", self.json_value)
        form.addRow("Markdown 文件", self.markdown_value)
        layout.addLayout(form)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.open_button = QPushButton("打开输出目录")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output_dir)
        action_row.addWidget(self.open_button)
        layout.addLayout(action_row)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("运行日志会显示在这里...")
        layout.addWidget(self.log_output, 1)

    def on_download_toggled(self, checked: bool) -> None:
        self.quality_combo.setEnabled(checked)

    def open_ai_settings(self) -> None:
        dialog = MinimaxSettingsDialog(self)
        if dialog.exec():
            QMessageBox.information(self, "保存成功", "MiniMax 设置已保存。")

    def start_save(self) -> None:
        video_input = self.video_input.text().strip()
        if not video_input:
            QMessageBox.warning(self, "缺少输入", "请输入 BV 号或视频链接。")
            return
        if self.worker and self.worker.isRunning():
            return

        options = SaveOptions(
            max_comments=self.max_comments_input.value(),
            download_video=self.download_checkbox.isChecked(),
            quality=self.quality_combo.currentText(),
            generate_summary=self.ai_checkbox.isChecked(),
        )

        self._set_busy(True)
        self._clear_result()
        self._update_progress("开始处理视频...", 1)
        self.worker = SaveWorker(video_input, options)
        self.worker.progress.connect(self.on_progress)
        self.worker.success.connect(self.on_success)
        self.worker.failure.connect(self.on_failure)
        self.worker.start()

    def on_progress(self, message: str, value: int) -> None:
        self._update_progress(message, value)

    def on_success(self, result: SaveResult) -> None:
        self.title_value.setText(result.video_title)
        self.output_value.setText(result.output_dir)
        self.json_value.setText(result.json_path)
        self.markdown_value.setText(result.markdown_path)
        self.last_output_dir = result.output_dir
        self.open_button.setEnabled(True)

        self.log_output.appendPlainText(
            (
                f"最终汇总: 一级评论 {result.total_comments}/{result.comment_target_count}；"
                f"子评论 {result.total_replies}；总评论 {result.total_units_fetched}/{result.total_units_target}"
            )
        )
        self.status_label.setText(
            f"状态: 处理完成，总评论 {result.total_units_fetched}/{result.total_units_target}"
        )
        self.progress_bar.setValue(100)
        self._set_busy(False)

    def on_failure(self, message: str) -> None:
        self._update_progress(f"处理失败: {message}", 100)
        QMessageBox.critical(self, "处理失败", message)
        self._set_busy(False)

    def _update_progress(self, message: str, value: int) -> None:
        self.log_output.appendPlainText(message)
        self.status_label.setText(f"状态: {message} ({value}%)")
        self.progress_bar.setValue(max(0, min(value, 100)))

    def open_output_dir(self) -> None:
        if not self.last_output_dir or not os.path.isdir(self.last_output_dir):
            QMessageBox.information(self, "目录不存在", "当前没有可打开的输出目录。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output_dir))

    def _set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)
        self.video_input.setEnabled(not busy)
        self.max_comments_input.setEnabled(not busy)
        self.download_checkbox.setEnabled(not busy)
        self.quality_combo.setEnabled(not busy and self.download_checkbox.isChecked())
        self.ai_checkbox.setEnabled(not busy)
        self.ai_settings_button.setEnabled(not busy)

    def _clear_result(self) -> None:
        self.title_value.clear()
        self.output_value.clear()
        self.json_value.clear()
        self.markdown_value.clear()
        self.open_button.setEnabled(False)
        self.last_output_dir = ""
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("状态: 等待输入")


def run_gui() -> None:
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_gui()
