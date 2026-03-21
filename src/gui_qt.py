# -*- coding: utf-8 -*-
"""PySide6 客户端界面。"""

from __future__ import annotations

import ctypes
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
RESOURCE_ROOT = getattr(sys, "_MEIPASS", PROJECT_ROOT)
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
    QFileDialog,
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


ICON_PATH = os.path.join(RESOURCE_ROOT, "assets", "app_icon.ico")
APP_USER_MODEL_ID = "ProfessorZhi.BiliArchive"


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("客户端设置")
        self.setModal(True)
        self.resize(660, 300)

        settings = config.get_runtime_settings()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.login_input = QLineEdit(settings["sessdata"])
        self.login_input.setPlaceholderText("这里只填 SESSDATA 的值；留空则按未登录方式运行")
        self.login_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        output_row = QHBoxLayout()
        self.output_input = QLineEdit(settings["output_dir"])
        self.output_input.setPlaceholderText("默认是项目根目录下的 output，建议尽量选择项目内路径")
        browse_button = QPushButton("选择...")
        browse_button.clicked.connect(self.choose_output_dir)
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(browse_button)

        self.api_key_input = QLineEdit(settings["minimax_api_key"])
        self.api_key_input.setPlaceholderText("输入 MiniMax API Key，可留空")
        self.api_key_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.model_input = QLineEdit(settings["minimax_model"])
        self.model_input.setPlaceholderText("例如: MiniMax-M2.7")

        form.addRow("B站登录信息", self.login_input)
        form.addRow("输出文件夹", output_row)
        form.addRow("MiniMax API Key", self.api_key_input)
        form.addRow("MiniMax 模型", self.model_input)
        layout.addLayout(form)

        login_help = QLabel(
            "填写提示：这里只填浏览器 Cookie 里的 SESSDATA 值，不要粘贴整串 Cookie。"
            "登录 B站后按 F12，在 Cookies 中找到 SESSDATA 的 Value，复制到这里即可。"
        )
        login_help.setWordWrap(True)
        login_help.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(login_help)

        hint = QLabel(
            "这些设置只保存在本机，不会默认上传。"
            "B站登录信息留空时，程序会按未登录方式运行；"
            "输出文件夹默认是项目根目录下的 output，建议尽量选择项目内路径。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出文件夹",
            self.output_input.text().strip() or config.get_output_dir(),
        )
        if directory:
            self.output_input.setText(directory)

    def accept(self) -> None:
        output_dir = self.output_input.text().strip() or config.DEFAULT_OUTPUT_DIR
        config.save_runtime_settings(
            self.login_input.text(),
            output_dir,
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
        self.resize(900, 720)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self._build_ui()
        self._refresh_settings_hint()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("输入 Bilibili 视频链接或 BV 号")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1d232f;")
        layout.addWidget(title)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(self.hint)

        input_row = QHBoxLayout()
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("例如: BV1xx411c7mD 或 https://www.bilibili.com/video/BV...")
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

        self.settings_button = QPushButton("客户端设置")
        self.settings_button.clicked.connect(self.open_settings)

        options_row.addWidget(self.max_comments_input)
        options_row.addWidget(self.download_checkbox)
        options_row.addWidget(self.quality_combo)
        options_row.addWidget(self.ai_checkbox)
        options_row.addWidget(self.settings_button)
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
        self.video_path_value = QLineEdit()
        self.video_path_value.setReadOnly(True)

        form.addRow("视频标题", self.title_value)
        form.addRow("输出目录", self.output_value)
        form.addRow("JSON 文件", self.json_value)
        form.addRow("Markdown 文件", self.markdown_value)
        form.addRow("视频文件", self.video_path_value)
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

    def _refresh_settings_hint(self) -> None:
        settings = config.get_runtime_settings()
        login_state = "已登录" if settings["sessdata"] else "未登录"
        self.hint.setText(
            f"支持评论抓取、字幕导出、视频下载和 AI 点评。当前输出目录：{settings['output_dir']}；B站状态：{login_state}。"
        )

    def on_download_toggled(self, checked: bool) -> None:
        self.quality_combo.setEnabled(checked)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._refresh_settings_hint()
            QMessageBox.information(self, "保存成功", "客户端设置已保存，当前窗口后续操作会直接使用新设置。")

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
        self.video_path_value.setText(result.video_path or "")
        self.last_output_dir = result.output_dir
        self.open_button.setEnabled(True)

        self.log_output.appendPlainText(
            (
                f"最终汇总: 一级评论 {result.total_comments} 条；"
                f"子评论 {result.total_replies} 条；已抓取总评论 {result.total_units_fetched} 条；"
                f"页面显示总评论 {result.total_units_target} 条"
            )
        )
        if result.video_path:
            self.log_output.appendPlainText(f"视频文件: {result.video_path}")
        self.status_label.setText(f"状态: 处理完成，已抓取评论 {result.total_units_fetched} 条")
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
        self.settings_button.setEnabled(not busy)

    def _clear_result(self) -> None:
        self.title_value.clear()
        self.output_value.clear()
        self.json_value.clear()
        self.markdown_value.clear()
        self.video_path_value.clear()
        self.open_button.setEnabled(False)
        self.last_output_dir = ""
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("状态: 等待输入")


def run_gui() -> None:
    _set_windows_app_id()
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_gui()
