"""Primeiro corpo 2D da Yuna: chibi vetorial, transparente e interativo.

Não requer imagens, Godot, rede, GPU dedicada ou arquivos adicionais. É uma
BASE VISUAL estilizada para posterior substituição por arte anime em camadas.
"""
import math
import time

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from avatar_state import (HAIR, EYES, OUTFITS, HAIR_STYLES, COSTUMES,
                          ACCESSORIES, SIZES, load_style)
from avatar_motion import ambient_pose, ease_gaze, frame_at, blend_frames
from avatar_idle_life import idle_expression
from hardware_profiles import select_profile
from hardware_detection import detected_profile
from battery_life import BatteryCompanion, read_battery


class YunaAvatar(QWidget):
    """Personagem opcional sobre a área de trabalho; não recebe entrada de voz."""
    def __init__(self, root, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.root = root
        self.setObjectName("YunaAvatar")
        self.setWindowTitle("Yuna • Avatar 2D")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.appearance = load_style(root)
        self._apply_size()
        self.pose = "idle"
        self.pose_until = 0.0
        self.speaking = False
        self.mouth_level = None
        self.bubble = ""
        self.bubble_until = 0.0
        self.drag_start = None
        self.tick_count = 0
        self._previous_motion = None
        self._last_render_pose = None
        self._transition_start = 0.0
        self._transition_from = None
        self.step = 1
        self.x_coordinate = 0.0
        self._eye_cursor = (95.0, 135.0)
        self._walk_speed = 0.0
        self._battery_companion = BatteryCompanion()
        self.battery_mood = self._battery_companion.observe(None)
        self._battery_seeking = False
        self._base_avatar_fps = self._animation_profile().avatar_fps
        self._position_initial()
        self.animation = QTimer(self)
        self.animation.setInterval(round(1000 / self._base_avatar_fps))
        self.animation.timeout.connect(self.advance)
        self.animation.start()
        self.battery_timer = QTimer(self)
        self.battery_timer.setInterval(90000)
        self.battery_timer.timeout.connect(self.refresh_battery_state)
        self.battery_timer.start()
        QTimer.singleShot(1600, self.refresh_battery_state)

    def _animation_profile(self):
        """Detecta hardware local; permite override explícito de perfil."""
        return detected_profile()

    def refresh_animation_profile(self):
        """Aplica mudanças de perfil sem recriar o avatar."""
        self._base_avatar_fps = self._animation_profile().avatar_fps
        self._apply_battery_fps()

    def _apply_battery_fps(self):
        limit = self.battery_mood.fps_cap
        fps = min(self._base_avatar_fps, limit) if limit else self._base_avatar_fps
        self.animation.setInterval(round(1000 / fps))

    def refresh_battery_state(self):
        """Consulta o indicador do Windows sem instalar bibliotecas extras."""
        self.set_battery_status(read_battery())

    def set_battery_status(self, status):
        """Separa reação visual de gestos explícitos, fala e preferências."""
        previous = self.battery_mood.mode
        self.battery_mood = self._battery_companion.observe(status)
        if self.battery_mood.mode != previous:
            self._apply_battery_fps()
        if (self.battery_mood.announcement and not self.speaking
                and self.drag_start is None
                and time.monotonic() >= self.pose_until):
            self.bubble = self.battery_mood.announcement
            self.bubble_until = time.monotonic() + 8
            if self.battery_mood.suggested_activity:
                self.set_pose("happy", seconds=6)
        self.update()

    def _apply_size(self):
        """Redimensiona o desenho vetorial sem exigir imagens ou modelos 3D."""
        factor = SIZES[self.appearance["size"]]
        self.setFixedSize(round(190 * factor), round(277 * factor))

    def _keep_on_screen(self):
        """Evita perder o avatar fora da área visível após mudar de tamanho."""
        screen = QApplication.screenAt(self.geometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        x = min(max(self.x(), rect.left()), max(rect.left(), rect.right() - self.width() + 1))
        y = min(max(self.y(), rect.top()), max(rect.top(), rect.bottom() - self.height() + 1))
        self.move(x, y)
        self.x_coordinate = float(x)

    def _position_initial(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(80, 80)
            return
        r = screen.availableGeometry()
        self.move(max(r.left(), r.right() - 235),
                  max(r.top(), r.bottom() - self.height() - 10))
        self.x_coordinate = float(self.x())

    def reload_appearance(self):
        self.appearance = load_style(self.root)
        self._apply_size()
        self._keep_on_screen()
        self.update()

    def set_pose(self, pose, seconds=4, phrase=""):
        if pose not in ("idle", "walk", "sit", "angry", "happy", "talk",
                        "wave", "pose", "surprised", "curious",
                        "wink", "laugh", "shy", "sleepy"):
            return
        self.pose = pose
        self.pose_until = time.monotonic() + max(0, float(seconds))
        if phrase:
            self.bubble = phrase[:60]
            self.bubble_until = self.pose_until
        self.update()

    def set_speaking(self, active):
        """Ligada ao ciclo real de áudio; não presume microfone nem vê a tela."""
        self.speaking = bool(active)
        if not active:
            self.mouth_level = None
        if not active and self.pose == "talk":
            # A voz terminou: não manter boca animada por um prazo antigo.
            self.pose_until = 0.0
        self.update()

    def set_mouth_level(self, level):
        """Recebe nível de áudio apenas enquanto a mídia está tocando."""
        if self.speaking:
            self.mouth_level = None if level is None else max(
                0.0, min(1.0, float(level)))
            self.update()

    def visible_pose(self):
        # Expressões solicitadas prevalecem sobre o TTS por poucos segundos.
        # A fala permanece sincronizada pelo flag 'speaking' no frame_at.
        if (time.monotonic() < self.pose_until
                and self.pose in ("angry", "wink", "laugh", "shy", "sleepy",
                                  "curious", "surprised", "wave", "happy", "pose")):
            return self.pose
        if self.speaking:
            return "talk"
        if time.monotonic() < self.pose_until:
            return self.pose
        if self.battery_mood.mode in ("low", "critical"):
            return "walk" if self._battery_seeking else "sleepy"
        if self.battery_mood.mode in ("tired", "charging"):
            return "sit"
        spontaneous = idle_expression(
            self.tick_count, speaking=self.speaking,
            reduced_motion=self.appearance["reduced_motion"],
            busy=self.drag_start is not None,
        )
        if spontaneous is not None:
            return spontaneous
        return ambient_pose(
            self.tick_count,
            self.appearance["walking"],
            self.appearance["reduced_motion"],
        )

    def _update_gaze(self):
        """Segue o cursor aos poucos; nenhuma posição é salva nem compartilhada."""
        factor = SIZES[self.appearance["size"]]
        cursor = self.mapFromGlobal(QCursor.pos())
        if (-90 * factor <= cursor.x() <= 280 * factor
                and -90 * factor <= cursor.y() <= 367 * factor):
            target = (cursor.x() / factor, cursor.y() / factor)
        else:
            target = (95.0, 135.0)
        self._eye_cursor = ease_gaze(self._eye_cursor, target)

    def advance(self):
        if not self.isVisible():
            return
        self.tick_count += 1
        self._update_gaze()
        if (self.battery_mood.seek_charger
                and self.drag_start is None
                and not self.appearance["reduced_motion"]
                and not self.speaking
                and time.monotonic() >= self.pose_until):
            screen = QApplication.screenAt(self.geometry().center())
            if screen is None:
                screen = QApplication.primaryScreen()
            if screen is not None:
                rect = screen.availableGeometry()
                target = max(rect.left(), rect.right() - self.width() - 6)
                delta = target - self.x_coordinate
                self._battery_seeking = abs(delta) > 9
                if self._battery_seeking:
                    self.x_coordinate += max(-1.2, min(1.2, delta))
                    self.move(round(self.x_coordinate), self.y())
            else:
                self._battery_seeking = False
        else:
            self._battery_seeking = False
        walking = (not self._battery_seeking and self.drag_start is None
                   and self.visible_pose() == "walk")
        self._walk_speed += ((1.0 if walking else 0.0) - self._walk_speed) * 0.18
        if walking:
            screen = QApplication.screenAt(self.geometry().center())
            if screen is None:
                screen = QApplication.primaryScreen()
            if screen is not None:
                rect = screen.availableGeometry()
                cursor = QCursor.pos()
                factor = SIZES[self.appearance["size"]]
                close_cursor = (
                    abs(cursor.x() - self.geometry().center().x()) < 105 * factor
                    and abs(cursor.y() - self.geometry().center().y()) < 155 * factor
                )
                if not close_cursor:
                    self.x_coordinate += self.step * 0.72 * self._walk_speed
                    low, high = rect.left(), rect.right() - self.width() + 1
                    if self.x_coordinate < low or self.x_coordinate > high:
                        self.step *= -1
                        self.x_coordinate = min(high, max(low, self.x_coordinate))
                    self.move(round(self.x_coordinate), self.y())
        self.update()

    def enterEvent(self, event):
        if self.drag_start is None and self.visible_pose() in ("idle", "walk", "sit"):
            self.set_pose("idle", seconds=1.1, phrase="Opa, Kaizen!")
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.set_pose("angry", 3.0, "Ei! Nada de me cutucar! >:(")
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.show_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start is not None:
            target = event.globalPosition().toPoint() - self.drag_start
            self.move(target)
            self.x_coordinate = float(self.x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = None
            self._keep_on_screen()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def show_menu(self, point):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#211a33;color:#f7f0ff;border:1px solid #745ba2;}"
            "QMenu::item{padding:9px 20px;}QMenu::item:selected{background:#59437d;}"
        )
        sit = menu.addAction("Sentar")
        stand = menu.addAction("Levantar")
        wave_action = menu.addAction("Acenar 👋")
        pose_action = menu.addAction("Fazer pose ✨")
        wink_action = menu.addAction("Dar piscadinha 😉")
        laugh_action = menu.addAction("Dar risada")
        shy_action = menu.addAction("Ficar tímida")
        curious_action = menu.addAction("Ficar curiosa 🤔")
        surprised_action = menu.addAction("Mostrar surpresa 😮")
        happy_action = menu.addAction("Sorrir 😊")
        sleep_action = menu.addAction("Tirar soneca")
        wake_action = menu.addAction("Acordar")
        pause = menu.addAction("Pausar caminhada" if self.appearance["walking"]
                               else "Permitir caminhada")
        reduce_motion = menu.addAction(
            "Restaurar animações" if self.appearance["reduced_motion"]
            else "Reduzir animações"
        )
        menu.addSeparator()
        hair_menu = menu.addMenu("Cabelo")
        hair_choices = {hair_menu.addAction(name.title()): ("hair", name)
                        for name in HAIR}
        eye_menu = menu.addMenu("Olhos")
        eye_choices = {eye_menu.addAction(name.title()): ("eyes", name)
                       for name in EYES}
        outfit_menu = menu.addMenu("Roupa")
        outfit_choices = {outfit_menu.addAction(name.title()): ("outfit", name)
                          for name in OUTFITS}
        hairstyle_menu = menu.addMenu("Estilo do cabelo")
        hairstyle_choices = {hairstyle_menu.addAction(label): ("hair_style", name)
                             for name, label in HAIR_STYLES.items()}
        costume_menu = menu.addMenu("Modelo da roupa")
        costume_choices = {costume_menu.addAction(label): ("costume", name)
                           for name, label in COSTUMES.items()}
        accessory_menu = menu.addMenu("Acessórios")
        accessory_choices = {accessory_menu.addAction(label): ("accessory", name)
                             for name, label in ACCESSORIES.items()}
        size_menu = menu.addMenu("Tamanho do avatar")
        size_choices = {size_menu.addAction(label): ("size", name)
                        for name, label in (("pequena", "Pequena (75%)"),
                                            ("normal", "Normal (100%)"),
                                            ("grande", "Grande (130%)"))}
        menu.addSeparator()
        hide = menu.addAction("Esconder avatar")
        chosen = menu.exec(point)
        chosen_style = (hair_choices | eye_choices | outfit_choices
                        | hairstyle_choices | costume_choices
                        | accessory_choices | size_choices).get(chosen)
        if chosen_style is not None:
            from avatar_state import save_style
            key, color = chosen_style
            self.appearance[key] = color
            save_style(self.root, self.appearance)
            self.reload_appearance()
            self.set_pose("happy", seconds=2, phrase="Visual novo! 🖤")
            return
        if chosen == sit:
            self.set_pose("sit", seconds=25, phrase="Uma pausa... 🖤")
        elif chosen == stand:
            self.set_pose("idle", seconds=7)
        elif chosen == wave_action:
            self.set_pose("wave", seconds=5, phrase="Oieee! 👋")
        elif chosen == pose_action:
            self.set_pose("pose", seconds=5, phrase="Ta-dã! ✨")
        elif chosen == wink_action:
            self.set_pose("wink", seconds=4, phrase="Hihi! 😉")
        elif chosen == laugh_action:
            self.set_pose("laugh", seconds=5, phrase="Hahaha! 🖤")
        elif chosen == shy_action:
            self.set_pose("shy", seconds=7, phrase="E-ei! ✨")
        elif chosen == curious_action:
            self.set_pose("curious", seconds=6, phrase="Hmm... interessante! 🤔")
        elif chosen == surprised_action:
            self.set_pose("surprised", seconds=5, phrase="Uau! 😮")
        elif chosen == happy_action:
            self.set_pose("happy", seconds=5, phrase="Hehe! 🖤")
        elif chosen == sleep_action:
            self.set_pose("sleepy", seconds=20, phrase="Zzz...")
        elif chosen == wake_action:
            self.set_pose("idle", seconds=4, phrase="Acordei! 🖤")
        elif chosen == reduce_motion:
            from avatar_state import save_style
            self.appearance["reduced_motion"] = not self.appearance["reduced_motion"]
            save_style(self.root, self.appearance)
            self.reload_appearance()
            self.set_pose("idle", seconds=1,
                          phrase="Movimentos reduzidos" if self.appearance["reduced_motion"]
                          else "Movimentos restaurados")
        elif chosen == pause:
            from avatar_state import save_style
            self.appearance["walking"] = not self.appearance["walking"]
            save_style(self.root, self.appearance)
            self.set_pose("idle", seconds=1)
        elif chosen == hide:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # Canvas original 190x277: escala uniforme, sem recortar o balão de fala.
        factor = SIZES[self.appearance["size"]]
        painter.scale(factor, factor)

        pose = self.visible_pose()
        now = time.monotonic()
        wave = math.sin(self.tick_count * 0.23)
        motion = frame_at(
            self.tick_count, pose, self._eye_cursor, self.speaking,
            reduced_motion=self.appearance["reduced_motion"],
            mouth_level=self.mouth_level,
        )
        # Uma transição de ~240 ms suaviza mudanças bruscas entre gestos.
        if self._last_render_pose != pose:
            self._transition_from = self._previous_motion
            self._transition_start = now
            self._last_render_pose = pose
        if self._transition_from is not None and not self.appearance["reduced_motion"]:
            progress = (now - self._transition_start) / 0.24
            if progress < 1.0:
                motion = blend_frames(self._transition_from, motion, progress)
            else:
                self._transition_from = None
        self._previous_motion = motion
        sway = motion.body_bob
        hair = QColor(HAIR[self.appearance["hair"]])
        eyes = QColor(EYES[self.appearance["eyes"]])
        dress = QColor(OUTFITS[self.appearance["outfit"]])
        hair_style = self.appearance["hair_style"]
        costume = self.appearance["costume"]
        accessory = self.appearance["accessory"]
        shadow = QColor("#171125")
        skin = QColor("#f5d8d8")

        # Sombra de apoio; no modo sentado, o corpo desce e as pernas dobram.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(22, 14, 38, 95))
        painter.drawEllipse(QRectF(32, 249, 126, 17))

        painter.save()
        painter.translate(95, 0)
        if self.step < 0 and pose == "walk":
            painter.scale(-1, 1)
        painter.translate(0, sway)
        painter.rotate(motion.tilt)

        sitting = pose in ("sit", "sleepy")
        vertical = 30 if sitting else 0

        # Cabelo atrás da cabeça: cortes realmente diferentes, não só cores.
        painter.setPen(QPen(shadow, 2.2))
        painter.setBrush(hair)
        if hair_style == "longo":
            painter.drawRoundedRect(QRectF(-57, 63 + vertical, 114, 133), 43, 34)
            painter.drawEllipse(QRectF(-62 + motion.hair_sway,
                                       95 + vertical, 26, 111))
            painter.drawEllipse(QRectF(37 - motion.hair_sway,
                                       95 + vertical, 26, 111))
            painter.setPen(QPen(hair.lighter(138), 2.0))
            painter.drawArc(QRectF(-58 + motion.hair_sway,
                                   98 + vertical, 20, 99), 80 * 16, 130 * 16)
            painter.drawArc(QRectF(38 - motion.hair_sway,
                                   98 + vertical, 20, 99), 320 * 16, 130 * 16)
        elif hair_style == "curto":
            painter.drawRoundedRect(QRectF(-56, 64 + vertical, 112, 101), 41, 33)
            painter.drawEllipse(QRectF(-58, 101 + vertical, 25, 57))
            painter.drawEllipse(QRectF(33, 101 + vertical, 25, 57))
        elif hair_style == "marias":
            painter.drawRoundedRect(QRectF(-53, 65 + vertical, 106, 95), 39, 34)
            painter.drawEllipse(QRectF(-74 - motion.hair_sway, 101 + vertical, 31, 86))
            painter.drawEllipse(QRectF(43 + motion.hair_sway, 101 + vertical, 31, 86))
            painter.setBrush(QColor("#cc9be9"))
            painter.drawRoundedRect(QRectF(-61, 106 + vertical, 14, 13), 4, 4)
            painter.drawRoundedRect(QRectF(47, 106 + vertical, 14, 13), 4, 4)
        else:  # rabo de cavalo
            painter.drawRoundedRect(QRectF(-53, 64 + vertical, 106, 95), 42, 35)
            ponytail = QPainterPath()
            ponytail.moveTo(45, 93 + vertical)
            ponytail.cubicTo(86 + motion.hair_sway, 87 + vertical,
                            74 + motion.hair_sway, 174 + vertical,
                            53 + motion.hair_sway, 198 + vertical)
            ponytail.cubicTo(66 + motion.hair_sway, 152 + vertical,
                            55, 129 + vertical, 43, 114 + vertical)
            ponytail.closeSubpath()
            painter.drawPath(ponytail)
            painter.setBrush(QColor("#bd91d6"))
            painter.drawEllipse(QRectF(42, 99 + vertical, 16, 16))

        # Pernas, sapatinhos e caminhada alternada.
        if sitting:
            painter.setPen(QPen(shadow, 10, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(-22, 210 + vertical), QPointF(-48, 236))
            painter.drawLine(QPointF(22, 210 + vertical), QPointF(48, 236))
        else:
            pace = wave * 7 if pose == "walk" else 0
            painter.setPen(QPen(shadow, 12, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(-17, 205), QPointF(-19 + pace, 249))
            painter.drawLine(QPointF(17, 205), QPointF(19 - pace, 249))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#443152"))
        painter.drawEllipse(QRectF(-37, 241, 33, 12))
        painter.drawEllipse(QRectF(4, 241, 33, 12))

        # Roupa em 3 modelagens, preservando a paleta escolhida.
        painter.setPen(QPen(shadow, 2.3))
        painter.setBrush(dress)
        if costume == "vestido":
            hem = QPainterPath()
            hem.moveTo(-23, 163 + vertical)
            hem.lineTo(23, 163 + vertical)
            hem.lineTo(48 + motion.breath, 220 + vertical)
            hem.quadTo(0, 230 + vertical, -48 - motion.breath, 220 + vertical)
            hem.closeSubpath()
            painter.drawPath(hem)
            painter.setPen(QPen(QColor("#b39bd1"), 2))
            painter.drawLine(QPointF(-43, 213 + vertical), QPointF(43, 213 + vertical))
            painter.setPen(QPen(QColor("#e7c6ec"), 1.8))
            painter.drawLine(QPointF(0, 165 + vertical), QPointF(0, 201 + vertical))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#bda2d7"))
            painter.drawEllipse(QRectF(-5, 185 + vertical, 10, 10))
        elif costume == "casual":
            # Camiseta e bermuda com faixa cruzada.
            painter.drawRoundedRect(QRectF(-36, 164 + vertical, 72, 50), 12, 12)
            painter.setBrush(dress.darker(135))
            painter.drawRoundedRect(QRectF(-35, 207 + vertical, 32, 18), 4, 4)
            painter.drawRoundedRect(QRectF(3, 207 + vertical, 32, 18), 4, 4)
            painter.setPen(QPen(QColor("#d3b6e9"), 3))
            painter.drawLine(QPointF(-21, 170 + vertical), QPointF(23, 205 + vertical))
            painter.setBrush(QColor("#bb87d8"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(-4, 186 + vertical, 8, 8))
        else:  # casaco
            painter.drawRoundedRect(QRectF(-38, 160 + vertical, 76, 66), 12, 13)
            painter.setBrush(dress.lighter(155))
            left_lapel = QPainterPath()
            left_lapel.moveTo(-30, 165 + vertical)
            left_lapel.lineTo(0, 189 + vertical)
            left_lapel.lineTo(-13, 208 + vertical)
            left_lapel.closeSubpath()
            right_lapel = QPainterPath()
            right_lapel.moveTo(30, 165 + vertical)
            right_lapel.lineTo(0, 189 + vertical)
            right_lapel.lineTo(13, 208 + vertical)
            right_lapel.closeSubpath()
            painter.drawPath(left_lapel)
            painter.drawPath(right_lapel)
            painter.setPen(QPen(QColor("#e7c6ec"), 2))
            painter.drawLine(QPointF(0, 192 + vertical), QPointF(0, 219 + vertical))
            painter.setBrush(QColor("#c9a5da"))
            painter.setPen(Qt.PenStyle.NoPen)
            for y in (197, 209, 220):
                painter.drawEllipse(QRectF(3, y + vertical, 5, 5))

        # Braços em gestos explícitos: aceno, pose e surpresa.
        painter.setPen(QPen(skin, 11, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        if pose == "angry":
            painter.drawLine(QPointF(-23, 171 + vertical), QPointF(-40, 185 + vertical))
            painter.drawLine(QPointF(23, 171 + vertical), QPointF(40, 185 + vertical))
        elif pose == "wave":
            painter.drawLine(QPointF(-25, 169 + vertical), QPointF(-43, 196 + vertical))
            painter.drawLine(QPointF(25, 169 + vertical),
                             QPointF(45 + wave * 6, 118 + vertical + abs(wave * 9)))
            painter.setBrush(skin)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(38 + wave * 6,
                                       110 + vertical + abs(wave * 9), 15, 15))
        elif pose == "pose":
            painter.drawLine(QPointF(-23, 171 + vertical), QPointF(-53, 150 + vertical))
            painter.drawLine(QPointF(23, 171 + vertical), QPointF(53, 150 + vertical))
        elif pose == "surprised":
            painter.drawLine(QPointF(-23, 172 + vertical), QPointF(-39, 141 + vertical))
            painter.drawLine(QPointF(23, 172 + vertical), QPointF(39, 141 + vertical))
        else:
            painter.drawLine(QPointF(-25, 169 + vertical),
                             QPointF(-47, 193 + vertical + wave * 3))
            painter.drawLine(QPointF(25, 169 + vertical),
                             QPointF(46, 192 + vertical - wave * 3))

        # Cabeça chibi e franja em três pontas.
        painter.setPen(QPen(shadow, 2.4))
        painter.setBrush(skin)
        painter.drawEllipse(QRectF(-50, 71 + vertical, 100, 94))
        painter.setBrush(hair)
        crown = QPainterPath()
        crown.moveTo(-53, 112 + vertical)
        crown.quadTo(-66, 47 + vertical, 0, 54 + vertical)
        crown.quadTo(64, 50 + vertical, 53, 111 + vertical)
        crown.quadTo(41, 101 + vertical, 32, 86 + vertical)
        crown.quadTo(13, 111 + vertical, 1, 101 + vertical)
        crown.quadTo(-10, 111 + vertical, -16, 92 + vertical)
        crown.quadTo(-32, 111 + vertical, -53, 112 + vertical)
        painter.drawPath(crown)
        # Mechas finas dão profundidade ao cabelo sem imagens ou GPU.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(hair.lighter(125), 1.3))
        painter.drawArc(QRectF(-47 + motion.hair_sway * 0.12,
                               64 + vertical, 44, 72), 28 * 16, 115 * 16)
        painter.drawArc(QRectF(5 - motion.hair_sway * 0.12,
                               64 + vertical, 44, 72), 35 * 16, 110 * 16)
        painter.setPen(QPen(hair.darker(118), 1.1))
        painter.drawArc(QRectF(-23, 70 + vertical, 44, 54),
                        190 * 16, 115 * 16)
        # Brilho da franja e pequeno laço decorativo estilo anime.
        painter.setPen(QPen(hair.lighter(156), 2.0))
        painter.drawArc(QRectF(-39, 64 + vertical, 67, 40),
                        42 * 16, 112 * 16)
        # Adornos aparecem ou desaparecem conforme a escolha no menu.
        if accessory == "laco":
            painter.setPen(QPen(shadow, 1.4))
            painter.setBrush(QColor("#9874bf"))
            painter.drawEllipse(QRectF(35, 77 + vertical, 19, 15))
            painter.setBrush(QColor("#d7b6ef"))
            painter.drawEllipse(QRectF(40, 81 + vertical, 8, 7))
            # Duas pontas de fita e um brilho para dar relevo ao laço.
            painter.setBrush(QColor("#b88bd8"))
            painter.drawEllipse(QRectF(32, 87 + vertical, 10, 14))
            painter.drawEllipse(QRectF(49, 87 + vertical, 10, 14))
            painter.setBrush(QColor("#f4dfff"))
            painter.drawEllipse(QRectF(42, 82 + vertical, 3, 3))
        elif accessory == "tiara":
            painter.setPen(QPen(QColor("#d0a5ec"), 6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(-46, 55 + vertical, 93, 49), 17 * 16, 150 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#f1c6ff"))
            painter.drawEllipse(QRectF(-5, 59 + vertical, 10, 10))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(-2, 61 + vertical, 3, 3))

        # Pálpebras piscam; pupilas acompanham o cursor quando ele se aproxima.
        if motion.blink > .9 or pose in ("sleepy", "laugh"):
            painter.setPen(QPen(shadow, 3.4, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawArc(QRectF(-35, 119 + vertical, 25, 12),
                            0, 180 * 16)
            painter.drawArc(QRectF(10, 119 + vertical, 25, 12),
                            0, 180 * 16)
        else:
            painter.setBrush(QColor("#fff8fa"))
            painter.setPen(QPen(shadow, 2))
            painter.drawEllipse(QRectF(-35, 117 + vertical, 25, 25))
            painter.drawEllipse(QRectF(10, 117 + vertical, 25, 25))
            painter.setBrush(eyes)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(-27 + motion.eye_dx,
                                       122 + vertical + motion.eye_dy, 13, 16))
            painter.drawEllipse(QRectF(14 + motion.eye_dx,
                                       122 + vertical + motion.eye_dy, 13, 16))
            painter.setBrush(eyes.darker(150))
            painter.drawEllipse(QRectF(-23 + motion.eye_dx, 128 + vertical + motion.eye_dy, 5, 8))
            painter.drawEllipse(QRectF(18 + motion.eye_dx, 128 + vertical + motion.eye_dy, 5, 8))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(-23 + motion.eye_dx,
                                       125 + vertical + motion.eye_dy, 5, 5))
            painter.drawEllipse(QRectF(18 + motion.eye_dx,
                                       125 + vertical + motion.eye_dy, 5, 5))
            painter.setBrush(QColor("#e9d8ff"))
            painter.drawEllipse(QRectF(-17 + motion.eye_dx, 133 + vertical + motion.eye_dy, 2.5, 2.5))
            painter.drawEllipse(QRectF(24 + motion.eye_dx, 133 + vertical + motion.eye_dy, 2.5, 2.5))
            painter.setPen(QPen(shadow, 2))
            painter.drawLine(QPointF(-36, 121 + vertical),
                             QPointF(-31, 117 + vertical))
            painter.drawLine(QPointF(31, 117 + vertical),
                             QPointF(36, 121 + vertical))
            if pose == "wink":
                # Fecha apenas o olho esquerdo, preservando o direito aberto.
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(skin)
                painter.drawEllipse(QRectF(-37, 115 + vertical, 29, 30))
                painter.setPen(QPen(shadow, 3.4, Qt.PenStyle.SolidLine,
                                    Qt.PenCapStyle.RoundCap))
                painter.drawArc(QRectF(-35, 119 + vertical, 25, 12),
                                0, 180 * 16)
        painter.setPen(QPen(shadow, 3, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        if pose == "angry":
            painter.drawLine(-36, 111 + vertical, -12, 118 + vertical)
            painter.drawLine(12, 118 + vertical, 36, 111 + vertical)
        elif pose == "surprised":
            # Sobrancelhas elevadas e simétricas.
            painter.drawArc(QRectF(-36, 105 + vertical, 24, 9), 0, 180 * 16)
            painter.drawArc(QRectF(12, 105 + vertical, 24, 9), 0, 180 * 16)
        elif pose == "curious":
            # Uma sobrancelha arqueada sugere curiosidade.
            painter.drawArc(QRectF(-36, 105 + vertical, 24, 10), 0, 180 * 16)
            painter.drawLine(14, 112 + vertical, 35, 111 + vertical)
        elif pose == "shy":
            # Sobrancelhas delicadamente inclinadas.
            painter.drawLine(-35, 110 + vertical, -14, 113 + vertical)
            painter.drawLine(14, 113 + vertical, 35, 110 + vertical)
        else:
            painter.drawLine(-35, 112 + vertical, -14, 111 + vertical)
            painter.drawLine(14, 111 + vertical, 35, 112 + vertical)

        if accessory == "oculos":
            painter.setPen(QPen(QColor("#9c80be"), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(-40, 116 + vertical, 34, 30), 8, 7)
            painter.drawRoundedRect(QRectF(6, 116 + vertical, 34, 30), 8, 7)
            painter.drawLine(QPointF(-6, 123 + vertical),
                             QPointF(6, 123 + vertical))
            painter.drawLine(QPointF(-40, 121 + vertical),
                             QPointF(-51, 115 + vertical))
            painter.drawLine(QPointF(40, 121 + vertical),
                             QPointF(51, 115 + vertical))

        # Bochechas e boca expressiva, sem atribuir sentimentos reais à IA.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(233, 130, 153,
                                190 if pose == "shy" else 95))
        painter.drawEllipse(QRectF(-43, 139 + vertical, 15, 6))
        painter.drawEllipse(QRectF(28, 139 + vertical, 15, 6))
        if pose in ("happy", "laugh", "shy"):
            # Pequenos brilhos nas bochechas reforçam expressões sem assets.
            painter.setBrush(QColor(255, 235, 242, 175))
            painter.drawEllipse(QRectF(-40, 140 + vertical, 5, 2))
            painter.drawEllipse(QRectF(35, 140 + vertical, 5, 2))
        painter.setPen(QPen(QColor("#6e3c5c"), 2))
        if pose == "angry":
            painter.drawArc(QRectF(-8, 153 + vertical, 16, 10), 0, 180 * 16)
        elif motion.mouth_open > 0:
            painter.setBrush(QColor("#a45b7e"))
            painter.drawEllipse(QRectF(-8, 149 + vertical,
                                       16, motion.mouth_open + 3))
        elif pose == "curious":
            painter.drawArc(QRectF(-6, 147 + vertical, 12, 9),
                            190 * 16, 155 * 16)
        elif pose == "surprised":
            painter.setBrush(QColor("#9b5774"))
            painter.drawEllipse(QRectF(-6, 148 + vertical, 12, 14))
        elif pose == "laugh":
            painter.setBrush(QColor("#a45b7e"))
            painter.drawEllipse(QRectF(-10, 146 + vertical, 20, 15))
        elif pose in ("happy", "wave", "pose", "wink", "shy"):
            painter.drawArc(QRectF(-9, 146 + vertical, 18, 13),
                            180 * 16, 180 * 16)
        else:
            painter.drawArc(QRectF(-8, 147 + vertical, 16, 9),
                            190 * 16, 155 * 16)
        painter.restore()

        # Efeitos vetoriais leves: sem imagens, captura da tela ou animação 3D.
        if pose == "sleepy":
            painter.setPen(QColor("#b89ae6"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.drawText(QRectF(143, 70, 44, 28), Qt.AlignmentFlag.AlignCenter, "Zzz")
        elif pose == "wink":
            painter.setPen(QColor("#f2c8fa"))
            painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            painter.drawText(QRectF(141, 120, 35, 31), Qt.AlignmentFlag.AlignCenter, "✦")

        # Indicador fictício da "energia" da personagem, lendo a bateria real.
        # Oculto em desktops e em sensores sem status confiável.
        if self.battery_mood.percent is not None:
            mode = self.battery_mood.mode
            tint = QColor("#e88d9e") if mode in ("low", "critical") else (
                QColor("#a1d5a0") if mode in ("charging", "full")
                else QColor("#bfa5ee"))
            painter.setPen(QPen(tint, 1.2))
            painter.setBrush(QColor("#292238"))
            painter.drawRoundedRect(QRectF(125, 223, 57, 27), 7, 7)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(131, 224, 48, 24),
                             Qt.AlignmentFlag.AlignCenter,
                             str(self.battery_mood.percent) + "%")
            if mode == "charging":
                painter.setPen(QColor("#d7eab0"))
                painter.drawText(QRectF(139, 249, 38, 22),
                                 Qt.AlignmentFlag.AlignCenter, "⚡")
        # Balão opcional; o avatar não lê arquivos, microfone ou janela de terceiros.
        if self.bubble and now < self.bubble_until:
            painter.setPen(QPen(QColor("#8b6cb9"), 1.6))
            painter.setBrush(QColor("#28213d"))
            painter.drawRoundedRect(QRectF(9, 6, 172, 43), 10, 10)
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#f5ecff"))
            painter.drawText(QRectF(17, 11, 156, 31),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             self.bubble)
        painter.end()


def main():
    import sys
    from pathlib import Path
    app = QApplication(sys.argv)
    avatar = YunaAvatar(Path(__file__).resolve().parent)
    avatar.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
