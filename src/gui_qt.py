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
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import bilibili_api
import config
import minimax_client
from app_service import SaveOptions, SaveResult, save_bilibili_video


ICON_PATH = os.path.join(RESOURCE_ROOT, "assets", "app_icon.ico")
APP_USER_MODEL_ID = "ProfessorZhi.BiliArchive"


def _short_message(message: str, limit: int = 120) -> str:
    normalized = " ".join((message or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..." if limit > 3 else normalized[:limit]


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def _resolve_login_state_text(settings: dict[str, str]) -> str:
    login_mode = (settings.get("login_mode") or "none").strip().lower()
    if login_mode == "cookie":
        ok, message = bilibili_api.validate_cookie(settings.get("cookie", ""))
        return message if ok else f"异常：{message}"
    if login_mode == "sessdata":
        ok, message = bilibili_api.validate_sessdata(settings.get("sessdata", ""))
        return message if ok else f"异常：{message}"
    return "未登录"


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("客户端设置")
        self.setModal(True)
        self.resize(760, 560)

        settings = config.get_runtime_settings()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.login_mode_combo = QComboBox()
        self.login_mode_combo.addItem("未登录", "none")
        self.login_mode_combo.addItem("使用 SESSDATA", "sessdata")
        self.login_mode_combo.addItem("使用整串 Cookie", "cookie")
        current_mode = settings.get("login_mode", "none") or "none"
        index = max(0, self.login_mode_combo.findData(current_mode))
        self.login_mode_combo.setCurrentIndex(index)

        self.sessdata_input = QLineEdit(settings.get("sessdata", ""))
        self.sessdata_input.setPlaceholderText("只填浏览器 Cookie 里的 SESSDATA 值")
        self.sessdata_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.cookie_input = QPlainTextEdit()
        self.cookie_input.setPlaceholderText("可直接粘贴整串浏览器 Cookie")
        self.cookie_input.setPlainText(settings.get("cookie", ""))
        self.cookie_input.setMaximumHeight(96)

        output_row = QHBoxLayout()
        self.output_input = QLineEdit(settings["output_dir"])
        self.output_input.setPlaceholderText("默认是项目根目录下的 output，也可以手动改")
        browse_button = QPushButton("选择...")
        browse_button.clicked.connect(self.choose_output_dir)
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(browse_button)

        self.api_key_input = QLineEdit(settings["minimax_api_key"])
        self.api_key_input.setPlaceholderText("留空则跳过 AI 点评")
        self.api_key_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.model_input = QLineEdit(settings["minimax_model"])
        self.model_input.setPlaceholderText("例如：MiniMax-M2.7")

        self.sessdata_status_label = QLabel("尚未检测")
        self.cookie_status_label = QLabel("尚未检测")
        self.api_status_label = QLabel("尚未检测")
        for label in (self.sessdata_status_label, self.cookie_status_label, self.api_status_label):
            label.setWordWrap(True)
            label.setStyleSheet("color: #5f6b7a;")

        form.addRow("登录方式", self.login_mode_combo)
        form.addRow("SESSDATA", self.sessdata_input)
        form.addRow("SESSDATA 检测", self.sessdata_status_label)
        form.addRow("整串 Cookie", self.cookie_input)
        form.addRow("Cookie 检测", self.cookie_status_label)
        form.addRow("输出文件夹", output_row)
        form.addRow("MiniMax API Key", self.api_key_input)
        form.addRow("API 检测", self.api_status_label)
        form.addRow("MiniMax 模型", self.model_input)
        layout.addLayout(form)

        detect_row = QHBoxLayout()
        detect_row.addStretch(1)
        self.detect_button = QPushButton("立即检测")
        self.detect_button.clicked.connect(self.run_validation)
        detect_row.addWidget(self.detect_button)
        layout.addLayout(detect_row)

        login_help = QLabel(
            "填写提示：可以二选一。\n"
            "1. 选择“使用 SESSDATA”时，只填 SESSDATA 的值，不要粘贴整串 Cookie。\n"
            "2. 选择“使用整串 Cookie”时，可以直接把浏览器里的整串 Cookie 粘贴进来。\n"
            "3. 选择“未登录”时，两项都可以留空。"
        )
        login_help.setWordWrap(True)
        login_help.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(login_help)

        cookie_help = QLabel(
            "如何找到整串 Cookie：\n"
            "1. 先在浏览器里登录 B站并打开任意一个 B站页面。\n"
            "2. 按 F12 打开开发者工具，切到“网络(Network)”或“应用(Application/存储)”面板。\n"
            "3. 如果用 Network：刷新页面，点开任意一个发往 bilibili.com 的请求，在 Request Headers 里找到 Cookie，复制整串内容。\n"
            "4. 如果用 Application/存储：打开 Cookies，选择 bilibili.com，把需要的 Cookie 项拼成一整串后再粘贴。\n"
            "5. 整串 Cookie 通常像这样：SESSDATA=...; bili_jct=...; DedeUserID=...; buvid3=..."
        )
        cookie_help.setWordWrap(True)
        cookie_help.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(cookie_help)

        sessdata_help = QLabel(
            "如何找到 SESSDATA：\n"
            "1. 在浏览器里登录 B站后按 F12。\n"
            "2. 打开“应用(Application/存储)”面板，再打开 Cookies。\n"
            "3. 选择 bilibili.com，找到名称为 SESSDATA 的条目。\n"
            "4. 只复制它的 Value 值粘贴到这里，不要带前面的 SESSDATA=，也不要把整串 Cookie 都贴进来。"
        )
        sessdata_help.setWordWrap(True)
        sessdata_help.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(sessdata_help)

        hint = QLabel("这些设置只保存在本机，不会默认上传。输出文件夹默认是项目根目录下的 output。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.login_mode_combo.currentIndexChanged.connect(self._apply_login_mode_state)
        self._apply_login_mode_state()

    def _apply_login_mode_state(self) -> None:
        mode = self.login_mode_combo.currentData()
        self.sessdata_input.setEnabled(mode == "sessdata")
        self.cookie_input.setEnabled(mode == "cookie")

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_input.text().strip() or config.get_output_dir(),
        )
        if directory:
            self.output_input.setText(directory)

    def run_validation(self) -> tuple[bool, bool, bool]:
        sessdata = self.sessdata_input.text().strip()
        cookie = self.cookie_input.toPlainText().strip()
        api_key = self.api_key_input.text().strip()
        model = self.model_input.text().strip() or "MiniMax-M2.7"

        sess_ok, sess_message = bilibili_api.validate_sessdata(sessdata)
        cookie_ok, cookie_message = bilibili_api.validate_cookie(cookie)
        api_ok, api_message = minimax_client.validate_api_key(api_key, model)

        self.sessdata_status_label.setText(sess_message)
        self.sessdata_status_label.setStyleSheet(f"color: {'#1f7a1f' if sess_ok else '#c0392b'};")
        self.cookie_status_label.setText(cookie_message)
        self.cookie_status_label.setStyleSheet(f"color: {'#1f7a1f' if cookie_ok else '#c0392b'};")
        self.api_status_label.setText(api_message)
        self.api_status_label.setStyleSheet(f"color: {'#1f7a1f' if api_ok else '#c0392b'};")
        return sess_ok, cookie_ok, api_ok

    def accept(self) -> None:
        output_dir = self.output_input.text().strip() or config.DEFAULT_OUTPUT_DIR
        login_mode = self.login_mode_combo.currentData()
        sessdata = self.sessdata_input.text().strip()
        cookie = self.cookie_input.toPlainText().strip()
        api_key = self.api_key_input.text().strip()
        model = self.model_input.text().strip() or "MiniMax-M2.7"

        sess_ok, cookie_ok, api_ok = self.run_validation()

        if login_mode == "sessdata" and not sessdata:
            QMessageBox.warning(self, "缺少登录信息", "你选择了 SESSDATA 登录，请填写 SESSDATA。")
            return
        if login_mode == "cookie" and not cookie:
            QMessageBox.warning(self, "缺少登录信息", "你选择了整串 Cookie 登录，请填写整串 Cookie。")
            return
        if login_mode == "sessdata" and not sess_ok:
            QMessageBox.warning(self, "登录信息无效", "SESSDATA 检测未通过，请检查后再保存。")
            return
        if login_mode == "cookie" and not cookie_ok:
            QMessageBox.warning(self, "登录信息无效", "整串 Cookie 检测未通过，请检查后再保存。")
            return
        if not api_ok:
            QMessageBox.warning(self, "API 设置无效", "MiniMax API Key 或模型检测未通过，请检查后再保存。")
            return

        config.save_runtime_settings(login_mode, sessdata, cookie, output_dir, api_key, model)
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
        self.hint.setTextFormat(Qt.PlainText)
        self.hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.hint.setStyleSheet("color: #5f6b7a;")
        layout.addWidget(self.hint)

        input_row = QHBoxLayout()
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("例如：BV1xx411c7mD 或 https://www.bilibili.com/video/BV...")
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

        self.status_label = QLabel("状态：等待输入")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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
        self.log_output.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.log_output.setPlaceholderText("运行日志会显示在这里...")
        layout.addWidget(self.log_output, 1)

    def _refresh_settings_hint(self) -> None:
        settings = config.get_runtime_settings()
        login_state = _resolve_login_state_text(settings)
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
                f"最终汇总：一级评论 {result.total_comments} 条；"
                f"子评论 {result.total_replies} 条；已抓取总评论 {result.total_units_fetched} 条；"
                f"页面显示总评论 {result.total_units_target} 条"
            )
        )
        self.log_output.appendPlainText(f"说明：{result.summary_note}")
        if result.video_path:
            self.log_output.appendPlainText(f"视频文件：{result.video_path}")
        self.status_label.setText(f"状态：{_short_message('处理完成，' + result.summary_note, 160)}")
        self.progress_bar.setValue(100)
        self._set_busy(False)

    def on_failure(self, message: str) -> None:
        self._update_progress(f"处理失败：{message}", 100)
        QMessageBox.critical(self, "处理失败", _short_message(message, 300))
        self._set_busy(False)

    def _update_progress(self, message: str, value: int) -> None:
        self.log_output.appendPlainText(message)
        self.status_label.setText(f"状态：{_short_message(message, 160)} ({value}%)")
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
        self.status_label.setText("状态：等待输入")


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
